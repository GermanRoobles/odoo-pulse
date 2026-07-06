import pytest
import json
from app.ai.analyzer import _parse_response, AIAnalysisError
from app.ai.schemas import AnalysisResult


VALID_RESPONSE = json.dumps({
    "score": 45,
    "score_label": "Automatización parcial",
    "summary": "La empresa tiene oportunidades claras de mejora en facturación y CRM.",
    "findings": [
        {
            "title": "Facturas en borrador",
            "description": "Hay 12 facturas atascadas más de 30 días. Esto supone riesgo de cobro.",
            "severity": "high",
            "estimated_hours_month": "6-10",
            "recommended_tool": "Odoo Studio",
            "category": "facturacion",
        }
    ],
    "quick_win": "Activar recordatorios automáticos de facturas pendientes en Odoo.",
})


def test_parse_valid_response():
    result = _parse_response(VALID_RESPONSE)
    assert isinstance(result, AnalysisResult)
    assert result.score == 45
    assert len(result.findings) == 1
    assert result.findings[0].severity == "high"


def test_parse_response_strips_markdown():
    wrapped = "```json\n" + VALID_RESPONSE + "\n```"
    result = _parse_response(wrapped)
    assert result.score == 45


def test_parse_invalid_json_raises():
    with pytest.raises(AIAnalysisError):
        _parse_response("not json at all")


def test_score_clamped():
    data = json.loads(VALID_RESPONSE)
    data["score"] = 150
    result = _parse_response(json.dumps(data))
    assert result.score == 100


def test_findings_capped_at_6():
    data = json.loads(VALID_RESPONSE)
    data["findings"] = data["findings"] * 10
    result = _parse_response(json.dumps(data))
    assert len(result.findings) <= 6


def test_parse_missing_field_raises():
    data = json.loads(VALID_RESPONSE)
    del data["summary"]
    with pytest.raises(AIAnalysisError):
        _parse_response(json.dumps(data))
