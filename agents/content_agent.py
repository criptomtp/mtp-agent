"""ContentAgent — генерація HTML презентації, PPTX та email тексту."""

import os
import re
import logging
import requests
from typing import Dict, Any, Optional
from datetime import datetime

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

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

    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        self._api_keys = api_keys or {}

    def generate(self, lead: Lead, analysis: Dict[str, Any], output_dir: str,
                 tariffs=None, brand_style: Optional[Dict[str, str]] = None, niche: str = "") -> Dict[str, str]:
        """Генерує HTML, PPTX та email.txt. Повертає шляхи до файлів."""
        os.makedirs(output_dir, exist_ok=True)

        html_path = os.path.join(output_dir, "proposal.html")
        email_path = os.path.join(output_dir, "email.txt")
        safe_name = re.sub(r"[^\w\s-]", "", lead.name).strip().replace(" ", "_")[:50]
        pptx_path = os.path.join(output_dir, f"{safe_name}_proposal.pptx")

        html = self._generate_html_proposal(lead, analysis, tariffs)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"HTML presentation saved: {html_path}")

        # PPTX generation
        try:
            prs = self._generate_pptx_proposal(lead, analysis, tariffs)
            prs.save(pptx_path)
            logger.info(f"PPTX presentation saved: {pptx_path}")
        except Exception as e:
            logger.error(f"PPTX generation failed: {e}", exc_info=True)
            pptx_path = ""

        self._generate_email(lead, analysis, email_path)

        # Web proposal — Gemini generates unique HTML
        web_proposal = None
        try:
            web_proposal = self.create_web_proposal(lead, analysis, brand_style=brand_style,
                                                     tariffs=tariffs, niche=niche)
        except Exception as e:
            logger.error(f"Web proposal creation failed: {e}", exc_info=True)

        result = {"html": html_path, "email": email_path, "pptx": pptx_path}
        if web_proposal:
            result["web_url"] = web_proposal["url"]
            result["web_proposal"] = web_proposal
        return result

    def create_web_proposal(self, lead: "Lead", analysis: Dict[str, Any],
                            brand_style: Optional[Dict[str, str]] = None,
                            tariffs=None, niche: str = "") -> Optional[Dict[str, str]]:
        """Generate unique HTML proposal via Gemini AI and upload to Supabase Storage.

        Returns {'slug': ..., 'url': ..., 'proposal_id': ...} or None on error.
        """
        import uuid
        import hashlib

        api_key = self._api_keys.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("[ContentAgent] GEMINI_API_KEY not set, cannot generate web proposal")
            return None

        # Build analysis text
        pain_points = analysis.get("pain_points", [])
        pain_titles = []
        for p in pain_points:
            if isinstance(p, dict):
                pain_titles.append(p.get("title", ""))
            else:
                pain_titles.append(str(p))

        benefits = analysis.get("key_benefits", [])
        benefit_titles = []
        for b in benefits:
            if isinstance(b, dict):
                benefit_titles.append(b.get("benefit", ""))
            else:
                benefit_titles.append(str(b))

        score = analysis.get("score", 0)
        grade = analysis.get("grade", "?")
        analysis_text = (
            f"Потенціал: {score}/10 ({grade}). "
            f"Болі: {', '.join(pain_titles)}. "
            f"Переваги MTP для клієнта: {', '.join(benefit_titles)}"
        )

        # Build tariffs text
        tariff_rows = _build_tariffs_rows(tariffs)
        tariffs_text = ", ".join([f"{name}: {price}" for name, price in tariff_rows])

        # Brand style
        bs = brand_style or {}
        brand_primary = bs.get("primary_color", "#1A365D")
        brand_secondary = bs.get("secondary_color", "#E53E3E")
        brand_font = bs.get("font_family", "Inter")

        # Generate slug
        slug = hashlib.md5(f"{lead.name}-{datetime.now().isoformat()}".encode()).hexdigest()[:12]

        calendly_url = "https://calendly.com/mtpfulfillment/30min"
        client_name = lead.name
        website = getattr(lead, "website", "") or ""
        city = getattr(lead, "city", "") or ""
        niche_text = niche or "e-commerce"
        api_base = os.getenv("MTP_API_URL", "https://mtp-agent-production.up.railway.app")

        prompt = f"""Ти — топовий UX/UI дизайнер і копірайтер. Створи повну HTML-сторінку комерційної пропозиції від MTP Fulfillment для клієнта.

КЛІЄНТ:
- Назва: {client_name}
- Ніша: {niche_text}
- Сайт: {website}
- Місто: {city}
- Аналіз (болі, потенціал): {analysis_text}
- Фірмовий стиль клієнта: primary={brand_primary}, secondary={brand_secondary}, font={brand_font}

MTP FULFILLMENT (продавець):
- Компанія: MTP Group Fulfillment, Бориспіль (біля Київ)
- Колір бренду: #E53E3E (червоний), білий
- 7+ років на ринку, 60K+ відправок/міс, 2 склади
- Тарифи: {tariffs_text}
- Контакти: mtpgrouppromo@gmail.com, +38 (050) 144-46-45, fulfillmentmtp.com.ua
- Calendly: {calendly_url}

ЗАВДАННЯ:
Створи УНІКАЛЬНУ HTML сторінку яка:
1. Використовує фірмові кольори КЛІЄНТА як основну палітру ({brand_primary} як домінантний)
2. Додає MTP червоний (#E53E3E) як акцентний колір на CTA кнопках і важливих елементах
3. Має УНІКАЛЬНУ структуру і layout — НЕ стандартний шаблон. Придумай щось оригінальне для цього клієнта
4. Пише УНІКАЛЬНИЙ текст під цю нішу і цього клієнта — не загальні фрази
5. Включає секції (але в унікальному порядку і стилі): hero з назвою клієнта, болі бізнесу, рішення від MTP, тарифи, соціальний доказ (KRKR/ORNER/ELEMIS), CTA
6. Адаптивна (mobile-friendly)
7. Без зовнішніх залежностей (тільки Google Fonts дозволені)
8. Tracking: при завантаженні fetch('{api_base}/api/proposals/track', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{slug:'{slug}', event:'open'}})}})\

ВАЖЛИВО: Поверни ТІЛЬКИ валідний HTML від <!DOCTYPE html> до </html>. Без markdown, без пояснень."""

        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)
            html = response.text.strip()

            # Strip markdown fences if present
            if html.startswith("```"):
                html = html.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            # Validate HTML
            if not html.startswith("<!DOCTYPE html>") and not html.startswith("<!doctype html>"):
                # Try to find DOCTYPE in response
                idx = html.lower().find("<!doctype html>")
                if idx >= 0:
                    html = html[idx:]
                else:
                    logger.error("[ContentAgent] Gemini response is not valid HTML")
                    return None

            logger.info(f"[ContentAgent] Gemini generated {len(html)} bytes of unique HTML for {client_name}")

        except Exception as e:
            logger.error(f"[ContentAgent] Gemini HTML generation failed: {e}", exc_info=True)
            return None

        # Upload to Supabase Storage
        try:
            from backend.services.database import get_supabase, upload_to_storage

            storage_path = f"web/{slug}/index.html"
            storage_url = upload_to_storage("proposals", storage_path, html.encode("utf-8"),
                                            content_type="text/html; charset=utf-8")

            if not storage_url:
                logger.error("[ContentAgent] Failed to upload HTML to Supabase Storage")
                return None

            # Save proposal record to DB
            db = get_supabase()
            proposal_data = {
                "slug": slug,
                "client_name": client_name,
                "html_url": storage_url,
                "client_data": {
                    "niche": niche_text,
                    "website": website,
                    "city": city,
                    "score": score,
                    "grade": grade,
                    "brand_style": bs,
                },
            }
            try:
                db.table("proposals").insert(proposal_data).execute()
            except Exception as e:
                logger.warning(f"[ContentAgent] Could not save proposal record: {e}")

            frontend_url = os.getenv("MTP_FRONTEND_URL", "https://mtp-lead-agent.vercel.app")
            url = f"{frontend_url}/proposals/{slug}"

            logger.info(f"[ContentAgent] Web proposal uploaded: {url}")
            return {"slug": slug, "url": url, "proposal_id": slug}

        except Exception as e:
            logger.error(f"[ContentAgent] Supabase upload failed: {e}", exc_info=True)
            return None

    # ── PPTX helpers ──

    @staticmethod
    def _pptx_add_bg(slide, prs, color):
        """Add a full-slide background rectangle."""
        from pptx.util import Emu
        from pptx.enum.shapes import MSO_SHAPE
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = color
        bg.line.fill.background()

    @staticmethod
    def _pptx_text_box(slide, left, top, width, height, text, font_size=18, bold=False,
                       color=RGBColor(0xFF, 0xFF, 0xFF), alignment=PP_ALIGN.LEFT, font_name="Calibri"):
        """Add a text box with styled text."""
        txBox = slide.shapes.add_textbox(left, top, width, height)
        tf = txBox.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = str(text)
        p.font.size = Pt(font_size)
        p.font.bold = bold
        p.font.color.rgb = color
        p.font.name = font_name
        p.alignment = alignment
        return tf

    def _generate_pptx_proposal(self, lead: Lead, analysis: Dict[str, Any], tariffs=None):
        """Generate 6-slide dark-themed PPTX presentation."""
        BG = RGBColor(0x0F, 0x20, 0x44)
        BG_CARD = RGBColor(0x16, 0x2D, 0x5A)
        ACCENT = RGBColor(0x00, 0xB4, 0xD8)
        MINT = RGBColor(0x06, 0xD6, 0xA0)
        WHITE = RGBColor(0xFF, 0xFF, 0xFF)
        LIGHT = RGBColor(0xBB, 0xBB, 0xCC)
        ORANGE = RGBColor(0xFF, 0x6B, 0x35)

        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)
        blank_layout = prs.slide_layouts[6]

        W = prs.slide_width
        H = prs.slide_height
        MARGIN = Inches(0.8)
        CONTENT_W = W - 2 * MARGIN

        date_str = datetime.now().strftime("%d.%m.%Y")
        hook = analysis.get("hook", f"{lead.name}: час масштабуватись")
        client_insight = analysis.get("client_insight", "")
        zoom_cta = analysis.get("zoom_cta", "Запишіться на безкоштовну Zoom-консультацію!")

        # ── SLIDE 1: Hero ──
        slide = prs.slides.add_slide(blank_layout)
        self._pptx_add_bg(slide, prs, BG)
        self._pptx_text_box(slide, MARGIN, Inches(1.0), CONTENT_W, Inches(0.6),
                            "MTP FULFILLMENT", font_size=14, color=ACCENT, bold=True)
        self._pptx_text_box(slide, MARGIN, Inches(2.0), CONTENT_W, Inches(1.5),
                            lead.name, font_size=48, bold=True, color=WHITE)
        subtitle = f"Комерційна пропозиція"
        if lead.city:
            subtitle += f"  •  {lead.city}"
        self._pptx_text_box(slide, MARGIN, Inches(3.8), CONTENT_W, Inches(0.6),
                            subtitle, font_size=20, color=LIGHT)
        self._pptx_text_box(slide, MARGIN, Inches(6.2), CONTENT_W, Inches(0.5),
                            date_str, font_size=14, color=LIGHT, alignment=PP_ALIGN.RIGHT)
        # Accent line
        from pptx.enum.shapes import MSO_SHAPE
        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, MARGIN, Inches(3.5), Inches(3), Pt(4))
        line.fill.solid()
        line.fill.fore_color.rgb = ACCENT
        line.line.fill.background()

        # ── SLIDE 2: Insight ──
        slide = prs.slides.add_slide(blank_layout)
        self._pptx_add_bg(slide, prs, BG)
        self._pptx_text_box(slide, MARGIN, Inches(0.5), CONTENT_W, Inches(0.4),
                            "ПРО НАС", font_size=12, color=ACCENT, bold=True)
        # Stats row
        stats = [("7+", "років на ринку"), ("60K+", "відправок / міс"), ("2", "склади під Києвом"), ("30с", "середній час обробки")]
        stat_w = Inches(2.8)
        for i, (num, label) in enumerate(stats):
            x = MARGIN + Emu(int(i * stat_w))
            self._pptx_text_box(slide, x, Inches(1.2), stat_w, Inches(0.8),
                                num, font_size=44, bold=True, color=MINT)
            self._pptx_text_box(slide, x, Inches(2.0), stat_w, Inches(0.5),
                                label, font_size=13, color=LIGHT)
        # Insight text
        if client_insight:
            self._pptx_text_box(slide, MARGIN, Inches(3.2), CONTENT_W, Inches(0.4),
                                "МИ РОЗУМІЄМО ВАШУ СПЕЦИФІКУ", font_size=12, color=ACCENT, bold=True)
            self._pptx_text_box(slide, MARGIN, Inches(3.8), CONTENT_W, Inches(2.5),
                                client_insight, font_size=18, color=WHITE)

        # ── SLIDE 3: Pain Points ──
        slide = prs.slides.add_slide(blank_layout)
        self._pptx_add_bg(slide, prs, BG)
        self._pptx_text_box(slide, MARGIN, Inches(0.5), CONTENT_W, Inches(0.4),
                            "ДЕ ВТРАЧАЄТЬСЯ ЕФЕКТИВНІСТЬ", font_size=12, color=ACCENT, bold=True)
        pain_points = analysis.get("pain_points", [])
        card_w = Inches(3.6)
        card_h = Inches(3.8)
        gap = Inches(0.4)
        for i, p in enumerate(pain_points[:3]):
            x = MARGIN + Emu(int(i * (card_w + gap)))
            # Card background
            card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, Inches(1.3), card_w, card_h)
            card.fill.solid()
            card.fill.fore_color.rgb = BG_CARD
            card.line.fill.background()
            # Number
            self._pptx_text_box(slide, x + Inches(0.3), Inches(1.6), Inches(1), Inches(0.7),
                                f"0{i+1}", font_size=36, bold=True, color=ACCENT)
            # Title & description
            if isinstance(p, dict):
                title = p.get("title", "")
                desc = p.get("description", "")
            else:
                title = str(p)
                desc = ""
            self._pptx_text_box(slide, x + Inches(0.3), Inches(2.5), card_w - Inches(0.6), Inches(0.6),
                                title, font_size=16, bold=True, color=WHITE)
            if desc:
                self._pptx_text_box(slide, x + Inches(0.3), Inches(3.2), card_w - Inches(0.6), Inches(1.5),
                                    desc, font_size=13, color=LIGHT)

        # ── SLIDE 4: Benefits ──
        slide = prs.slides.add_slide(blank_layout)
        self._pptx_add_bg(slide, prs, BG)
        self._pptx_text_box(slide, MARGIN, Inches(0.5), CONTENT_W, Inches(0.4),
                            "КЛЮЧОВІ ПЕРЕВАГИ", font_size=12, color=ACCENT, bold=True)
        benefits = analysis.get("key_benefits", [])
        b_w = Inches(5.5)
        b_h = Inches(2.2)
        b_gap_x = Inches(0.5)
        b_gap_y = Inches(0.4)
        for i, kb in enumerate(benefits[:4]):
            col = i % 2
            row = i // 2
            x = MARGIN + Emu(int(col * (b_w + b_gap_x)))
            y = Inches(1.3) + Emu(int(row * (b_h + b_gap_y)))
            # Card
            card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, b_w, b_h)
            card.fill.solid()
            card.fill.fore_color.rgb = BG_CARD
            card.line.fill.background()
            # Accent stripe
            stripe = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, Pt(5), b_h)
            stripe.fill.solid()
            stripe.fill.fore_color.rgb = MINT
            stripe.line.fill.background()
            if isinstance(kb, dict):
                benefit = kb.get("benefit", "")
                proof = kb.get("proof", "")
            else:
                benefit = str(kb)
                proof = ""
            self._pptx_text_box(slide, x + Inches(0.4), y + Inches(0.3), b_w - Inches(0.7), Inches(0.6),
                                benefit, font_size=16, bold=True, color=WHITE)
            if proof:
                self._pptx_text_box(slide, x + Inches(0.4), y + Inches(1.0), b_w - Inches(0.7), Inches(1.0),
                                    proof, font_size=13, color=LIGHT)

        # ── SLIDE 5: Pricing ──
        slide = prs.slides.add_slide(blank_layout)
        self._pptx_add_bg(slide, prs, BG)
        self._pptx_text_box(slide, MARGIN, Inches(0.5), CONTENT_W, Inches(0.4),
                            "ТАРИФИ MTP FULFILLMENT", font_size=12, color=ACCENT, bold=True)
        tariff_rows = _build_tariffs_rows(tariffs)
        rows_count = len(tariff_rows) + 1
        cols = 2
        tbl_w = Inches(7)
        tbl = slide.shapes.add_table(rows_count, cols, MARGIN, Inches(1.3), tbl_w, Inches(0.45 * rows_count)).table
        tbl.columns[0].width = Inches(4.5)
        tbl.columns[1].width = Inches(2.5)
        # Header
        for ci, txt in enumerate(["Послуга", "Тариф"]):
            cell = tbl.cell(0, ci)
            cell.text = txt
            cell.fill.solid()
            cell.fill.fore_color.rgb = ACCENT
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(13)
                p.font.bold = True
                p.font.color.rgb = WHITE
                p.font.name = "Calibri"
        # Rows
        for ri, (name, price) in enumerate(tariff_rows):
            for ci, txt in enumerate([name, price]):
                cell = tbl.cell(ri + 1, ci)
                cell.text = txt
                cell.fill.solid()
                cell.fill.fore_color.rgb = BG_CARD if ri % 2 == 0 else BG
                for p in cell.text_frame.paragraphs:
                    p.font.size = Pt(12)
                    p.font.color.rgb = WHITE if ci == 0 else MINT
                    p.font.name = "Calibri"
        # Pricing estimate
        pricing = analysis.get("pricing_estimate", {})
        if pricing:
            self._pptx_text_box(slide, Inches(8.5), Inches(1.3), Inches(4), Inches(0.4),
                                "ОРІЄНТОВНИЙ КОШТОРИС", font_size=12, color=ACCENT, bold=True)
            y_off = Inches(2.0)
            if isinstance(pricing, dict):
                for key, val in pricing.items():
                    label = key.replace("_", " ").capitalize()
                    self._pptx_text_box(slide, Inches(8.5), y_off, Inches(2.5), Inches(0.4),
                                        label, font_size=13, color=LIGHT)
                    self._pptx_text_box(slide, Inches(11), y_off, Inches(1.5), Inches(0.4),
                                        str(val), font_size=13, bold=True, color=MINT, alignment=PP_ALIGN.RIGHT)
                    y_off += Inches(0.45)
            else:
                self._pptx_text_box(slide, Inches(8.5), y_off, Inches(4), Inches(1),
                                    str(pricing), font_size=16, color=WHITE)

        # ── SLIDE 6: CTA ──
        slide = prs.slides.add_slide(blank_layout)
        self._pptx_add_bg(slide, prs, BG)
        self._pptx_text_box(slide, MARGIN, Inches(1.5), CONTENT_W, Inches(0.6),
                            "НАСТУПНИЙ КРОК", font_size=14, color=ACCENT, bold=True)
        self._pptx_text_box(slide, MARGIN, Inches(2.3), CONTENT_W, Inches(1.2),
                            zoom_cta, font_size=28, bold=True, color=WHITE)
        # CTA button shape
        btn_w = Inches(4)
        btn_h = Inches(0.8)
        btn_x = Emu(int((W - btn_w) / 2))
        btn = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, btn_x, Inches(4.0), btn_w, btn_h)
        btn.fill.solid()
        btn.fill.fore_color.rgb = ACCENT
        btn.line.fill.background()
        tf = btn.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = "ZOOM-ДЗВІНОК"
        p.font.size = Pt(18)
        p.font.bold = True
        p.font.color.rgb = WHITE
        p.font.name = "Calibri"
        p.alignment = PP_ALIGN.CENTER
        tf.paragraphs[0].space_before = Pt(10)
        # Contacts
        contacts = [
            "mtpgrouppromo@gmail.com  |  +38 (050) 144-46-45",
            "fulfillmentmtp.com.ua  |  @nikolay_mtp",
        ]
        self._pptx_text_box(slide, MARGIN, Inches(5.3), CONTENT_W, Inches(0.5),
                            contacts[0], font_size=14, color=LIGHT, alignment=PP_ALIGN.CENTER)
        self._pptx_text_box(slide, MARGIN, Inches(5.8), CONTENT_W, Inches(0.5),
                            contacts[1], font_size=14, color=LIGHT, alignment=PP_ALIGN.CENTER)
        self._pptx_text_box(slide, MARGIN, Inches(6.5), CONTENT_W, Inches(0.4),
                            "MTP Fulfillment — 7+ років на ринку, 60 000+ відправок на місяць",
                            font_size=11, color=RGBColor(0x66, 0x66, 0x88), alignment=PP_ALIGN.CENTER)

        return prs

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
