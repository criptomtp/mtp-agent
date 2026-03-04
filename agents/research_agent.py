"""ResearchAgent — пошук потенційних клієнтів косметики."""

import os
import re
import random
import logging
import unicodedata
from dataclasses import dataclass, field, asdict
from typing import List, Optional

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class Lead:
    name: str
    website: str = ""
    email: str = ""
    phone: str = ""
    city: str = ""
    description: str = ""
    products_count: int = 0
    source: str = ""


def _normalize_name(name: str) -> str:
    """Normalize company name for dedup: lowercase, strip punctuation/whitespace."""
    name = unicodedata.normalize("NFKC", name).lower().strip()
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


class ResearchAgent:
    """Шукає потенційних клієнтів косметики на Prom.ua та Google Maps."""

    PROM_SEARCH_URL = "https://prom.ua/search?search_term={query}"
    PROM_COMPANY_URL = "https://prom.ua/c{company_id}"
    GOOGLE_MAPS_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    # Targeted queries for cosmetics companies that need fulfillment
    PROM_QUERIES = [
        "косметика виробник",
        "натуральна косметика магазин",
        "косметика оптом",
        "косметика інтернет магазин",
        "натуральна косметика виробник",
        "корейська косметика магазин",
        "професійна косметика дистриб'ютор",
    ]

    FALLBACK_LEADS = [
        Lead(
            name="КосметикПро",
            website="https://kosmetikpro.ua",
            email="info@kosmetikpro.ua",
            phone="+380671234567",
            city="Київ",
            description="Інтернет-магазин професійної косметики. Широкий асортимент засобів для догляду за шкірою та волоссям.",
            products_count=1200,
            source="fallback",
        ),
        Lead(
            name="BeautyBox Ukraine",
            website="https://beautybox.com.ua",
            email="sales@beautybox.com.ua",
            phone="+380509876543",
            city="Харків",
            description="Дистриб'ютор косметичних брендів. Постачання салонам краси та магазинам по всій Україні.",
            products_count=3500,
            source="fallback",
        ),
        Lead(
            name="ГлоуСкін",
            website="https://glowskin.ua",
            email="hello@glowskin.ua",
            phone="+380631112233",
            city="Одеса",
            description="Виробник натуральної косметики. Власна лінія кремів, сироваток та масок.",
            products_count=85,
            source="fallback",
        ),
        Lead(
            name="Makeup Point",
            website="https://makeuppoint.com.ua",
            email="order@makeuppoint.com.ua",
            phone="+380977654321",
            city="Дніпро",
            description="Мережа магазинів декоративної косметики з онлайн-доставкою по Україні.",
            products_count=2800,
            source="fallback",
        ),
        Lead(
            name="НатурКосметик",
            website="https://naturcosmetic.ua",
            email="info@naturcosmetic.ua",
            phone="+380661239876",
            city="Львів",
            description="Еко-косметика українського виробництва. Органічні інгредієнти, без тестування на тваринах.",
            products_count=150,
            source="fallback",
        ),
        Lead(
            name="SkinLab Ukraine",
            website="https://skinlab.ua",
            email="partners@skinlab.ua",
            phone="+380501234000",
            city="Київ",
            description="Лабораторія з розробки та виробництва косметичних засобів. B2B та B2C продажі.",
            products_count=420,
            source="fallback",
        ),
        Lead(
            name="Аромат Плюс",
            website="https://aromatplus.com.ua",
            email="zakaz@aromatplus.com.ua",
            phone="+380931234567",
            city="Запоріжжя",
            description="Оптовий постачальник парфумерії та косметики. Працюють з 200+ брендами.",
            products_count=5000,
            source="fallback",
        ),
        Lead(
            name="CosmoTrade",
            website="https://cosmotrade.ua",
            email="info@cosmotrade.ua",
            phone="+380681112244",
            city="Вінниця",
            description="Торгова платформа косметичних товарів. Дропшипінг та оптові поставки.",
            products_count=1800,
            source="fallback",
        ),
        Lead(
            name="УкрБ'юті",
            website="https://ukrbeauty.com.ua",
            email="office@ukrbeauty.com.ua",
            phone="+380731239999",
            city="Полтава",
            description="Українська косметична компанія. Виробництво та продаж засобів по догляду за тілом.",
            products_count=320,
            source="fallback",
        ),
        Lead(
            name="ProBeauty Shop",
            website="https://probeautyshop.ua",
            email="support@probeautyshop.ua",
            phone="+380991234555",
            city="Чернівці",
            description="Онлайн-магазин професійної косметики для салонів краси та приватних майстрів.",
            products_count=950,
            source="fallback",
        ),
    ]

    def search(self, count: int = 5) -> List[Lead]:
        """Шукає лідів з усіх джерел, повертає до count результатів."""
        leads: List[Lead] = []
        seen_names: set = set()

        def _add_lead(lead: Lead) -> bool:
            norm = _normalize_name(lead.name)
            if norm in seen_names or len(norm) < 3:
                return False
            seen_names.add(norm)
            leads.append(lead)
            return True

        # Prom.ua — targeted queries
        prom_leads = self._search_prom(count * 2)  # fetch extra for dedup
        for lead in prom_leads:
            if len(leads) >= count:
                break
            _add_lead(lead)

        # Google Maps
        if len(leads) < count:
            maps_leads = self._search_google_maps(count - len(leads))
            for lead in maps_leads:
                if len(leads) >= count:
                    break
                _add_lead(lead)

        # Fallback
        if len(leads) < count:
            fallback_pool = list(self.FALLBACK_LEADS)
            random.shuffle(fallback_pool)
            for lead in fallback_pool:
                if len(leads) >= count:
                    break
                _add_lead(lead)

        return leads[:count]

    def _search_prom(self, count: int) -> List[Lead]:
        """Парсинг продавців косметики з Prom.ua з enrichment."""
        leads = []

        for query in self.PROM_QUERIES:
            if len(leads) >= count:
                break
            try:
                url = self.PROM_SEARCH_URL.format(query=query)
                resp = requests.get(url, headers=self.HEADERS, timeout=10)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")

                company_cards = soup.select("[data-qaid='company_name'], .company-info, .seller-info a")
                for card in company_cards[:count]:
                    name = card.get_text(strip=True)
                    if not name or len(name) < 3:
                        continue

                    href = card.get("href", "")
                    website = href if href.startswith("http") else ""

                    lead = Lead(
                        name=name,
                        website=website,
                        description=f"Продавець косметики на Prom.ua (запит: {query})",
                        source="prom.ua",
                    )

                    # Try to enrich from company page
                    if website and "prom.ua" in website:
                        self._enrich_lead_from_prom(lead)

                    leads.append(lead)

                    if len(leads) >= count:
                        break

            except Exception as e:
                logger.warning(f"[ResearchAgent] Prom.ua ({query}): {e}")
                continue

        return leads

    def _enrich_lead_from_prom(self, lead: Lead):
        """Visit Prom.ua company page to extract phone, email, city, products_count."""
        try:
            resp = requests.get(lead.website, headers=self.HEADERS, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            # Phone
            phone_el = soup.select_one("[data-qaid='phone_number'], .js-company-phone, [href^='tel:']")
            if phone_el:
                phone_text = phone_el.get("href", "") or phone_el.get_text(strip=True)
                phone_text = phone_text.replace("tel:", "").strip()
                if phone_text and len(phone_text) >= 10:
                    lead.phone = phone_text

            # Email
            email_el = soup.select_one("[href^='mailto:']")
            if email_el:
                email_text = email_el.get("href", "").replace("mailto:", "").strip()
                if "@" in email_text:
                    lead.email = email_text

            # City
            city_el = soup.select_one("[data-qaid='company_city'], .company-address, .seller-address")
            if city_el:
                city_text = city_el.get_text(strip=True)
                if city_text:
                    lead.city = city_text.split(",")[0].strip()

            # Products count
            count_el = soup.select_one("[data-qaid='products_count'], .company-products-count")
            if count_el:
                count_text = count_el.get_text(strip=True)
                nums = re.findall(r"\d+", count_text.replace(" ", ""))
                if nums:
                    lead.products_count = int(nums[0])

            # Company website (external)
            ext_site = soup.select_one("[data-qaid='company_site'] a, .company-site a")
            if ext_site and ext_site.get("href"):
                ext_url = ext_site["href"]
                if ext_url.startswith("http") and "prom.ua" not in ext_url:
                    lead.website = ext_url

        except Exception as e:
            logger.debug(f"[ResearchAgent] Prom enrichment failed for {lead.name}: {e}")

    def _search_google_maps(self, count: int) -> List[Lead]:
        """Пошук через Google Maps Places API."""
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not api_key:
            logger.info("[ResearchAgent] Google Maps API key не налаштований, пропускаю.")
            return []

        leads = []
        queries = ["косметика виробник Україна", "cosmetics wholesale Ukraine"]

        for query in queries:
            if len(leads) >= count:
                break
            try:
                resp = requests.get(
                    self.GOOGLE_MAPS_URL,
                    params={"query": query, "key": api_key, "language": "uk"},
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()

                for place in data.get("results", [])[:count]:
                    name = place.get("name", "")
                    address = place.get("formatted_address", "")
                    city = address.split(",")[0].strip() if address else ""

                    leads.append(Lead(
                        name=name,
                        city=city,
                        description=f"Знайдено через Google Maps: {address}",
                        source="google_maps",
                    ))

                    if len(leads) >= count:
                        break

            except Exception as e:
                logger.warning(f"[ResearchAgent] Google Maps: {e}")
                continue

        return leads
