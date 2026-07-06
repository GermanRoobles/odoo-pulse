import resend
from app.config import settings

SEVERITY_COLOR = {"high": "#f87171", "medium": "#fbbf24", "low": "#4ade80"}
SEVERITY_LABEL = {"high": "Alta", "medium": "Media", "low": "Baja"}
SCORE_COLOR = {True: "#4ade80", False: "#fbbf24"}  # >= 70 green, else amber, < 40 red handled below


def _score_color(score: int) -> str:
    if score >= 70:
        return "#4ade80"
    if score >= 40:
        return "#fbbf24"
    return "#f87171"


def send_new_lead_notification(
    company_name: str,
    contact_name: str,
    contact_email: str,
    sector: str,
    score: int,
    score_label: str,
    summary: str,
    findings: list,
    report_url: str,
) -> None:
    if not settings.resend_api_key:
        return

    resend.api_key = settings.resend_api_key

    findings_html = "".join(
        f"""
        <tr>
          <td style="padding:10px 12px; border-bottom:1px solid #1e293b;">
            <span style="color:{SEVERITY_COLOR.get(f.severity, '#94a3b8')}; font-size:11px; font-weight:700;
              text-transform:uppercase; letter-spacing:.06em;">{SEVERITY_LABEL.get(f.severity, f.severity)}</span><br>
            <span style="color:#f1f5f9; font-size:14px;">{f.title}</span>
          </td>
          <td style="padding:10px 12px; border-bottom:1px solid #1e293b; color:#94a3b8; font-size:13px; white-space:nowrap;">
            {f.estimated_hours_month}h/mes
          </td>
        </tr>
        """
        for f in findings[:6]
    )

    sector_text = sector if sector else "No especificado"
    score_col = _score_color(score)

    html = f"""
<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0; padding:0; background:#0b1120; font-family:'Segoe UI',system-ui,sans-serif;">
  <div style="max-width:580px; margin:0 auto; padding:32px 16px;">

    <!-- Header -->
    <div style="margin-bottom:24px;">
      <span style="font-family:monospace; font-size:18px; font-weight:700; color:#14b8a6;">Odoo Pulse</span>
      <span style="font-size:12px; color:#64748b; margin-left:12px; text-transform:uppercase; letter-spacing:.1em;">Nuevo lead</span>
    </div>

    <!-- Alert box -->
    <div style="background:#141f35; border:1px solid #263352; border-radius:12px; padding:24px; margin-bottom:20px;">
      <p style="font-size:13px; color:#64748b; text-transform:uppercase; letter-spacing:.08em; margin:0 0 4px;">Nueva auditoría completada</p>
      <h1 style="font-size:22px; color:#f1f5f9; margin:0 0 4px;">{company_name}</h1>
      <p style="font-size:14px; color:#94a3b8; margin:0;">{contact_name} · <a href="mailto:{contact_email}" style="color:#14b8a6;">{contact_email}</a> · {sector_text}</p>
    </div>

    <!-- Score -->
    <div style="background:#141f35; border:1px solid #263352; border-radius:12px; padding:20px 24px; margin-bottom:20px; display:flex; align-items:center; gap:16px;">
      <div style="width:64px; height:64px; border-radius:50%; border:5px solid {score_col}; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
        <span style="font-family:monospace; font-size:20px; font-weight:700; color:{score_col};">{score}</span>
      </div>
      <div>
        <p style="font-size:15px; font-weight:600; color:#f1f5f9; margin:0 0 4px;">{score_label}</p>
        <p style="font-size:13px; color:#94a3b8; margin:0;">{summary}</p>
      </div>
    </div>

    <!-- Findings -->
    <div style="background:#141f35; border:1px solid #263352; border-radius:12px; overflow:hidden; margin-bottom:24px;">
      <div style="padding:14px 16px; border-bottom:1px solid #263352;">
        <p style="font-size:12px; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:.08em; margin:0;">Hallazgos detectados</p>
      </div>
      <table style="width:100%; border-collapse:collapse;">
        {findings_html}
      </table>
    </div>

    <!-- CTA -->
    <div style="text-align:center; margin-bottom:32px;">
      <a href="{report_url}" style="display:inline-block; background:#14b8a6; color:#0b1120; font-weight:700;
        font-size:15px; padding:12px 28px; border-radius:8px; text-decoration:none;">
        Ver informe completo →
      </a>
    </div>

    <!-- Footer -->
    <p style="font-size:12px; color:#334155; text-align:center;">
      Odoo Pulse · Este email se ha generado automáticamente al completarse el análisis.
    </p>
  </div>
</body>
</html>
"""

    resend.Emails.send({
        "from": "Odoo Pulse <onboarding@resend.dev>",
        "to": [settings.notification_email],
        "subject": f"🔔 Nuevo lead — {company_name} (score {score})",
        "html": html,
    })
