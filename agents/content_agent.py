"""ContentAgent — генерація PDF комерційної пропозиції та email тексту."""

import os
from typing import Dict, Any
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .research_agent import Lead

# Корпоративні кольори
BLUE = HexColor("#1B3A6B")
ORANGE = HexColor("#E8730A")
WHITE = HexColor("#FFFFFF")
LIGHT_GRAY = HexColor("#F5F5F5")
DARK_TEXT = HexColor("#333333")

HARDCODED_TARIFFS_TABLE = [
    ["Послуга", "Тариф"],
    ["Прийом товару", "2 грн / одиниця"],
    ["Зберігання (паллет)", "800 грн / місяць"],
    ["Зберігання (коробка)", "80 грн / місяць"],
    ["Комплектація B2C (1-3 од.)", "22 грн / замовлення"],
    ["Комплектація B2B", "45 грн / замовлення"],
    ["Пакування", "8 грн / замовлення"],
    ["Відправка Новою Поштою", "за тарифом НП"],
]


def _build_tariffs_table(tariffs=None):
    """Build tariff table rows from DB tariffs or fallback to hardcoded."""
    if not tariffs:
        return HARDCODED_TARIFFS_TABLE

    rows = [["Послуга", "Тариф"]]
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
        rows.append([name, tariff_str])
    return rows if len(rows) > 1 else HARDCODED_TARIFFS_TABLE


def _register_cyrillic_font() -> str:
    """Реєстрація DejaVu шрифтів для кирилиці з автозавантаженням."""
    search_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/Library/Fonts/DejaVuSans.ttf",
        os.path.expanduser("~/Library/Fonts/DejaVuSans.ttf"),
        os.path.join(os.path.dirname(__file__), "fonts", "DejaVuSans.ttf"),
        os.path.join(os.path.dirname(__file__), "..", "fonts", "DejaVuSans.ttf"),
    ]

    for path in search_paths:
        if os.path.exists(path):
            bold_path = path.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")
            pdfmetrics.registerFont(TTFont("DejaVuSans", path))
            if os.path.exists(bold_path):
                pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", bold_path))
            return "DejaVuSans"

    # Автозавантаження якщо не знайдено
    fonts_dir = os.path.join(os.path.dirname(__file__), "..", "fonts")
    os.makedirs(fonts_dir, exist_ok=True)
    font_path = os.path.join(fonts_dir, "DejaVuSans.ttf")
    bold_path = os.path.join(fonts_dir, "DejaVuSans-Bold.ttf")

    if not os.path.exists(font_path):
        import urllib.request, zipfile, tempfile
        print("[ContentAgent] Завантаження DejaVuSans шрифту...")
        zip_url = "https://github.com/dejavu-fonts/dejavu-fonts/releases/download/version_2_37/dejavu-fonts-ttf-2.37.zip"
        zip_path = os.path.join(tempfile.gettempdir(), "dejavu.zip")
        urllib.request.urlretrieve(zip_url, zip_path)
        with zipfile.ZipFile(zip_path) as z:
            for name in z.namelist():
                basename = os.path.basename(name)
                if basename in ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"):
                    with open(os.path.join(fonts_dir, basename), "wb") as f:
                        f.write(z.read(name))

    pdfmetrics.registerFont(TTFont("DejaVuSans", font_path))
    if os.path.exists(bold_path):
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", bold_path))
    return "DejaVuSans"


FONT_NAME = _register_cyrillic_font()
FONT_BOLD = "DejaVuSans-Bold"


def _get_font_name(bold: bool = False) -> str:
    """Повертає назву шрифту."""
    return FONT_BOLD if bold else FONT_NAME


