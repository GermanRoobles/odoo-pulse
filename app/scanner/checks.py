from datetime import datetime, timedelta, timezone
from typing import Any
from app.scanner.odoo_client import OdooClient


def _now() -> datetime:
    return datetime.now(timezone.utc)


CheckResult = dict

# Company size buckets based on order volume (last 90 days)
# Used to calibrate severity so a 10% problem at 50 orders/mo ≠ same at 4000 orders/mo
def _company_size(total_orders_90d: int) -> str:
    if total_orders_90d >= 1000:
        return "grande"
    if total_orders_90d >= 150:
        return "media"
    return "pequeña"


def _severity_pct(pct: float, size: str, thresholds: dict) -> str:
    """Threshold-based severity that scales with company size."""
    medium, high = thresholds[size]
    if pct >= high:
        return "high"
    if pct >= medium:
        return "medium"
    return "low"


def _severity_abs(value: float, size: str, thresholds: dict) -> str:
    """Absolute-value severity that scales with company size."""
    medium, high = thresholds[size]
    if value >= high:
        return "high"
    if value >= medium:
        return "medium"
    return "low"


def _make_result(check_id: str, raw_metric, context: dict, severity: str) -> CheckResult:
    return {
        "check_id": check_id,
        "raw_metric": raw_metric,
        "context": context,
        "severity": severity,
        "applicable": True,
    }


def _not_applicable(check_id: str) -> CheckResult:
    return {"check_id": check_id, "raw_metric": 0, "context": {}, "severity": "none", "applicable": False}


def check_sale_orders(client: OdooClient) -> CheckResult:
    if not client.model_exists("sale.order"):
        return _not_applicable("sale_orders_stuck")
    cutoff = (_now() - timedelta(days=90)).strftime("%Y-%m-%d")
    total = client.count("sale.order", [("create_date", ">=", cutoff)])
    if total == 0:
        return _make_result("sale_orders_stuck", 0,
                            {"total_orders_90d": 0, "pct": 0.0, "volume_context": "pequeña"}, "low")
    stuck_cutoff = (_now() - timedelta(days=7)).strftime("%Y-%m-%d")
    stuck = client.count("sale.order", [
        ("state", "=", "draft"),
        ("create_date", ">=", cutoff),
        ("write_date", "<=", stuck_cutoff),
    ])
    pct = round(stuck / total * 100, 1)
    size = _company_size(total)
    # Larger companies tolerate less % blockage before it becomes high severity
    thresholds = {"pequeña": (10, 30), "media": (5, 20), "grande": (3, 10)}
    return _make_result("sale_orders_stuck", stuck,
                        {"total_orders_90d": total, "pct": pct, "volume_context": size},
                        _severity_pct(pct, size, thresholds))


def check_stock_pickings(client: OdooClient) -> CheckResult:
    if not client.model_exists("stock.picking"):
        return _not_applicable("stock_pickings_unfinished")
    total_pending = client.count("stock.picking", [("state", "not in", ["done", "cancel"])])
    overdue = client.count("stock.picking", [
        ("state", "not in", ["done", "cancel"]),
        ("scheduled_date", "<=", _now().strftime("%Y-%m-%d")),
    ])
    # Derive size from pending pickings volume
    size = "grande" if total_pending >= 500 else ("media" if total_pending >= 100 else "pequeña")
    thresholds = {"pequeña": (10, 40), "media": (30, 100), "grande": (100, 400)}
    return _make_result("stock_pickings_unfinished", overdue,
                        {"total_pending": total_pending, "overdue": overdue, "volume_context": size},
                        _severity_abs(overdue, size, thresholds))


def check_account_moves(client: OdooClient) -> CheckResult:
    if not client.model_exists("account.move"):
        return _not_applicable("invoices_stuck_draft")
    cutoff = (_now() - timedelta(days=30)).strftime("%Y-%m-%d")
    total = client.count("account.move", [("move_type", "in", ["out_invoice", "out_refund"])])
    stuck = client.count("account.move", [
        ("state", "=", "draft"),
        ("move_type", "in", ["out_invoice", "out_refund"]),
        ("create_date", "<=", cutoff),
    ])
    size = "grande" if total >= 500 else ("media" if total >= 100 else "pequeña")
    thresholds = {"pequeña": (2, 8), "media": (5, 20), "grande": (15, 50)}
    return _make_result("invoices_stuck_draft", stuck,
                        {"total_invoices": total, "stuck_draft_30d": stuck, "volume_context": size},
                        _severity_abs(stuck, size, thresholds))


