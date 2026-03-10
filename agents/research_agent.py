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
    contact_source: str = ""
    extra_phones: str = ""
    social_media: str = ""  # JSON string: {"instagram": "url", ...}


def _normalize_name(name: str) -> str:
    """Normalize company name for dedup: lowercase, strip punctuation/whitespace."""
    name = unicodedata.normalize("NFKC", name).lower().strip()
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


def clean_company_name(name: str, website: str = "") -> str:
    """Обрізає довгі назви компаній до читабельної форми."""
    if len(name) <= 80:
        result = name
    else:
        result = name
        for sep in [",", "(", "\u2014", " - ", " | "]:
            if sep in name:
                result = name.split(sep)[0].strip()
                break
        else:
            result = name[:80].strip()

    # Fallback to domain if name is too short or ends abruptly
    bad_endings = ("чи", "та", "або", "для", "хл", "дл", "ін", "пр", "ко", "за", "на", "по")
    if len(result) < 5 or result.endswith(bad_endings):
        if website:
            from urllib.parse import urlparse
            try:
                domain = urlparse(website).netloc.replace("www.", "")
                if domain:
                    result = domain
            except Exception:
                pass
    return result


class ResearchAgent:
    """Шукає потенційних клієнтів косметики з багатьох джерел."""

    PROM_SEARCH_URL = "https://prom.ua/ua/search?search_term={query}"
    PROM_COMPANY_URL = "https://prom.ua/c{company_id}"
    GOOGLE_MAPS_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    GOOGLE_PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
    GOOGLE_CUSTOM_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"
    OLX_SEARCH_URL = "https://www.olx.ua/d/uk/q-{query}/"
    INSTAGRAM_GRAPH_URL = "https://graph.facebook.com/v19.0"

    # All available search channels — Serper (Google API) first, then Prom.ua fallback
    ALL_CHANNELS = ["serper", "prom", "google", "google_maps", "google_search", "olx", "instagram", "facebook"]

    def __init__(self, api_keys: Optional[dict] = None, channels: Optional[List[str]] = None):
        self._api_keys = api_keys or {}
        self._channels = channels or self.ALL_CHANNELS

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

    def search(self, count: int = 5, niche: str = "косметика", channels: Optional[List[str]] = None) -> List[Lead]:
        """Шукає лідів з вибраних джерел, повертає до count результатів."""
        active_channels = channels or self._channels
        leads: List[Lead] = []
        seen_names: set = set()
        seen_domains: set = set()

        def _add_lead(lead: Lead) -> bool:
            norm = _normalize_name(lead.name)
            if norm in seen_names or len(norm) < 3:
                return False
            # Domain dedup within run
            if lead.website:
                domain = ResearchAgent._extract_domain(lead.website)
                if domain and domain in seen_domains:
                    logger.debug(f"[Research] Пропускаємо дублікат домену в рамках run: {lead.name} ({domain})")
                    return False
                if domain:
                    seen_domains.add(domain)
            # Fuzzy name dedup within run
            for existing_name in seen_names:
                if ResearchAgent._name_similarity(norm, existing_name) > 0.80:
                    logger.debug(f"[Research] Пропускаємо схоже ім'я в рамках run: {lead.name} ~= {existing_name}")
                    return False
            seen_names.add(norm)
            leads.append(lead)
            return True

        def _add_leads(new_leads: List[Lead]):
            for lead in new_leads:
                if len(leads) >= count:
                    break
                _add_lead(lead)

        # Channel dispatch — order matters for priority
        # Request 2x to account for dedup filtering
        remaining = lambda: max(0, count * 2 - len(leads))
        channel_methods = {
            "serper": lambda: self._search_serper(remaining(), niche=niche),
            "google": lambda: self._search_google(remaining(), niche=niche),
            "prom": lambda: self._search_prom(remaining(), niche=niche),
            "google_maps": lambda: self._search_google_maps(remaining(), niche=niche),
            "google_search": lambda: self._search_google_custom(remaining(), niche=niche),
            "olx": lambda: self._search_olx(remaining(), niche=niche),
            "instagram": lambda: self._search_instagram(remaining()),
            "facebook": lambda: self._search_facebook(remaining()),
        }

        for channel in active_channels:
            if len(leads) >= count:
                break
            method = channel_methods.get(channel)
            if method:
                try:
                    _add_leads(method())
                except Exception as e:
                    logger.warning(f"[ResearchAgent] Channel {channel} failed: {e}")

        # Deduplicate against existing leads in DB
        leads = self._filter_already_contacted(leads)

        # Gemini fallback — generate leads via AI if scrapers returned 0
        if len(leads) < count:
            logger.info(f"[ResearchAgent] Scrapers returned {len(leads)}/{count}, using Gemini fallback for '{niche}'")
            try:
                gemini_leads = self._generate_leads_gemini(count - len(leads), niche)
                gemini_leads = self._filter_already_contacted(gemini_leads)
                _add_leads(gemini_leads)
            except Exception as e:
                logger.warning(f"[ResearchAgent] Gemini fallback failed: {e}")

        # Static fallback only if still short
        if len(leads) < count:
            fallback_pool = self._filter_already_contacted(list(self.FALLBACK_LEADS))
            random.shuffle(fallback_pool)
            for lead in fallback_pool:
                if len(leads) >= count:
                    break
                norm = _normalize_name(lead.name)
                if norm not in seen_names and len(norm) >= 3:
                    seen_names.add(norm)
                    leads.append(lead)

        return leads[:count]

    def _generate_leads_gemini(self, count: int, niche: str) -> List[Lead]:
        """Generate realistic leads via Gemini AI based on niche."""
        import json as _json
        api_key = self._api_keys.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.info("[ResearchAgent] Gemini API key not configured, skipping.")
            return []

        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.0-flash")

            prompt = f"""Ти — експерт з B2B лідогенерації в Україні.
Згенеруй {count} УНІКАЛЬНИХ потенційних клієнтів (українські компанії) у ніші "{niche}",
яким може бути корисний фулфілмент-сервіс (зберігання, пакування, доставка товарів).

ВАЖЛИВО:
- Кожна компанія має бути РІЗНА — різні назви, міста, розміри
- Назви мають бути специфічні для ніші "{niche}", НЕ загальні
- Різні міста України (не тільки Київ)
- Різний масштаб бізнесу (від малих до великих)

Для кожного ліда вкажи:
- name: назва компанії (реалістична, специфічна для ніші "{niche}")
- website: правдоподібний URL (формат https://example.com.ua)
- email: правдоподібний email
- phone: телефон у форматі +380XXXXXXXXX
- city: місто в Україні (різні міста!)
- description: короткий опис бізнесу саме у ніші "{niche}" (1-2 речення)
- products_count: приблизна кількість товарних позицій (число)

Відповідь ТІЛЬКИ у форматі JSON масив, без markdown:
[{{"name":"...","website":"...","email":"...","phone":"...","city":"...","description":"...","products_count":...}}]"""

            response = model.generate_content(prompt)
            text = response.text.strip()
            # Strip markdown code blocks if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            data = _json.loads(text)
            leads = []
            for item in data:
                leads.append(Lead(
                    name=item.get("name", ""),
                    website=item.get("website", ""),
                    email=item.get("email", ""),
                    phone=item.get("phone", ""),
                    city=item.get("city", ""),
                    description=item.get("description", ""),
                    products_count=item.get("products_count", 0),
                    source="gemini",
                ))
            logger.info(f"[ResearchAgent] Gemini generated {len(leads)} leads for '{niche}'")
            return leads

        except Exception as e:
            logger.warning(f"[ResearchAgent] Gemini lead generation failed: {e}")
            return []

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract clean domain from URL for dedup (e.g. 'example.com.ua')."""
        from urllib.parse import urlparse
        try:
            domain = urlparse(url).netloc.lower().replace("www.", "")
            return domain if domain else ""
        except Exception:
            return ""

    @staticmethod
    def _name_similarity(a: str, b: str) -> float:
        """Simple character-level similarity ratio (0..1) between two normalized names."""
        if not a or not b:
            return 0.0
        a, b = _normalize_name(a), _normalize_name(b)
        if a == b:
            return 1.0
        # Use longest common subsequence ratio
        shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
        if len(longer) == 0:
            return 1.0
        matches = sum(1 for c in shorter if c in longer)
        # Simple overlap ratio
        overlap = 2 * matches / (len(a) + len(b))
        # Also check substring containment
        if shorter in longer:
            return max(overlap, 0.85)
        return overlap

    def _filter_already_contacted(self, leads: List[Lead]) -> List[Lead]:
        """Filter out leads that already exist in the DB (by website domain, phone, email, or fuzzy name)."""
        try:
            from backend.services.database import get_supabase
            db = get_supabase()
            existing = db.table("leads").select("name,website,phone,email").execute()
            existing_websites = {r["website"] for r in existing.data if r.get("website")}
            existing_domains = {self._extract_domain(r["website"]) for r in existing.data if r.get("website")}
            existing_domains.discard("")
            existing_phones = {r["phone"] for r in existing.data if r.get("phone")}
            existing_emails = {r["email"] for r in existing.data if r.get("email")}
            existing_names = [_normalize_name(r["name"]) for r in existing.data if r.get("name")]

            filtered = []
            for lead in leads:
                is_duplicate = False
                reason = ""

                # 1. Exact website match
                if lead.website and lead.website in existing_websites:
                    is_duplicate, reason = True, "website exact"
                # 2. Domain match
                elif lead.website:
                    domain = self._extract_domain(lead.website)
                    if domain and domain in existing_domains:
                        is_duplicate, reason = True, f"domain {domain}"
                # 3. Phone match
                if not is_duplicate and lead.phone and lead.phone in existing_phones:
                    is_duplicate, reason = True, "phone"
                # 4. Email match
                if not is_duplicate and lead.email and lead.email in existing_emails:
                    is_duplicate, reason = True, "email"
                # 5. Fuzzy name match (>80% similarity)
                if not is_duplicate and lead.name:
                    norm = _normalize_name(lead.name)
                    for ex_name in existing_names:
                        if self._name_similarity(norm, ex_name) > 0.80:
                            is_duplicate, reason = True, f"name ~'{ex_name}'"
                            break

                if is_duplicate:
                    logger.info(f"[Research] Пропускаємо дублікат ({reason}): {lead.name}")
                else:
                    filtered.append(lead)

            logger.info(f"[Research] Після дедуплікації: {len(filtered)}/{len(leads)} нових лідів")
            return filtered
        except Exception as e:
            logger.warning(f"[Research] Дедуплікація не вдалась: {e}")
            return leads

    # ── Serper.dev Google Search API ──────────────────────────────

    def _search_serper(self, count: int, niche: str = "косметика") -> List[Lead]:
        """Search via Serper.dev API (Google results, free tier 2500 req/month)."""
        from urllib.parse import urlparse

        api_key = self._api_keys.get("SERPER_API_KEY") or os.getenv("SERPER_API_KEY", "")
        if not api_key:
            logger.warning("[ResearchAgent] SERPER_API_KEY not set — add it to Railway env vars. Skipping Serper.")
            return []
        logger.info(f"[ResearchAgent] Using Serper API (key: {api_key[:8]}...)")

        leads = []
        seen_domains: set = set()
        queries = [
            f"{niche} інтернет магазин Україна",
            f"{niche} купити оптом Україна",
        ]

        for query in queries:
            if len(leads) >= count:
                break
            try:
                resp = requests.post(
                    "https://google.serper.dev/search",
                    json={"q": query, "gl": "ua", "hl": "uk", "num": 20},
                    headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()

                for item in data.get("organic", []):
                    if len(leads) >= count:
                        break

                    link = item.get("link", "")
                    title = item.get("title", "")
                    snippet = item.get("snippet", "")

                    if not link or not link.startswith("http"):
                        continue

                    try:
                        parsed = urlparse(link)
                        domain = parsed.netloc.replace("www.", "").lower()
                    except Exception:
                        continue

                    # Skip aggregators
                    if any(skip in domain for skip in self.SKIP_DOMAINS):
                        continue
                    if domain in seen_domains:
                        continue
                    seen_domains.add(domain)

                    website_url = f"{parsed.scheme}://{parsed.netloc}"
                    name = clean_company_name(
                        title.split(" - ")[0].split(" | ")[0].split(" — ")[0].strip(),
                        website=website_url,
                    )
                    if len(name) < 3:
                        name = domain.split(".")[0].replace("-", " ").replace("_", " ").title()
                    if len(name) < 3:
                        continue

                    lead = Lead(
                        name=name,
                        website=website_url,
                        description=snippet[:200] or f"Google: {query}",
                        source="google",
                    )

                    # Enrich contacts from website
                    self._scrape_contact_from_website(lead)
                    lead.contact_source = "website" if (lead.email or lead.phone) else "manual_needed"

                    leads.append(lead)

            except Exception as e:
                logger.warning(f"[ResearchAgent] Serper ({query}): {e}")
                continue

        logger.info(f"[ResearchAgent] Serper found {len(leads)} leads for '{niche}'")
        return leads

    # ── Google Organic Search ──────────────────────────────────────

    SKIP_DOMAINS = {
        "prom.ua", "rozetka.com.ua", "olx.ua", "facebook.com", "instagram.com",
        "youtube.com", "tiktok.com", "wikipedia.org", "google.com", "google.com.ua",
        "makeup.com.ua", "pinterest.com", "linkedin.com", "twitter.com",
    }

    def _search_google(self, count: int, niche: str = "косметика") -> List[Lead]:
        """Search Google via direct HTTP request — parse div.g blocks for leads."""
        from urllib.parse import urlparse, quote_plus

        leads = []
        seen_domains: set = set()
        queries = [
            f"{niche} інтернет магазин Україна",
            f"{niche} оптом Україна купити",
            f"{niche} виробник Україна сайт",
        ]

        for query in queries:
            if len(leads) >= count:
                break
            try:
                url = f"https://www.google.com/search?q={quote_plus(query)}&num=20&hl=uk"
                resp = requests.get(url, headers=self.HEADERS, timeout=10)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")

                # Parse structured result blocks (div.g or div[data-ved])
                blocks = soup.select("div.g, div[data-ved]")
                for block in blocks:
                    if len(leads) >= count:
                        break

                    # Extract company name from <h3>
                    h3 = block.select_one("h3")
                    if not h3:
                        continue

                    # Extract URL: try <cite>, then <a href>
                    site_url = ""
                    cite = block.select_one("cite, span.tjvcx")
                    if cite:
                        cite_text = cite.get_text(strip=True)
                        if cite_text.startswith("http"):
                            site_url = cite_text.split(" ")[0]
                        elif "." in cite_text:
                            site_url = "https://" + cite_text.split(" ")[0].split(" ›")[0]

                    if not site_url:
                        a_tag = block.select_one("a[href^='http']")
                        if not a_tag:
                            a_tag = block.select_one("a[href^='/url?q=']")
                        if a_tag:
                            href = a_tag.get("href", "")
                            if href.startswith("/url?q="):
                                href = href.split("/url?q=")[1].split("&")[0]
                            site_url = href

                    if not site_url or not site_url.startswith("http"):
                        continue

                    parsed = urlparse(site_url)
                    domain = parsed.netloc.replace("www.", "")

                    # Only .ua domains
                    if not domain.endswith(".ua"):
                        continue

                    # Skip aggregators
                    if any(skip in domain for skip in self.SKIP_DOMAINS):
                        continue

                    # Skip already seen domains
                    if domain in seen_domains:
                        continue
                    seen_domains.add(domain)

                    raw_name = h3.get_text(strip=True)
                    name = clean_company_name(
                        raw_name.split(" - ")[0].split(" | ")[0].split(" — ")[0].strip(),
                        website=site_url,
                    )
                    if len(name) < 3:
                        name = domain.split(".")[0].replace("-", " ").replace("_", " ").title()
                    if len(name) < 3:
                        continue

                    lead = Lead(
                        name=name,
                        website=site_url,
                        description=f"Google: {query}",
                        source="google",
                    )

                    # Enrich from website
                    self._scrape_contact_from_website(lead)
                    lead.contact_source = "website" if (lead.email or lead.phone) else "manual_needed"

                    leads.append(lead)

            except Exception as e:
                logger.warning(f"[ResearchAgent] Google search ({query}): {e}")
                continue

        return leads

    # ── Prom.ua ────────────────────────────────────────────────────

    def _search_prom(self, count: int, niche: str = "косметика") -> List[Lead]:
        """Парсинг продавців з Prom.ua по ніші з enrichment."""
        leads = []

        # Dynamic queries based on niche
        queries = [
            f"{niche} виробник",
            f"{niche} магазин",
            f"{niche} оптом",
            f"{niche} інтернет магазин",
            niche,
        ]

        for query in queries:
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
                    # Build full URL for prom.ua relative links
                    if href.startswith("/"):
                        href = f"https://prom.ua{href}"
                    prom_url = href if href.startswith("http") else ""

                    lead = Lead(
                        name=name,
                        website=prom_url,
                        description=f"Продавець на Prom.ua (запит: {query})",
                        source="prom.ua",
                    )

                    # Try to enrich from company page (get external website, phone, email)
                    if prom_url and "prom.ua" in prom_url:
                        self._enrich_lead_from_prom(lead)

                    # If still no external website — try Google search
                    if not lead.website or "prom.ua" in lead.website:
                        self._find_website_via_google(lead)

                    # Scrape contacts from external website if available
                    if lead.website and "prom.ua" not in lead.website:
                        self._scrape_contact_from_website(lead)
                        if lead.email or lead.phone:
                            lead.contact_source = "website"

                    # Mark if contacts still missing
                    if not lead.email and not lead.phone:
                        lead.contact_source = "manual_needed"

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

            # Company website (external) — try multiple selectors
            ext_site = soup.select_one("[data-qaid='company_site'] a, .company-site a, a[rel='nofollow'][href^='http']")
            if ext_site and ext_site.get("href"):
                ext_url = ext_site["href"]
                if ext_url.startswith("http") and "prom.ua" not in ext_url:
                    lead.website = ext_url
                    lead.contact_source = "prom_profile"

            # If no external website found, try links in page that look like company sites
            if not lead.website or "prom.ua" in lead.website:
                for a in soup.select("a[href^='http']"):
                    href = a.get("href", "")
                    if href and "prom.ua" not in href and "google." not in href and "facebook." not in href:
                        if ".ua" in href or ".com" in href:
                            lead.website = href
                            lead.contact_source = "prom_link"
                            break

        except Exception as e:
            logger.debug(f"[ResearchAgent] Prom enrichment failed for {lead.name}: {e}")

    def _search_google_maps(self, count: int, niche: str = "косметика") -> List[Lead]:
        """Пошук через Google Maps Places API з Place Details enrichment."""
        api_key = self._api_keys.get("GOOGLE_MAPS_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY")
        if not api_key:
            logger.info("[ResearchAgent] Google Maps API key не налаштований, пропускаю.")
            return []

        leads = []
        queries = [f"{niche} виробник Україна", f"{niche} оптом Україна", f"{niche} інтернет-магазин"]

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
                    name = clean_company_name(place.get("name", ""))
                    address = place.get("formatted_address", "")
                    city = address.split(",")[0].strip() if address else ""

                    lead = Lead(
                        name=name,
                        city=city,
                        description=f"Знайдено через Google Maps: {address}",
                        source="google_maps",
                    )

                    # Enrich via Place Details API
                    place_id = place.get("place_id")
                    if place_id:
                        self._enrich_from_place_details(lead, place_id, api_key)

                    # Scrape contacts from website if available
                    if lead.website:
                        self._scrape_contact_from_website(lead)

                    leads.append(lead)

                    if len(leads) >= count:
                        break

            except Exception as e:
                logger.warning(f"[ResearchAgent] Google Maps: {e}")
                continue

        return leads

    def _enrich_from_place_details(self, lead: Lead, place_id: str, api_key: str):
        """Fetch phone and website from Google Place Details API."""
        try:
            resp = requests.get(
                self.GOOGLE_PLACE_DETAILS_URL,
                params={
                    "place_id": place_id,
                    "fields": "formatted_phone_number,international_phone_number,website",
                    "key": api_key,
                },
                timeout=10,
            )
            resp.raise_for_status()
            result = resp.json().get("result", {})

            phone = result.get("international_phone_number") or result.get("formatted_phone_number", "")
            if phone and not lead.phone:
                lead.phone = phone

            website = result.get("website", "")
            if website and not lead.website:
                lead.website = website

        except Exception as e:
            logger.debug(f"[ResearchAgent] Place Details failed for {lead.name}: {e}")

    def _find_website_via_google(self, lead: Lead):
        """Try to find the lead's external website via Google search."""
        from urllib.parse import urlparse, quote_plus
        try:
            query = f"{lead.name} сайт Україна"
            url = f"https://www.google.com/search?q={quote_plus(query)}&num=5&hl=uk"
            resp = requests.get(url, headers=self.HEADERS, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            for a_tag in soup.select("a[href]"):
                href = a_tag.get("href", "")
                if href.startswith("/url?q="):
                    href = href.split("/url?q=")[1].split("&")[0]
                if not href.startswith("http"):
                    continue
                domain = urlparse(href).netloc.replace("www.", "")
                if domain.endswith(".ua") and not any(s in domain for s in self.SKIP_DOMAINS):
                    lead.website = href
                    lead.contact_source = "google_search"
                    logger.info(f"[ResearchAgent] Found website via Google for '{lead.name}': {href}")
                    return
        except Exception as e:
            logger.debug(f"[ResearchAgent] Google website search for '{lead.name}' failed: {e}")

    # Emails to ignore
    JUNK_EMAIL_DOMAINS = {"example.com", "wixpress.com", "sentry.io", "googleapis.com",
                          "w3.org", "schema.org", "prom.ua", "google.com", "facebook.com"}

    def _scrape_contact_from_website(self, lead: Lead):
        """Scrape email and phone from a company website + cooperation pages."""
        from urllib.parse import urlparse

        try:
            base_url = lead.website.rstrip("/")
            parsed_base = urlparse(base_url)
            base_origin = f"{parsed_base.scheme}://{parsed_base.netloc}"

            # Pages to check — main page + cooperation/contact pages
            pages_to_check = [base_url]
            cooperation_paths = [
                "/contacts", "/kontakty", "/контакти", "/contact",
                "/cooperation", "/partners", "/b2b", "/wholesale",
                "/співпраця", "/партнерам", "/оптом", "/about",
            ]
            for path in cooperation_paths:
                pages_to_check.append(base_origin + path)

            for page_url in pages_to_check:
                if lead.email and lead.phone:
                    break  # Already have both
                try:
                    resp = requests.get(page_url, headers=self.HEADERS, timeout=8,
                                        allow_redirects=True)
                    if resp.status_code != 200:
                        continue
                    html = resp.text
                    self._extract_contacts_from_html(lead, html)
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"[ResearchAgent] Website scrape failed for {lead.name}: {e}")

    def _extract_contacts_from_html(self, lead: Lead, html: str):
        """Extract all emails, phones, and social media from HTML."""
        import json as _json
        from urllib.parse import unquote

        soup = BeautifulSoup(html, "lxml")

        # ── Collect ALL emails from mailto: links ──
        all_emails = []
        for mailto in soup.select("[href^='mailto:']"):
            email = unquote(mailto["href"].replace("mailto:", "").split("?")[0].strip())
            if "@" in email and not any(d in email.lower() for d in self.JUNK_EMAIL_DOMAINS):
                if email not in all_emails:
                    all_emails.append(email)

        # Regex fallback for emails
        if len(all_emails) < 2:
            regex_emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.(?:ua|com|net|org|info)", html)
            for email in regex_emails:
                if not any(d in email.lower() for d in self.JUNK_EMAIL_DOMAINS) and email not in all_emails:
                    all_emails.append(email)

        all_emails = all_emails[:2]
        if not lead.email and all_emails:
            lead.email = all_emails[0]

        # ── Collect ALL phones from tel: links ──
        all_phones = []
        for tel in soup.select("[href^='tel:']"):
            raw = unquote(tel["href"].replace("tel:", "").strip())
            digits = re.sub(r"[^\d+]", "", raw)
            # Normalize to +380 format
            clean_digits = re.sub(r"[^\d]", "", digits)
            phone = None
            if clean_digits.startswith("380") and len(clean_digits) >= 12:
                phone = f"+{clean_digits[:12]}"
            elif clean_digits.startswith("0") and len(clean_digits) >= 10:
                phone = f"+38{clean_digits[:10]}"
            if phone and phone not in all_phones:
                all_phones.append(phone)

        # Regex fallback for phones
        if len(all_phones) < 3:
            phone_patterns = [
                r"\+?38\s*\(?0\d{2}\)?\s*\d{3}[\s\-]?\d{2}[\s\-]?\d{2}",
                r"\+?380[\s\-\(\)]*\d{2}[\s\-\(\)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}",
                r"(?<!\d)0\d{2}[\s\-\(\)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}(?!\d)",
            ]
            for pattern in phone_patterns:
                for raw in re.findall(pattern, html):
                    clean_digits = re.sub(r"[^\d]", "", raw)
                    phone = None
                    if clean_digits.startswith("380") and len(clean_digits) >= 12:
                        phone = f"+{clean_digits[:12]}"
                    elif clean_digits.startswith("80") and len(clean_digits) >= 11:
                        phone = f"+3{clean_digits[:11]}"
                    elif clean_digits.startswith("0") and len(clean_digits) >= 10:
                        phone = f"+38{clean_digits[:10]}"
                    if phone and phone not in all_phones:
                        all_phones.append(phone)

        all_phones = all_phones[:3]
        if not lead.phone and all_phones:
            lead.phone = all_phones[0]
        # Store extra phones (beyond the first one)
        extra = [p for p in all_phones if p != lead.phone]
        if extra:
            lead.extra_phones = ", ".join(extra)

        # ── Collect social media links ──
        social = {}
        if not lead.social_media or lead.social_media == "{}":
            social_platforms = {
                "instagram": r'https?://(?:www\.)?instagram\.com/[^\s"\'<>]+',
                "facebook": r'https?://(?:www\.)?facebook\.com/[^\s"\'<>]+',
                "tiktok": r'https?://(?:www\.)?tiktok\.com/[^\s"\'<>]+',
                "telegram": r'https?://t\.me/[^\s"\'<>]+',
                "youtube": r'https?://(?:www\.)?youtube\.com/[^\s"\'<>]+',
                "linkedin": r'https?://(?:www\.)?linkedin\.com/[^\s"\'<>]+',
            }
            for platform, pattern in social_platforms.items():
                matches = re.findall(pattern, html, re.I)
                if matches:
                    social[platform] = matches[0].rstrip("/")

            if social:
                lead.social_media = _json.dumps(social, ensure_ascii=False)

        # ── Extract city from address/location elements ──
        if not lead.city:
            for sel in ["[class*='address']", "[class*='location']", "[class*='city']", "[itemprop='address']"]:
                el = soup.select_one(sel)
                if el:
                    text = el.get_text(strip=True)[:100]
                    cities = re.findall(r"(?:Київ|Харків|Одеса|Дніпро|Львів|Запоріжжя|Вінниця|Полтава|Чернігів|Суми|Рівне|Тернопіль|Житомир|Хмельницький|Черкаси|Кропивницький|Миколаїв|Херсон|Чернівці|Івано-Франківськ|Ужгород|Луцьк|Бориспіль)", text)
                    if cities:
                        lead.city = cities[0]
                        break

    # ── Google Custom Search ─────────────────────────────────────────

    GOOGLE_SEARCH_QUERIES = [
        "косметика інтернет-магазин Україна",
        "натуральна косметика купити",
        "косметика оптом Україна",
        "виробник косметики Україна",
        '"Працює на Horoshop" косметика',
    ]

    def _search_google_custom(self, count: int, niche: str = "косметика") -> List[Lead]:
        """Пошук через Google Custom Search JSON API."""
        api_key = self._api_keys.get("GOOGLE_CUSTOM_SEARCH_API_KEY") or os.getenv("GOOGLE_CUSTOM_SEARCH_API_KEY")
        cx = self._api_keys.get("GOOGLE_CUSTOM_SEARCH_CX") or os.getenv("GOOGLE_CUSTOM_SEARCH_CX")
        if not api_key or not cx:
            logger.info("[ResearchAgent] Google Custom Search не налаштований, пропускаю.")
            return []

        leads = []
        niche_queries = [
            f"{niche} інтернет-магазин Україна",
            f"{niche} купити оптом",
            f"{niche} виробник Україна",
        ]
        for query in niche_queries:
            if len(leads) >= count:
                break
            try:
                resp = requests.get(
                    self.GOOGLE_CUSTOM_SEARCH_URL,
                    params={"key": api_key, "cx": cx, "q": query, "num": min(10, count), "lr": "lang_uk"},
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()

                for item in data.get("items", []):
                    link = item.get("link", "")
                    title = item.get("title", "")
                    snippet = item.get("snippet", "")

                    # Skip aggregators and marketplaces
                    if any(skip in link for skip in ["prom.ua", "rozetka.com", "makeup.com.ua", "olx.ua", "facebook.com", "instagram.com"]):
                        continue

                    # Extract domain as company name fallback
                    from urllib.parse import urlparse
                    domain = urlparse(link).netloc.replace("www.", "")
                    name = clean_company_name(title.split(" - ")[0].split(" | ")[0].split(" — ")[0].strip(), website=link)
                    if not name or len(name) < 3:
                        name = domain

                    lead = Lead(
                        name=name,
                        website=link,
                        description=f"Google Search: {snippet[:150]}",
                        source="google_search",
                    )
                    self._scrape_contact_from_website(lead)
                    leads.append(lead)

                    if len(leads) >= count:
                        break

            except Exception as e:
                logger.warning(f"[ResearchAgent] Google Custom Search ({query}): {e}")
                continue

        return leads

    # ── OLX ───────────────────────────────────────────────────────────

    OLX_QUERIES = [
        "косметика оптом",
        "косметика виробник",
        "натуральна косметика",
    ]

    def _search_olx(self, count: int, niche: str = "косметика") -> List[Lead]:
        """Парсинг бізнес-профілів з OLX.ua по ніші."""
        leads = []
        seen_sellers: set = set()

        queries = [f"{niche} оптом", f"{niche} виробник", niche]
        for query in queries:
            if len(leads) >= count:
                break
            try:
                url = self.OLX_SEARCH_URL.format(query=query.replace(" ", "-"))
                resp = requests.get(url, headers=self.HEADERS, timeout=10)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")

                # OLX listing cards
                cards = soup.select("[data-cy='l-card']")
                for card in cards:
                    if len(leads) >= count:
                        break

                    # Seller name
                    seller_el = card.select_one("[data-testid='seller-name'], .css-1lcz6o7")
                    if not seller_el:
                        continue
                    seller_name = seller_el.get_text(strip=True)
                    if not seller_name or seller_name in seen_sellers:
                        continue
                    seen_sellers.add(seller_name)

                    # Listing title for description
                    title_el = card.select_one("h6, [data-cy='ad-card-title']")
                    title = title_el.get_text(strip=True) if title_el else ""

                    # Location
                    loc_el = card.select_one("[data-testid='location-date'], .css-veheph")
                    city = ""
                    if loc_el:
                        loc_text = loc_el.get_text(strip=True)
                        city = loc_text.split("-")[0].split(",")[0].strip()

                    # Link to listing (to scrape seller page)
                    link_el = card.select_one("a[href]")
                    listing_url = ""
                    if link_el:
                        href = link_el.get("href", "")
                        listing_url = href if href.startswith("http") else f"https://www.olx.ua{href}"

                    lead = Lead(
                        name=seller_name,
                        city=city,
                        description=f"OLX: {title[:150]}",
                        source="olx",
                    )

                    # Try to get phone from listing page
                    if listing_url:
                        self._enrich_from_olx_listing(lead, listing_url)

                    leads.append(lead)

            except Exception as e:
                logger.warning(f"[ResearchAgent] OLX ({query}): {e}")
                continue

        return leads

    def _enrich_from_olx_listing(self, lead: Lead, listing_url: str):
        """Extract contacts from OLX listing page."""
        try:
            resp = requests.get(listing_url, headers=self.HEADERS, timeout=10)
            resp.raise_for_status()
            html = resp.text

            # Phone patterns in page text
            if not lead.phone:
                phones = re.findall(r"\+380\d{9}", html)
                if not phones:
                    phones = re.findall(r"(?<!\d)0\d{9}(?!\d)", html)
                if phones:
                    lead.phone = phones[0] if phones[0].startswith("+") else f"+38{phones[0]}"

            # Sometimes seller has a website link
            soup = BeautifulSoup(html, "lxml")
            for a in soup.select("a[href]"):
                href = a.get("href", "")
                if href.startswith("http") and not any(x in href for x in ["olx.ua", "facebook.com", "google.", "apple."]):
                    if "." in href and len(href) > 10:
                        lead.website = href
                        self._scrape_contact_from_website(lead)
                        break

        except Exception as e:
            logger.debug(f"[ResearchAgent] OLX enrichment failed for {lead.name}: {e}")

    # ── Instagram ─────────────────────────────────────────────────────

    INSTAGRAM_HASHTAGS = [
        "косметикаукраїна",
        "натуральнакосметика",
        "українськакосметика",
        "косметикаоптом",
    ]

    def _search_instagram(self, count: int) -> List[Lead]:
        """Пошук бізнес-акаунтів через Instagram Graph API."""
        access_token = self._api_keys.get("INSTAGRAM_ACCESS_TOKEN") or os.getenv("INSTAGRAM_ACCESS_TOKEN")
        if not access_token:
            logger.info("[ResearchAgent] Instagram access token не налаштований, пропускаю.")
            return []

        leads = []
        seen_users: set = set()

        for hashtag_name in self.INSTAGRAM_HASHTAGS:
            if len(leads) >= count:
                break
            try:
                # Step 1: Get hashtag ID
                resp = requests.get(
                    f"{self.INSTAGRAM_GRAPH_URL}/ig_hashtag_search",
                    params={"q": hashtag_name, "access_token": access_token},
                    timeout=10,
                )
                resp.raise_for_status()
                hashtag_data = resp.json().get("data", [])
                if not hashtag_data:
                    continue
                hashtag_id = hashtag_data[0]["id"]

                # Step 2: Get recent media for hashtag
                resp = requests.get(
                    f"{self.INSTAGRAM_GRAPH_URL}/{hashtag_id}/recent_media",
                    params={
                        "fields": "caption,permalink",
                        "access_token": access_token,
                        "limit": 50,
                    },
                    timeout=10,
                )
                resp.raise_for_status()

                for media in resp.json().get("data", []):
                    if len(leads) >= count:
                        break

                    caption = media.get("caption", "") or ""
                    permalink = media.get("permalink", "")

                    # Extract username from permalink
                    # Format: https://www.instagram.com/p/XXX/ or /username/
                    username = ""
                    if "/p/" in permalink:
                        parts = permalink.rstrip("/").split("/")
                        # Try to get from media owner via API
                        pass
                    else:
                        parts = permalink.rstrip("/").split("/")
                        if len(parts) >= 4:
                            username = parts[3]

                    if not username or username in seen_users:
                        continue
                    seen_users.add(username)

                    # Extract contacts from bio/caption
                    email = ""
                    phone = ""
                    website = ""

                    emails = re.findall(r"[\w.-]+@[\w.-]+\.\w+", caption)
                    if emails:
                        email = emails[0]

                    phones = re.findall(r"\+380\d{9}", caption)
                    if phones:
                        phone = phones[0]

                    # Look for URLs in caption
                    urls = re.findall(r"https?://[\w./\-?=&]+", caption)
                    for url in urls:
                        if "instagram.com" not in url and "facebook.com" not in url:
                            website = url
                            break

                    lead = Lead(
                        name=username,
                        email=email,
                        phone=phone,
                        website=website,
                        description=f"Instagram: {caption[:150]}",
                        source="instagram",
                    )

                    if lead.website:
                        self._scrape_contact_from_website(lead)

                    leads.append(lead)

            except Exception as e:
                logger.warning(f"[ResearchAgent] Instagram ({hashtag_name}): {e}")
                continue

        return leads

    # ── Facebook Pages ────────────────────────────────────────────────

    def _search_facebook(self, count: int) -> List[Lead]:
        """Пошук бізнес-сторінок через Facebook Graph API."""
        access_token = self._api_keys.get("FACEBOOK_ACCESS_TOKEN") or os.getenv("FACEBOOK_ACCESS_TOKEN")
        if not access_token:
            logger.info("[ResearchAgent] Facebook access token не налаштований, пропускаю.")
            return []

        leads = []
        queries = ["косметика Україна", "натуральна косметика", "cosmetics Ukraine"]

        for query in queries:
            if len(leads) >= count:
                break
            try:
                resp = requests.get(
                    f"{self.INSTAGRAM_GRAPH_URL}/pages/search",
                    params={
                        "q": query,
                        "fields": "name,website,phone,emails,location,about",
                        "access_token": access_token,
                        "limit": 25,
                    },
                    timeout=10,
                )
                resp.raise_for_status()

                for page in resp.json().get("data", []):
                    if len(leads) >= count:
                        break

                    name = page.get("name", "")
                    if not name:
                        continue

                    location = page.get("location", {})
                    city = location.get("city", "") if location else ""

                    emails_list = page.get("emails", [])
                    email = emails_list[0] if emails_list else ""

                    lead = Lead(
                        name=name,
                        website=page.get("website", ""),
                        email=email,
                        phone=page.get("phone", ""),
                        city=city,
                        description=f"Facebook: {page.get('about', '')[:150]}",
                        source="facebook",
                    )

                    if lead.website:
                        self._scrape_contact_from_website(lead)

                    leads.append(lead)

            except Exception as e:
                logger.warning(f"[ResearchAgent] Facebook ({query}): {e}")
                continue

        return leads
