import pytest
from unittest.mock import MagicMock, patch
from app.scanner.odoo_client import OdooClient, OdooConnectionError, OdooPermissionError, _validate_url
from app.scanner.checks import (
    check_sale_orders,
    check_stock_pickings,
    check_crm_leads,
    check_ir_cron,
    check_res_partner,
)


def test_validate_url_rejects_localhost():
    with pytest.raises(OdooConnectionError):
        _validate_url("http://localhost:8069")


def test_validate_url_rejects_private_ip():
    with pytest.raises(OdooConnectionError):
        _validate_url("http://192.168.1.100:8069")


def test_validate_url_accepts_public():
    result = _validate_url("https://mycompany.odoo.com")
    assert result == "https://mycompany.odoo.com"


def test_validate_url_rejects_non_http():
    with pytest.raises(OdooConnectionError):
        _validate_url("ftp://mycompany.odoo.com")


def make_mock_client(model_exists=True):
    client = MagicMock(spec=OdooClient)
    client.model_exists.return_value = model_exists
    return client


def test_check_sale_orders_not_applicable():
    client = make_mock_client(model_exists=False)
    result = check_sale_orders(client)
    assert result["applicable"] is False
    assert result["check_id"] == "sale_orders_stuck"


def test_check_sale_orders_no_orders():
    client = make_mock_client()
    client.count.return_value = 0
    result = check_sale_orders(client)
    assert result["applicable"] is True
    assert result["raw_metric"] == 0
    assert result["severity"] == "low"


def test_check_sale_orders_high_severity():
    # pequeña company (100 orders): high threshold is 30% → use 35 stuck
    client = make_mock_client()
    client.count.side_effect = [100, 35]
    result = check_sale_orders(client)
    assert result["severity"] == "high"
    assert result["raw_metric"] == 35


def test_check_crm_leads_not_applicable():
    client = make_mock_client(model_exists=False)
    result = check_crm_leads(client)
    assert result["applicable"] is False


def test_check_crm_leads_all_have_activity():
    client = make_mock_client()
    client.count.side_effect = [50, 0]
    result = check_crm_leads(client)
    assert result["raw_metric"] == 0
    assert result["severity"] == "low"


def test_check_ir_cron_active():
    client = make_mock_client()
    client.count.side_effect = [10, 2]
    result = check_ir_cron(client)
    assert result["raw_metric"] == 10
    assert result["context"]["active_crons"] == 10


def test_check_res_partner_high_missing_email():
    client = make_mock_client()
    client.count.side_effect = [100, 60]
    result = check_res_partner(client)
    assert result["severity"] == "high"
