"""ContentAgent — генерація HTML презентації та email тексту."""

import os
import re
import logging
from typing import Dict, Any
from datetime import datetime

from .research_agent import Lead

logger = logging.getLogger(__name__)

HARDCODED_TARIFFS_TABLE = [
    ("Прийом товару", "2 грн / одиниця"),
    ("Зберігання (паллет)", "800 грн / місяць"),
    ("Зберігання (коробка)", "80 грн / місяць"),
    ("Комплектація B2C (1-3 од.)", "22 грн / замовлення"),
    ("Комплектація B2B", "45 грн / замовлення"),
    ("Пакування", "8 грн / замовлення"),
    ("Відправка Новою Поштою", "за тарифом НП"),
]


def _build_tariffs_rows(tariffs=None):
    """Build tariff rows from DB tariffs or fallback to hardcoded."""
    if not tariffs:
        return HARDCODED_TARIFFS_TABLE

    rows = []
    for t in tariffs:
        name = t["service_name"]
        price = t["price"]
        unit = t.get("unit", "")
        note = t.get("note", "")
        if price > 0:
            tariff_str = f"{int(price)} грн / {unit}" if unit else f"{int(price)} грн"
        elif note:
            tariff_str = note
        else:
            continue
        rows.append((name, tariff_str))
    return rows if rows else HARDCODED_TARIFFS_TABLE


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


