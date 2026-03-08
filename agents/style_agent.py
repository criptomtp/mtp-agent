"""StyleAgent — витягує brand style з сайту клієнта."""

import re
import logging
from collections import Counter
from typing import Dict

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DEFAULT_STYLE = {
    "primary_color": "#1A365D",
    "secondary_color": "#E53E3E",
    "font_family": "Inter",
    "website": "",
    "brand_name": "",
}

# Colors to ignore (too generic)
IGNORE_COLORS = {
    "#fff", "#ffffff", "#000", "#000000",
    "#fff0", "#0000", "#ffff", "#0000ff",
    "#333", "#333333", "#666", "#666666",
    "#999", "#999999", "#ccc", "#cccccc",
    "#eee", "#eeeeee", "#ddd", "#dddddd",
    "#f5f5f5", "#fafafa", "#f0f0f0",
}

HEX_RE = re.compile(r"#([0-9a-fA-F]{3,8})\b")
FONT_FAMILY_RE = re.compile(r"font-family\s*:\s*['\"]?([^;'\"}{,]+)", re.I)
GOOGLE_FONTS_RE = re.compile(r"fonts\.googleapis\.com/css2?\?family=([^&\"']+)", re.I)


class StyleAgent:
    """Витягує brand style (кольори, шрифти) з сайту клієнта."""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    def extract(self, url: str) -> Dict[str, str]:
        """Scrape website and return brand style dict."""
        if not url or not url.startswith("http"):
            return {**DEFAULT_STYLE}

        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=10, allow_redirects=True)
            resp.raise_for_status()
            html = resp.text
            soup = BeautifulSoup(html, "lxml")

            colors = self._extract_colors(soup, html)
            font = self._extract_font(soup, html)
            title = soup.title.get_text(strip=True) if soup.title else ""

            # Pick top 2 non-generic colors
            primary = colors[0] if len(colors) >= 1 else DEFAULT_STYLE["primary_color"]
            secondary = colors[1] if len(colors) >= 2 else DEFAULT_STYLE["secondary_color"]

            result = {
                "primary_color": primary,
                "secondary_color": secondary,
                "font_family": font,
                "website": url,
                "brand_name": title[:100],
            }
            logger.info(f"[StyleAgent] Extracted: {primary}, {secondary}, font={font} from {url}")
            return result

        except Exception as e:
            logger.warning(f"[StyleAgent] Failed to extract style from {url}: {e}")
            return {**DEFAULT_STYLE, "website": url}

    def _extract_colors(self, soup: BeautifulSoup, html: str) -> list:
        """Extract most frequent non-generic colors from CSS."""
        color_counts: Counter = Counter()

        # From inline styles
        for el in soup.select("[style]"):
            style = el.get("style", "")
            for match in HEX_RE.findall(style):
                self._count_hex(match, color_counts)

        # From <style> tags
        for style_tag in soup.select("style"):
            text = style_tag.get_text()
            for match in HEX_RE.findall(text):
                self._count_hex(match, color_counts)

        # From linked stylesheets (just the HTML source, not fetching external CSS)
        for match in HEX_RE.findall(html):
            self._count_hex(match, color_counts)

        # Sort by frequency, return top colors
        sorted_colors = [c for c, _ in color_counts.most_common(10)]
        return sorted_colors

    def _count_hex(self, hex_digits: str, counter: Counter):
        """Normalize and count a hex color, ignoring generic ones."""
        # Normalize to 6-digit lowercase
        h = hex_digits.lower()
        if len(h) == 3:
            h = h[0] * 2 + h[1] * 2 + h[2] * 2
        elif len(h) != 6:
            return  # skip 4/8 digit (rgba) hex

        color = f"#{h}"
        if color not in IGNORE_COLORS:
            counter[color] += 1

    def _extract_font(self, soup: BeautifulSoup, html: str) -> str:
        """Extract primary font family."""
        # Check Google Fonts links first (most reliable)
        for link in soup.select("link[href]"):
            href = link.get("href", "")
            match = GOOGLE_FONTS_RE.search(href)
            if match:
                font = match.group(1).replace("+", " ").split(":")[0].split("|")[0]
                return font.strip()

        # From <style> tags
        for style_tag in soup.select("style"):
            text = style_tag.get_text()
            match = FONT_FAMILY_RE.search(text)
            if match:
                font = match.group(1).strip().strip("'\"")
                if font.lower() not in ("inherit", "initial", "sans-serif", "serif", "monospace", "system-ui"):
                    return font.split(",")[0].strip().strip("'\"")

        # From inline styles
        for el in soup.select("[style*='font-family']"):
            style = el.get("style", "")
            match = FONT_FAMILY_RE.search(style)
            if match:
                font = match.group(1).strip().strip("'\"")
                if font.lower() not in ("inherit", "initial", "sans-serif", "serif", "monospace", "system-ui"):
                    return font.split(",")[0].strip().strip("'\"")

        return "Inter"
