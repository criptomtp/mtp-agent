"""OutreachAgent — відправка або збереження контактної інформації."""

import os
import re
from typing import Optional

import requests
from dotenv import load_dotenv

from .research_agent import Lead

load_dotenv()


class OutreachAgent:
    """Відправляє email або зберігає контактну картку для ручної відправки."""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    def process(self, lead: Lead, output_dir: str, send_email: bool = False) -> str:
        """Обробка outreach для ліда. Повертає статус."""
        email = lead.email or self._find_email_on_website(lead.website)

        if email and send_email:
            sent = self._send_gmail(email, lead, output_dir)
            if sent:
                return f"email_sent:{email}"

        if email:
            self._save_contact_card(lead, email, output_dir, note="Email знайдено, готово до відправки.")
            return f"ready:{email}"

        self._save_contact_card(lead, "", output_dir, note="Email не знайдено. Потрібен ручний пошук контакту.")
        return "manual_required"

    def _find_email_on_website(self, website: str) -> Optional[str]:
        """Шукає email на сайті компанії."""
        if not website:
            return None

        try:
            resp = requests.get(website, headers=self.HEADERS, timeout=10)
            resp.raise_for_status()
            emails = re.findall(
                r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                resp.text,
            )
            exclude = {"example.com", "email.com", "domain.com", "test.com"}
            for email in emails:
                domain = email.split("@")[1].lower()
                if domain not in exclude:
                    return email
        except Exception as e:
            print(f"  [OutreachAgent] Пошук email на {website}: {e}")

        return None

    def _send_gmail(self, to_email: str, lead: Lead, output_dir: str) -> bool:
        """Відправка через Gmail API (потребує OAuth)."""
        client_id = os.getenv("GMAIL_CLIENT_ID")
        sender = os.getenv("SENDER_EMAIL")

        if not client_id or not sender:
            print(f"  [OutreachAgent] Gmail API не налаштований. Зберігаю для ручної відправки.")
            return False

        email_file = os.path.join(output_dir, "email.txt")
        if not os.path.exists(email_file):
            print(f"  [OutreachAgent] email.txt не знайдено в {output_dir}")
            return False

        try:
            # Gmail API потребує повної OAuth2 авторизації.
            # Для production: використати google-auth + gmail API.
            # Поки зберігаємо як ready to send.
            print(f"  [OutreachAgent] Gmail OAuth потребує інтерактивної авторизації.")
            print(f"  [OutreachAgent] Email підготовлено для: {to_email}")
            return False
        except Exception as e:
            print(f"  [OutreachAgent] Gmail помилка: {e}")
            return False

    def _save_contact_card(self, lead: Lead, email: str, output_dir: str, note: str = "") -> None:
        """Зберігає контактну картку для ручного outreach."""
        card_path = os.path.join(output_dir, "contact_card.txt")

        lines = [
            "=" * 50,
            "КОНТАКТНА КАРТКА",
            "=" * 50,
            f"Компанія:  {lead.name}",
            f"Сайт:     {lead.website or 'не знайдено'}",
            f"Email:    {email or 'не знайдено'}",
            f"Телефон:  {lead.phone or 'не знайдено'}",
            f"Місто:    {lead.city or 'не вказано'}",
            "",
            f"Опис: {lead.description}",
            "",
        ]

        if note:
            lines.append(f"Примітка: {note}")
            lines.append("")

        lines.extend([
            "Дія: Надіслати КП (proposal.pdf) та текст листа (email.txt)",
            "=" * 50,
        ])

        with open(card_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