class ContentAgent:
    """Генерує HTML презентацію та email текст."""

    def __init__(self):
        pass

    def generate(self, lead: Lead, analysis: Dict[str, Any], output_dir: str, tariffs=None) -> Dict[str, str]:
        """Генерує HTML презентацію та email.txt. Повертає шляхи до файлів."""
        os.makedirs(output_dir, exist_ok=True)

        html_path = os.path.join(output_dir, "proposal.html")
        email_path = os.path.join(output_dir, "email.txt")

        html = self._generate_html_proposal(lead, analysis, tariffs)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"HTML presentation saved: {html_path}")

        self._generate_email(lead, analysis, email_path)

        return {"html": html_path, "email": email_path}

    def _generate_html_proposal(self, lead: Lead, analysis: Dict[str, Any], tariffs=None) -> str:
        """Generate HTML string for the commercial proposal."""
        primary = "#1a1a2e"
        # Try to use a brand color from website scraping (stored in analysis metadata)
        # Default to dark blue if not available

        hook = _escape_html(analysis.get("hook", f"{lead.name}: час масштабуватись"))
        client_insight = _escape_html(analysis.get("client_insight", ""))
        mtp_fit = _escape_html(analysis.get("mtp_fit", ""))
        zoom_cta = _escape_html(analysis.get("zoom_cta", "Запишіться на безкоштовну Zoom-консультацію!"))
        date_str = datetime.now().strftime("%d.%m.%Y")
        client_name = _escape_html(lead.name)

        # Pain points HTML
        pain_points = analysis.get("pain_points", [])
        pains_html = ""
        for p in pain_points:
            if isinstance(p, dict):
                title = _escape_html(p.get("title", ""))
                desc = _escape_html(p.get("description", ""))
                pains_html += f"""
                <div class="pain-item">
                    <div class="pain-icon">&#9679;</div>
                    <div>
                        <div class="pain-title">{title}</div>
                        <div class="pain-desc">{desc}</div>
                    </div>
                </div>"""
            else:
                pains_html += f"""
                <div class="pain-item">
                    <div class="pain-icon">&#9679;</div>
                    <div class="pain-desc">{_escape_html(str(p))}</div>
                </div>"""

        # Key benefits HTML
        key_benefits = analysis.get("key_benefits", [])
        benefits_html = ""
        for kb in key_benefits:
            if isinstance(kb, dict):
                benefit = _escape_html(kb.get("benefit", ""))
                proof = _escape_html(kb.get("proof", ""))
                benefits_html += f"""
                <div class="benefit-card">
                    <div class="benefit-title">{benefit}</div>
                    <div class="benefit-proof">{proof}</div>
                </div>"""
            else:
                benefits_html += f"""
                <div class="benefit-card">
                    <div class="benefit-title">{_escape_html(str(kb))}</div>
                </div>"""

        # Tariffs table rows
        tariff_rows = _build_tariffs_rows(tariffs)
        tariffs_html = ""
        for i, (name, price) in enumerate(tariff_rows):
            tariffs_html += f"""
            <tr>
                <td>{_escape_html(name)}</td>
                <td>{_escape_html(price)}</td>
            </tr>"""

        # Pricing estimate
        pricing = analysis.get("pricing_estimate", {})
        pricing_html = ""
        if pricing:
            pricing_html = '<div class="section-title">Орієнтовний кошторис</div><table class="pricing-table">'
            items = list(pricing.items())
            for i, (key, val) in enumerate(items):
                label = key.replace("_", " ").capitalize()
                cls = ' class="total-row"' if i == len(items) - 1 else ""
                pricing_html += f"<tr{cls}><td>{_escape_html(label)}</td><td>{_escape_html(str(val))}</td></tr>"
            pricing_html += "</table>"

        # MTP fit section
        mtp_fit_html = f"<p>{mtp_fit}</p>" if mtp_fit else ""

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');

  @page {{
    size: A4;
    margin: 0;
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: 'Inter', 'DejaVu Sans', sans-serif;
    background: #ffffff;
    color: #1a1a1a;
    width: 210mm;
    min-height: 297mm;
    padding: 0;
    font-size: 13px;
    line-height: 1.5;
  }}

  /* HEADER */
  .header {{
    background: {primary};
    color: white;
    padding: 40px 50px 30px;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }}
  .header-left .company {{
    font-size: 13px;
    opacity: 0.7;
    text-transform: uppercase;
    letter-spacing: 2px;
  }}
  .header-left .client {{
    font-size: 28px;
    font-weight: 900;
    margin-top: 8px;
  }}
  .header-right {{
    text-align: right;
    font-size: 12px;
    opacity: 0.7;
  }}

  /* HOOK */
  .hook-section {{
    background: #f8f9fa;
    padding: 35px 50px;
    border-left: 5px solid {primary};
  }}
  .hook-text {{
    font-size: 22px;
    font-weight: 700;
    line-height: 1.4;
    color: #1a1a1a;
  }}

  /* CONTENT */
  .content {{
    padding: 25px 50px 30px;
  }}

  /* SECTION TITLE */
  .section-title {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #888;
    margin-bottom: 15px;
    margin-top: 25px;
  }}
  .section-title:first-child {{
    margin-top: 0;
  }}

  .insight {{
    font-size: 14px;
    color: #333;
    line-height: 1.6;
    margin-bottom: 5px;
  }}

  /* PAIN POINTS */
  .pain-item {{
    display: flex;
    gap: 15px;
    margin-bottom: 12px;
    align-items: flex-start;
  }}
  .pain-icon {{
    color: {primary};
    font-size: 10px;
    margin-top: 4px;
    flex-shrink: 0;
  }}
  .pain-title {{
    font-weight: 600;
    font-size: 14px;
  }}
  .pain-desc {{
    font-size: 13px;
    color: #555;
    margin-top: 3px;
    line-height: 1.5;
  }}

  /* BENEFITS */
  .benefits-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-top: 10px;
  }}
  .benefit-card {{
    background: #f8f9fa;
    border-radius: 8px;
    padding: 15px;
    border-left: 3px solid {primary};
  }}
  .benefit-title {{
    font-weight: 600;
    font-size: 13px;
  }}
  .benefit-proof {{
    font-size: 12px;
    color: #666;
    margin-top: 4px;
    font-style: italic;
  }}

  /* TARIFFS TABLE */
  .pricing-table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
    font-size: 13px;
  }}
  .pricing-table tr:nth-child(even) {{
    background: #f8f9fa;
  }}
  .pricing-table td {{
    padding: 8px 12px;
    border-bottom: 1px solid #eee;
  }}
  .pricing-table td:last-child {{
    text-align: right;
    font-weight: 600;
    color: {primary};
  }}
  .pricing-table tr.total-row {{
    background: #e8f0fe;
    font-weight: 700;
  }}

  /* CTA */
  .cta-section {{
    background: {primary};
    color: white;
    padding: 25px 50px;
    margin-top: 20px;
    text-align: center;
  }}
  .cta-text {{
    font-size: 16px;
    font-weight: 700;
    line-height: 1.5;
  }}

  /* FOOTER */
  .footer {{
    padding: 20px 50px;
    text-align: center;
    font-size: 12px;
    color: #888;
    border-top: 1px solid #eee;
  }}
  .footer .contacts {{
    font-size: 13px;
    color: #444;
    margin-bottom: 8px;
  }}
