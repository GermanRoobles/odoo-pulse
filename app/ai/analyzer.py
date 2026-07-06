import json
import anthropic
from app.ai.prompts import SYSTEM_PROMPT
from app.ai.schemas import AnalysisResult
from app.config import settings


class AIAnalysisError(Exception):
    pass


def _parse_response(text: str) -> AnalysisResult:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # strip opening fence (```json or ```) and closing fence
        start = 1
        end = len(lines)
        if lines[-1].strip() == "```":
            end = len(lines) - 1
        text = "\n".join(lines[start:end])
    try:
        data = json.loads(text)
        return AnalysisResult.model_validate(data)
    except (json.JSONDecodeError, Exception) as e:
        raise AIAnalysisError(f"Respuesta de IA con formato inválido: {e}") from e


def analyze_checks(checks: list, company_name: str, company_context: str = "", sector: str = "") -> AnalysisResult:
    """Send scanner checks to Claude and return a validated AnalysisResult."""
    if not settings.anthropic_api_key:
        raise AIAnalysisError("ANTHROPIC_API_KEY no configurada.")

    applicable = [c for c in checks if c.get("applicable", True)]
    payload = {
        "empresa": company_name,
        "sector": sector if sector else "no especificado",
        "contexto_adicional": company_context,
        "checks": applicable,
    }
    user_message = (
        "Analiza los siguientes datos de auditoría Odoo:\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    last_error = None
    for attempt in range(2):
        try:
            msg = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )
            text = msg.content[0].text
            return _parse_response(text)
        except AIAnalysisError as e:
            last_error = e
            if attempt == 0:
                user_message += (
                    "\n\nIMPORTANTE: Responde ÚNICAMENTE con JSON puro, "
                    "sin texto adicional ni bloques de código markdown."
                )
                continue
            raise
        except anthropic.APIError as e:
            raise AIAnalysisError(f"Error en la API de Claude: {e}") from e

    raise last_error or AIAnalysisError("No se pudo obtener un análisis válido.")
