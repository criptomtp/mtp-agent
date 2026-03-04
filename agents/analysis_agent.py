"""AnalysisAgent — аналіз ліда через Gemini/Claude API."""

import os
import json
from typing import Dict, Any

from dotenv import load_dotenv

from .research_agent import Lead

load_dotenv()

MTP_TARIFFS = {
    "прийом_товару": "2 грн/одиниця",
    "зберігання_паллет": "800 грн/місяць",
    "зберігання_коробка": "80 грн/місяць",
    "комплектація_b2c": "22 грн/замовлення (1-3 од.)",
    "комплектація_b2b": "45 грн/замовлення",
    "пакування": "8 грн/замовлення",
    "відправка_нп": "за тарифом Нової Пошти",
}


def _build_prompt(lead: Lead) -> str:
    return f"""Ти — бізнес-аналітик компанії MTP Fulfillment (3PL фулфілмент, Бориспіль, Україна).

Проаналізуй потенційного клієнта та поверни JSON (без markdown, тільки чистий JSON):

Клієнт:
- Назва: {lead.name}
- Сайт: {lead.website}
- Місто: {lead.city}
- Опис: {lead.description}
- Кількість товарів: {lead.products_count}

Тарифи MTP:
{json.dumps(MTP_TARIFFS, ensure_ascii=False, indent=2)}

Поверни JSON з полями:
{{
  "company_analysis": "короткий аналіз компанії та її потреб у фулфілменті (2-3 речення)",
  "mtp_value_proposition": "чому MTP Fulfillment ідеально підходить цьому клієнту (2-3 речення)",
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

    def analyze(self, lead: Lead) -> Dict[str, Any]:
        """Аналіз ліда: Gemini → Claude → fallback."""
        result = self._try_gemini(lead)
        if result:
            return result

        result = self._try_claude(lead)
        if result:
            return result

        return self._fallback_analysis(lead)

    def _try_gemini(self, lead: Lead) -> Dict[str, Any] | None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("  [AnalysisAgent] GEMINI_API_KEY не налаштований.")
            return None

        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(_build_prompt(lead))
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(text)
        except Exception as e:
            print(f"  [AnalysisAgent] Gemini помилка: {e}")
            return None

    def _try_claude(self, lead: Lead) -> Dict[str, Any] | None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("  [AnalysisAgent] ANTHROPIC_API_KEY не налаштований.")
            return None

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[{"role": "user", "content": _build_prompt(lead)}],
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
        storage_boxes = max(10, products // 50)
        orders_month = max(100, products // 5)

        storage_cost = storage_boxes * 80
        picking_cost = orders_month * 22
        packing_cost = orders_month * 8
        total = storage_cost + picking_cost + packing_cost

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
            "pricing_estimate": {
                "зберігання_місяць": f"{storage_cost} грн ({storage_boxes} коробок × 80 грн)",
                "комплектація_місяць": f"{picking_cost} грн ({orders_month} замовлень × 22 грн)",
                "пакування_місяць": f"{packing_cost} грн ({orders_month} замовлень × 8 грн)",
                "загалом_місяць": f"~{total} грн/місяць",
            },
            "personalization": (
                f"Вітаємо, {lead.name}! Ми бачимо великий потенціал у співпраці — "
                f"наш склад у Борисполі ідеально підходить для швидкої доставки косметики по всій Україні."
            ),
        }