</style>
</head>
<body>

  <div class="header">
    <div class="header-left">
      <div class="company">MTP Fulfillment</div>
      <div class="client">{client_name}</div>
    </div>
    <div class="header-right">
      Комерційна пропозиція<br>
      {date_str}
    </div>
  </div>

  <div class="hook-section">
    <div class="hook-text">{hook}</div>
  </div>

  <div class="content">
    {"<div class='section-title'>Ми розуміємо вашу специфіку</div><p class='insight'>" + client_insight + "</p>" if client_insight else ""}

    {"<div class='section-title'>Де зазвичай втрачається ефективність</div>" + pains_html if pains_html else ""}

    {"<div class='section-title'>Чому МТП</div>" + mtp_fit_html if mtp_fit else ""}

    {"<div class='section-title'>Ключові переваги</div><div class='benefits-grid'>" + benefits_html + "</div>" if benefits_html else ""}

    <div class="section-title">Тарифи MTP Fulfillment</div>
    <table class="pricing-table">
      {tariffs_html}
    </table>

    {pricing_html}
  </div>

  <div class="cta-section">
    <div class="cta-text">{zoom_cta}</div>
  </div>

  <div class="footer">
    <div class="contacts">
      mtpgrouppromo@gmail.com &nbsp;|&nbsp; +38 (050) 144-46-45 &nbsp;|&nbsp; fulfillmentmtp.com.ua &nbsp;|&nbsp; @nikolay_mtp
    </div>
    MTP Fulfillment — 7+ років на ринку, 60 000+ відправок на місяць
  </div>

</body>
</html>"""
        return html

    def _generate_email(self, lead: Lead, analysis: Dict[str, Any], path: str):
        subject = analysis.get("email_subject", f"{lead.name}, пропозиція від MTP Fulfillment")
        opening = analysis.get("email_opening", f"Привіт! Ми подивились на {lead.name} і бачимо великий потенціал.")
        client_insight = analysis.get("client_insight", "")
        mtp_fit = analysis.get("mtp_fit", "")
        zoom_cta = analysis.get("zoom_cta", "Запишіться на безкоштовну Zoom-консультацію!")

        # Build pain points text
        pain_lines = []
        for pain in analysis.get("pain_points", []):
            if isinstance(pain, dict):
                pain_lines.append(f"— {pain.get('title', '')}: {pain.get('description', '')}")
            else:
                pain_lines.append(f"— {pain}")
        pains_text = "\n".join(pain_lines)

        # Build benefits text
        benefit_lines = []
        for kb in analysis.get("key_benefits", []):
            if isinstance(kb, dict):
                benefit_lines.append(f"✓ {kb.get('benefit', '')} — {kb.get('proof', '')}")
            else:
                benefit_lines.append(f"✓ {kb}")
        benefits_text = "\n".join(benefit_lines)

        body = f"""Тема: {subject}

{opening}

{client_insight}

Знайомі ситуації?
{pains_text}

{mtp_fit}

Що ви отримаєте з МТП:
{benefits_text}

{zoom_cta}

У додатку — детальна комерційна пропозиція з тарифами та кошторисом для {lead.name}.

Микола
MTP Fulfillment
mtpgrouppromo@gmail.com | +38 (050) 144-46-45
fulfillmentmtp.com.ua | @nikolay_mtp
"""

        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
