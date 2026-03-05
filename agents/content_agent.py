"""ContentAgent — генерація PDF комерційної пропозиції та email тексту."""

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
    """Генерує PDF КП та email текст."""

    def __init__(self):
        pass

    def generate(self, lead: Lead, analysis: Dict[str, Any], output_dir: str, tariffs=None) -> Dict[str, str]:
        """Генерує PDF та email.txt. Повертає шляхи до файлів."""
        os.makedirs(output_dir, exist_ok=True)

        pdf_path = os.path.join(output_dir, "proposal.pdf")
        email_path = os.path.join(output_dir, "email.txt")

        self._generate_pdf(lead, analysis, pdf_path, tariffs)
        self._generate_email(lead, analysis, email_path)

        return {"pdf": pdf_path, "email": email_path}

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

    def _generate_pdf(self, lead: Lead, analysis: Dict[str, Any], path: str, tariffs=None):
        """Generate PDF from HTML using WeasyPrint, fallback to ReportLab."""
        html = self._generate_html_proposal(lead, analysis, tariffs)

        try:
            from weasyprint import HTML
            HTML(string=html).write_pdf(path)
            logger.info(f"PDF generated via WeasyPrint: {path}")
        except Exception as e:
            logger.warning(f"WeasyPrint failed: {e}, falling back to ReportLab")
            self._generate_pdf_reportlab(lead, analysis, path, tariffs)

    def _generate_pdf_reportlab(self, lead: Lead, analysis: Dict[str, Any], path: str, tariffs=None):
        """Fallback PDF generation using ReportLab."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.colors import HexColor
        from reportlab.lib.units import mm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        BLUE = HexColor("#1B3A6B")
        ORANGE = HexColor("#E8730A")
        WHITE = HexColor("#FFFFFF")
        LIGHT_GRAY = HexColor("#F5F5F5")
        DARK_TEXT = HexColor("#333333")

        # Register font
        font = "Helvetica"
        font_bold = "Helvetica-Bold"
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
            os.path.join(os.path.dirname(__file__), "..", "fonts", "DejaVuSans.ttf"),
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    pdfmetrics.registerFont(TTFont("DejaVuSans", fp))
                    bold_fp = fp.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")
                    if os.path.exists(bold_fp):
                        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", bold_fp))
                    font = "DejaVuSans"
                    font_bold = "DejaVuSans-Bold" if os.path.exists(bold_fp) else font
                except Exception:
                    pass
                break

        doc = SimpleDocTemplate(path, pagesize=A4, topMargin=15*mm, bottomMargin=15*mm, leftMargin=20*mm, rightMargin=20*mm)
        styles = getSampleStyleSheet()
        s_title = ParagraphStyle("T", parent=styles["Title"], fontName=font_bold, fontSize=22, textColor=BLUE, alignment=TA_CENTER, spaceAfter=2*mm)
        s_subtitle = ParagraphStyle("S", parent=styles["Normal"], fontName=font, fontSize=11, textColor=ORANGE, alignment=TA_CENTER, spaceAfter=6*mm)
        s_hook = ParagraphStyle("H", parent=styles["Title"], fontName=font_bold, fontSize=18, textColor=ORANGE, alignment=TA_CENTER, spaceBefore=4*mm, spaceAfter=6*mm)
        s_heading = ParagraphStyle("Hd", parent=styles["Heading2"], fontName=font_bold, fontSize=14, textColor=BLUE, spaceBefore=6*mm, spaceAfter=3*mm)
        s_body = ParagraphStyle("B", parent=styles["Normal"], fontName=font, fontSize=10, textColor=DARK_TEXT, leading=14, alignment=TA_JUSTIFY, spaceAfter=2*mm)
        s_pain_title = ParagraphStyle("PT", parent=styles["Normal"], fontName=font_bold, fontSize=10, textColor=ORANGE, spaceAfter=1*mm)
        s_benefit = ParagraphStyle("BN", parent=styles["Normal"], fontName=font_bold, fontSize=10, textColor=BLUE, spaceAfter=1*mm)
        s_accent = ParagraphStyle("A", parent=styles["Normal"], fontName=font_bold, fontSize=12, textColor=ORANGE, alignment=TA_CENTER, spaceAfter=2*mm)
        s_footer = ParagraphStyle("F", parent=styles["Normal"], fontName=font, fontSize=9, textColor=BLUE, alignment=TA_CENTER)
        s_contact = ParagraphStyle("C", parent=styles["Normal"], fontName=font, fontSize=9, textColor=DARK_TEXT, alignment=TA_CENTER, spaceAfter=1*mm)

        elements = []
        elements.append(Paragraph("MTP Fulfillment", s_title))
        elements.append(Paragraph(f"Комерцiйна пропозицiя для {lead.name}", s_subtitle))
        elements.append(HRFlowable(width="100%", thickness=2, color=ORANGE, spaceAfter=4*mm))
        elements.append(Paragraph(analysis.get("hook", f"{lead.name}: час масштабуватись"), s_hook))

        ci = analysis.get("client_insight", "")
        if ci:
            elements.append(Paragraph("Ми розумiємо вашу специфiку", s_heading))
            elements.append(Paragraph(ci, s_body))

        for pain in analysis.get("pain_points", []):
            if isinstance(pain, dict):
                elements.append(Paragraph(f"▸ {pain.get('title', '')}", s_pain_title))
                elements.append(Paragraph(pain.get("description", ""), s_body))

        mtp_fit = analysis.get("mtp_fit", "")
        if mtp_fit:
            elements.append(Paragraph("Чому МТП", s_heading))
            elements.append(Paragraph(mtp_fit, s_body))
        for kb in analysis.get("key_benefits", []):
            if isinstance(kb, dict):
                elements.append(Paragraph(f"✓ {kb.get('benefit', '')}", s_benefit))
                elements.append(Paragraph(kb.get("proof", ""), s_body))

        # Tariffs
        elements.append(Paragraph("Тарифи MTP Fulfillment", s_heading))
        tariff_rows = [["Послуга", "Тариф"]] + [list(r) for r in _build_tariffs_rows(tariffs)]
        table = Table(tariff_rows, colWidths=[100*mm, 60*mm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLUE), ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), font_bold), ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("FONTNAME", (0, 1), (-1, -1), font), ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_GRAY, WHITE]),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)

        # CTA
        elements.append(Spacer(1, 6*mm))
        elements.append(Paragraph(analysis.get("zoom_cta", "Zoom-консультацiя"), s_accent))
        elements.append(Spacer(1, 4*mm))
        for c in ["mtpgrouppromo@gmail.com | +38 (050) 144-46-45", "fulfillmentmtp.com.ua | @nikolay_mtp"]:
            elements.append(Paragraph(c, s_contact))
        elements.append(Paragraph("© MTP Fulfillment — 7+ рокiв, 60 000+ вiдправок/мiс", s_footer))
        doc.build(elements)
        logger.info(f"PDF generated via ReportLab fallback: {path}")

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
