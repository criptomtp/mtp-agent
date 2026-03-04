"""AnalysisAgent — аналіз ліда через Gemini/Claude API з веб-скрапінгом."""

import os
import json
import logging
from typing import Dict, Any, List, Optional

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from .research_agent import Lead

load_dotenv()

logger = logging.getLogger(__name__)

HARDCODED_TARIFFS = {
    "розвантаження_коробки": "20 грн/коробка",
    "розвантаження_палети": "80 грн/палета",
    "приймання_розміщення": "3 грн/одиниця (до 2 кг)",
    "доплата_вага_приймання": "0.5 грн/кг понад 2 кг",
    "зберігання": "650 грн/м³/місяць (євро-палета ≈ 1.73 м³)",
    "відвантаження_b2c": "18-26 грн/замовлення",
    "доукомплектація": "2.5 грн/одиниця",
    "доплата_вага_відвантаження": "0.5 грн/кг понад 2 кг",
    "мінімальний_платіж": "5000 грн/місяць",
    "комісія_нп": "10% від суми накладеного платежу",
}


def _format_tariffs_for_prompt(tariffs: Optional[List[Dict[str, Any]]]) -> str:
    """Format DB tariffs or fall back to hardcoded."""
    if tariffs:
        lines = {}
        for t in tariffs:
            name = t["service_name"]
            price = t["price"]
            unit = t.get("unit", "")
            note = t.get("note", "")
            if price > 0:
                lines[name] = f"{int(price)} грн/{unit}" if unit else f"{int(price)} грн"
            elif note:
                lines[name] = note
        if lines:
            return json.dumps(lines, ensure_ascii=False, indent=2)
    return json.dumps(HARDCODED_TARIFFS, ensure_ascii=False, indent=2)


def _scrape_website(url: str) -> Dict[str, str]:
    """Fetch title, meta description, and text excerpt from a website."""
    if not url or not url.startswith("http"):
        return {}
    try:
        resp = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            timeout=10,
            allow_redirects=True,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        title = ""
        if soup.title:
            title = soup.title.get_text(strip=True)

        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag and meta_tag.get("content"):
            meta_desc = meta_tag["content"].strip()

        # Extract visible text excerpt
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)[:2000]

        return {"title": title, "meta_description": meta_desc, "text_excerpt": text}
    except Exception as e:
        logger.debug(f"Website scrape failed for {url}: {e}")
        return {}


def _build_prompt(lead: Lead, tariffs_text: str, website_data: Dict[str, str]) -> str:
    website_section = ""
    if website_data:
        website_section = f"""
Дані з сайту компанії ({lead.website}):
- Заголовок: {website_data.get('title', 'н/д')}
- Мета-опис: {website_data.get('meta_description', 'н/д')}
- Фрагмент тексту: {website_data.get('text_excerpt', 'н/д')[:500]}
"""

    return f"""Ти — бізнес-аналітик компанії MTP Fulfillment (3PL фулфілмент, Бориспіль, Україна).

Проаналізуй потенційного клієнта та поверни JSON (без markdown, тільки чистий JSON):

Клієнт:
- Назва: {lead.name}
- Сайт: {lead.website}
- Місто: {lead.city}
- Опис: {lead.description}
- Кількість товарів: {lead.products_count}
{website_section}
Тарифи MTP:
{tariffs_text}

Поверни JSON з полями:
{{
  "company_analysis": "короткий аналіз компанії та її потреб у фулфілменті (2-3 речення)",
  "mtp_value_proposition": "чому MTP Fulfillment ідеально підходить цьому клієнту (2-3 речення)",
  "pain_points": ["біль 1", "біль 2", "біль 3"],
  "potential": "low / medium / high",
  "pricing_estimate": {{
    "зберігання_місяць": "оцінка в грн",
    "комплектація_місяць": "оцінка в грн (при ~500 замовлень/міс)",
    "пакування_місяць": "оцінка в грн",
    "загалом_місяць": "оцінка загальна в грн"
  }},
  "personalization": "персональне звернення до клієнта для листа (1-2 речення)"
}}"""