class ContentAgent:
    """Генерує PDF КП та email текст."""

    def __init__(self):
        self._fonts_registered = bool(FONT_NAME)

    def generate(self, lead: Lead, analysis: Dict[str, Any], output_dir: str, tariffs=None) -> Dict[str, str]:
        """Генерує PDF та email.txt. Повертає шляхи до файлів."""
        os.makedirs(output_dir, exist_ok=True)

        pdf_path = os.path.join(output_dir, "proposal.pdf")
        email_path = os.path.join(output_dir, "email.txt")

        self._generate_pdf(lead, analysis, pdf_path, tariffs)
        self._generate_email(lead, analysis, email_path)

        return {"pdf": pdf_path, "email": email_path}

    def _generate_pdf(self, lead: Lead, analysis: Dict[str, Any], path: str, tariffs=None):
        font = _get_font_name()
        font_bold = _get_font_name(bold=True)

        doc = SimpleDocTemplate(
            path,
            pagesize=A4,
            topMargin=15 * mm,
            bottomMargin=15 * mm,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
        )

        styles = getSampleStyleSheet()

        s_title = ParagraphStyle(
            "MTPTitle", parent=styles["Title"],
            fontName=font_bold, fontSize=22, textColor=BLUE, alignment=TA_CENTER,
            spaceAfter=2 * mm,
        )
        s_subtitle = ParagraphStyle(
            "MTPSubtitle", parent=styles["Normal"],
            fontName=font, fontSize=11, textColor=ORANGE, alignment=TA_CENTER,
            spaceAfter=6 * mm,
        )
        s_hook = ParagraphStyle(
            "MTPHook", parent=styles["Title"],
            fontName=font_bold, fontSize=18, textColor=ORANGE, alignment=TA_CENTER,
            spaceBefore=4 * mm, spaceAfter=6 * mm,
        )
        s_heading = ParagraphStyle(
            "MTPHeading", parent=styles["Heading2"],
            fontName=font_bold, fontSize=14, textColor=BLUE,
            spaceBefore=6 * mm, spaceAfter=3 * mm,
        )
        s_body = ParagraphStyle(
            "MTPBody", parent=styles["Normal"],
            fontName=font, fontSize=10, textColor=DARK_TEXT,
            leading=14, alignment=TA_JUSTIFY, spaceAfter=2 * mm,
        )
        s_pain_title = ParagraphStyle(
            "MTPPainTitle", parent=styles["Normal"],
            fontName=font_bold, fontSize=10, textColor=ORANGE,
            spaceAfter=1 * mm,
        )
        s_benefit = ParagraphStyle(
            "MTPBenefit", parent=styles["Normal"],
            fontName=font_bold, fontSize=10, textColor=BLUE,
            spaceAfter=1 * mm,
        )
        s_accent = ParagraphStyle(
            "MTPAccent", parent=styles["Normal"],
            fontName=font_bold, fontSize=12, textColor=ORANGE,
            alignment=TA_CENTER, spaceAfter=2 * mm,
        )
        s_footer = ParagraphStyle(
            "MTPFooter", parent=styles["Normal"],
            fontName=font, fontSize=9, textColor=BLUE, alignment=TA_CENTER,
        )
        s_contact = ParagraphStyle(
            "MTPContact", parent=styles["Normal"],
            fontName=font, fontSize=9, textColor=DARK_TEXT, alignment=TA_CENTER,
            spaceAfter=1 * mm,
        )

        elements = []

        # 1. Шапка MTP + назва клієнта
        elements.append(Paragraph("MTP Fulfillment", s_title))
        elements.append(Paragraph(
            f"Комерцiйна пропозицiя для {lead.name}",
            s_subtitle,
        ))
        elements.append(HRFlowable(
            width="100%", thickness=2, color=ORANGE, spaceAfter=4 * mm,
        ))

        # 2. Hook
        hook = analysis.get("hook", f"{lead.name}: час масштабуватись")
        elements.append(Paragraph(hook, s_hook))

        # 3. Ми розуміємо вашу специфіку — client_insight
        client_insight = analysis.get("client_insight", "")
        if client_insight:
            elements.append(Paragraph("Ми розумiємо вашу специфiку", s_heading))
            elements.append(Paragraph(client_insight, s_body))

        # 4. Де зазвичай втрачається ефективність — pain_points
        pain_points = analysis.get("pain_points", [])
        if pain_points:
            elements.append(Paragraph("Де зазвичай втрачається ефективнiсть", s_heading))
            for pain in pain_points:
                if isinstance(pain, dict):
                    elements.append(Paragraph(f"▸ {pain.get('title', '')}", s_pain_title))
                    elements.append(Paragraph(pain.get("description", ""), s_body))
                else:
                    elements.append(Paragraph(f"▸ {pain}", s_body))

        # 5. Чому МТП — key_benefits з proof
        mtp_fit = analysis.get("mtp_fit", "")
        key_benefits = analysis.get("key_benefits", [])
        if mtp_fit or key_benefits:
            elements.append(Paragraph("Чому МТП", s_heading))
            if mtp_fit:
                elements.append(Paragraph(mtp_fit, s_body))
                elements.append(Spacer(1, 2 * mm))
            for kb in key_benefits:
                if isinstance(kb, dict):
                    elements.append(Paragraph(f"✓ {kb.get('benefit', '')}", s_benefit))
                    elements.append(Paragraph(kb.get("proof", ""), s_body))

        # 6. Тарифна таблиця
        elements.append(Paragraph("Тарифи MTP Fulfillment", s_heading))
        tariffs_table_data = _build_tariffs_table(tariffs)
        table = Table(tariffs_table_data, colWidths=[100 * mm, 60 * mm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), font_bold),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("FONTNAME", (0, 1), (-1, -1), font),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("TEXTCOLOR", (0, 1), (-1, -1), DARK_TEXT),
            ("BACKGROUND", (0, 1), (-1, -1), LIGHT_GRAY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_GRAY, WHITE]),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 4 * mm))

        # 7. Кошторис
        pricing = analysis.get("pricing_estimate", {})
        if pricing:
            elements.append(Paragraph("Орiєнтовний кошторис", s_heading))
            estimate_data = [["Стаття витрат", "Сума"]]
            for key, val in pricing.items():
                label = key.replace("_", " ").capitalize()
                estimate_data.append([label, str(val)])

            est_table = Table(estimate_data, colWidths=[100 * mm, 60 * mm])
            est_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), ORANGE),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), font_bold),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("FONTNAME", (0, 1), (-1, -1), font),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("BACKGROUND", (0, -1), (-1, -1), HexColor("#FFF3E6")),
                ("FONTNAME", (0, -1), (-1, -1), font_bold),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]))
            elements.append(est_table)

        # 8. CTA на Zoom
        elements.append(Spacer(1, 6 * mm))
        elements.append(HRFlowable(width="100%", thickness=1, color=ORANGE, spaceAfter=4 * mm))
        zoom_cta = analysis.get("zoom_cta", "Запишiться на безкоштовну Zoom-консультацiю!")
        elements.append(Paragraph(zoom_cta, s_accent))

        # 9. Контакти
        elements.append(Spacer(1, 4 * mm))
        elements.append(Paragraph("MTP Fulfillment", ParagraphStyle(
            "ContactTitle", parent=s_body, fontName=font_bold, fontSize=11,
            textColor=BLUE, alignment=TA_CENTER,
        )))
        for c in [
            "mtpgrouppromo@gmail.com | +38 (050) 144-46-45",
            "fulfillmentmtp.com.ua | @nikolay_mtp",
        ]:
            elements.append(Paragraph(c, s_contact))

        elements.append(Spacer(1, 6 * mm))
        elements.append(Paragraph(
            "© MTP Fulfillment — 7+ рокiв на ринку, 60 000+ вiдправок на мiсяць",
            s_footer,
        ))

        doc.build(elements)

    def _generate_email(self, lead: Lead, analysis: Dict[str, Any], path: str):
        subject = analysis.get("email_subject", f"{lead.name}, пропозиція від MTP Fulfillment")
        opening = analysis.get("email_opening", f"Привіт! Ми подивились на {lead.name} і бачимо великий потенціал.")
        hook = analysis.get("hook", "")
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