def check_crm_leads(client: OdooClient) -> CheckResult:
    if not client.model_exists("crm.lead"):
        return _not_applicable("crm_leads_no_activity")
    total = client.count("crm.lead", [("active", "=", True)])
    no_activity = client.count("crm.lead", [
        ("active", "=", True),
        ("activity_ids", "=", False),
    ])
    pct = round(no_activity / total * 100, 1) if total else 0.0
    size = "grande" if total >= 500 else ("media" if total >= 100 else "pequeña")
    # % of leads without activity — tolerance lower for bigger pipelines
    thresholds = {"pequeña": (40, 70), "media": (30, 60), "grande": (20, 50)}
    return _make_result("crm_leads_no_activity", no_activity,
                        {"total_active_leads": total, "without_activity": no_activity,
                         "pct": pct, "volume_context": size},
                        _severity_pct(pct, size, thresholds))


def check_ir_cron(client: OdooClient) -> CheckResult:
    if not client.model_exists("ir.cron"):
        return _not_applicable("cron_jobs")
    active = client.count("ir.cron", [("active", "=", True)])
    inactive = client.count("ir.cron", [("active", "=", False)])
    total = active + inactive
    inactive_pct = round(inactive / total * 100, 1) if total else 0.0
    # High inactive % with low active count is a red flag regardless of size
    if active <= 3 and inactive >= 10:
        severity = "high"
    elif inactive_pct >= 70:
        severity = "high"
    elif inactive_pct >= 40 or active <= 5:
        severity = "medium"
    else:
        severity = "low"
    return _make_result("cron_jobs", active,
                        {"active_crons": active, "inactive_crons": inactive,
                         "inactive_pct": inactive_pct},
                        severity)


def check_base_automation(client: OdooClient) -> CheckResult:
    if not client.model_exists("base.automation"):
        return _not_applicable("base_automations")
    active = client.count("base.automation", [("active", "=", True)])
    return _make_result("base_automations", active,
                        {"active_automations": active},
                        "low" if active > 3 else "medium")


def check_mail_activity(client: OdooClient) -> CheckResult:
    if not client.model_exists("mail.activity"):
        return _not_applicable("overdue_activities")
    overdue = client.count("mail.activity", [
        ("date_deadline", "<", _now().strftime("%Y-%m-%d")),
    ])
    size = "grande" if overdue >= 200 else ("media" if overdue >= 50 else "pequeña")
    thresholds = {"pequeña": (10, 30), "media": (30, 100), "grande": (100, 300)}
    return _make_result("overdue_activities", overdue,
                        {"overdue_count": overdue, "volume_context": size},
                        _severity_abs(overdue, size, thresholds))


def check_res_partner(client: OdooClient) -> CheckResult:
    if not client.model_exists("res.partner"):
        return _not_applicable("partner_data_quality")
    total = client.count("res.partner", [("is_company", "=", True)])
    no_email = client.count("res.partner", [("is_company", "=", True), ("email", "=", False)])
    pct = round(no_email / total * 100, 1) if total else 0.0
    size = "grande" if total >= 500 else ("media" if total >= 100 else "pequeña")
    thresholds = {"pequeña": (30, 60), "media": (20, 50), "grande": (15, 40)}
    return _make_result("partner_data_quality", no_email,
                        {"total_companies": total, "without_email": no_email,
                         "pct_no_email": pct, "volume_context": size},
                        _severity_pct(pct, size, thresholds))


def check_product_template(client: OdooClient) -> CheckResult:
    if not client.model_exists("product.template"):
        return _not_applicable("product_catalog_quality")
    total = client.count("product.template", [("active", "=", True)])
    no_barcode = client.count("product.template", [("active", "=", True), ("barcode", "=", False)])
    pct = round(no_barcode / total * 100, 1) if total else 0.0
    size = "grande" if total >= 1000 else ("media" if total >= 200 else "pequeña")
    thresholds = {"pequeña": (60, 85), "media": (50, 75), "grande": (40, 65)}
    return _make_result("product_catalog_quality", no_barcode,
                        {"total_active_products": total, "without_barcode": no_barcode,
                         "pct_no_barcode": pct, "volume_context": size},
                        _severity_pct(pct, size, thresholds))


def run_all_checks(client: OdooClient) -> list:
    check_fns = [
        check_sale_orders,
        check_stock_pickings,
        check_account_moves,
        check_crm_leads,
        check_ir_cron,
        check_base_automation,
        check_mail_activity,
        check_res_partner,
        check_product_template,
    ]
    results = []
    for fn in check_fns:
        try:
            result = fn(client)
            results.append(result)
        except Exception as e:
            results.append({
                "check_id": fn.__name__.replace("check_", ""),
                "raw_metric": 0,
                "context": {"error": str(e)},
                "severity": "none",
                "applicable": False,
            })
    return results