class AnalysisAgent:
    """Аналізує ліда через AI API з fallback."""

    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        self._api_keys = api_keys or {}

    def _get_key(self, name: str) -> str | None:
        """Get API key: first from passed dict, then from env."""
        return self._api_keys.get(name) or os.getenv(name.upper())

    def analyze(self, lead: Lead, tariffs: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Аналіз ліда: scrape website → Gemini → Claude → fallback."""
        website_data = _scrape_website(lead.website)
        if website_data:
            logger.info(f"  [AnalysisAgent] Scraped website: {lead.website} (title: {website_data.get('title', '')[:50]})")

        tariffs_text = _format_tariffs_for_prompt(tariffs)

        result = self._try_gemini(lead, tariffs_text, website_data)
        if not result:
            result = self._try_claude(lead, tariffs_text, website_data)
        if not result:
            result = self._fallback_analysis(lead)

        scoring = score_lead(lead, result)
        result["score"] = scoring["score"]
        result["grade"] = scoring["grade"]
        result["score_label"] = scoring["label"]
        result["score_reasons"] = scoring["reasons"]
        return result

    def _try_gemini(self, lead: Lead, tariffs_text: str, website_data: Dict[str, str]) -> Dict[str, Any] | None:
        api_key = self._get_key("GEMINI_API_KEY")
        if not api_key:
            print("  [AnalysisAgent] GEMINI_API_KEY не налаштований.")
            return None

        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(_build_prompt(lead, tariffs_text, website_data))
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(text)
        except Exception as e:
            print(f"  [AnalysisAgent] Gemini помилка: {e}")
            return None

    def _try_claude(self, lead: Lead, tariffs_text: str, website_data: Dict[str, str]) -> Dict[str, Any] | None:
        api_key = self._get_key("ANTHROPIC_API_KEY")
        if not api_key:
            print("  [AnalysisAgent] ANTHROPIC_API_KEY не налаштований.")
            return None

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[{"role": "user", "content": _build_prompt(lead, tariffs_text, website_data)}],
            )
            text = message.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(text)
        except Exception as e:
            print(f"  [AnalysisAgent] Claude помилка: {e}")
            return None

    def _fallback_analysis(self, lead: Lead) -> Dict[str, Any]:
        """Розумний fallback без API."""
        print("  [AnalysisAgent] Використовую fallback аналіз.")

        products = lead.products_count or 500
        storage_m3 = max(1, products // 200)
        orders_month = max(100, products // 5)

        storage_cost = storage_m3 * 650
        picking_cost = orders_month * 22
        total = storage_cost + picking_cost

        city_note = f" з {lead.city}" if lead.city else ""

        return {
            "company_analysis": (
                f"{lead.name} — компанія{city_note}, що працює у сфері косметики. "
                f"{'Має каталог з ' + str(products) + ' товарів. ' if products > 0 else ''}"
                f"Потребує надійного фулфілмент-партнера для зберігання та доставки продукції."
            ),
            "mtp_value_proposition": (
                f"MTP Fulfillment забезпечить {lead.name} повний цикл логістики: "
                f"від прийому товару на склад у Борисполі до доставки кінцевому клієнту через Нову Пошту. "
                f"Це дозволить зосередитись на розвитку бренду та маркетингу."
            ),
            "pain_points": [
                "Витрати часу на пакування та відправку замовлень",
                "Помилки при комплектації та втрата клієнтів",
                "Складнощі з масштабуванням у пікові сезони",
            ],
            "potential": "medium",
            "pricing_estimate": {
                "зберігання_місяць": f"{storage_cost} грн ({storage_m3} м³ × 650 грн)",
                "відвантаження_місяць": f"{picking_cost} грн ({orders_month} замовлень × 22 грн)",
                "загалом_місяць": f"~{total} грн/місяць",
            },
            "personalization": (
                f"Вітаємо, {lead.name}! Ми бачимо великий потенціал у співпраці — "
                f"наш склад у Борисполі ідеально підходить для швидкої доставки косметики по всій Україні."
            ),
        }


def score_lead(lead, analysis: dict) -> dict:
    """Score a lead from 0-10 based on multiple criteria."""
    score = 0
    reasons = []

    # Критерій 1: Кількість товарів/SKU (вага 3) — макс 3 бали
    products = lead.products_count or 0
    if products >= 1000:
        score += 3
        reasons.append(f"Великий каталог: {products} SKU (+3)")
    elif products >= 300:
        score += 2
        reasons.append(f"Середній каталог: {products} SKU (+2)")
    elif products >= 50:
        score += 1
        reasons.append(f"Малий каталог: {products} SKU (+1)")
    else:
        reasons.append("Каталог невідомий або малий (+0)")

    # Критерій 2: Потенціал за аналізом AI (вага 3) — макс 3 бали
    potential = analysis.get("potential", "low")
    if potential == "high":
        score += 3
        reasons.append("AI оцінка: високий потенціал (+3)")
    elif potential == "medium":
        score += 2
        reasons.append("AI оцінка: середній потенціал (+2)")
    else:
        score += 1
        reasons.append("AI оцінка: низький потенціал (+1)")

    # Критерій 3: Місто не Київ — перевага по тарифах НП (вага 2) — макс 2 бали
    city = (lead.city or "").lower()
    kyiv_keywords = ["київ", "kyiv", "kiev"]
    if city and not any(k in city for k in kyiv_keywords):
        score += 2
        reasons.append(f"Місто {lead.city} — не Київ, перевага НП тарифів (+2)")
    elif not city:
        score += 1
        reasons.append("Місто невідоме (+1)")
    else:
        reasons.append("Київ — без переваги по НП тарифах (+0)")

    # Критерій 4: Продає на маркетплейсах (вага 2) — макс 2 бали
    description = (lead.description or "").lower()
    website = (lead.website or "").lower()
    marketplace_keywords = [
        "rozetka", "розетка", "prom.ua", "prom", "маркетплейс", "marketplace",
        "інтернет-магазин", "інтернет магазин", "онлайн",
    ]
    if any(k in description or k in website for k in marketplace_keywords):
        score += 2
        reasons.append("Продає онлайн / маркетплейс (+2)")
    elif lead.website:
        score += 1
        reasons.append("Має сайт (+1)")

    # Фінальна оцінка (max = 10)
    score = min(score, 10)

    if score >= 8:
        grade = "A"
        label = "Гарячий лід"
    elif score >= 6:
        grade = "B"
        label = "Перспективний"
    elif score >= 4:
        grade = "C"
        label = "Можливий"
    else:
        grade = "D"
        label = "Слабкий"

    return {
        "score": score,
        "grade": grade,
        "label": label,
        "reasons": reasons,
    }
