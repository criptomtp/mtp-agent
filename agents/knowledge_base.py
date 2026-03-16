"""MTP Fulfillment Knowledge Base — constants used by all agents."""

MTP_TARIFFS = {
    "storage_per_m3": 650,  # грн/м³/міс
    "storage_display": "325 грн / 0.5 м³/міс",
    "fulfillment_b2c_from": 18,
    "fulfillment_b2c_display": "від 18 грн/замовлення",
    "fulfillment_b2b": 45,
    "fulfillment_b2b_display": "від 45 грн/відвантаження",
    "receiving_box": 20,
    "receiving_box_display": "20 грн/коробка",
    "receiving_pallet": 80,
    "receiving_pallet_display": "80 грн/палета",
    "receiving_unit": 3,
    "receiving_unit_display": "3 грн/одиниця",
    "replenishment_from": 2,
    "replenishment_display": "від 2 грн/одиниця",
    "min_payment": 5000,
}

MTP_COMPANY = {
    "name": "MTP Group Fulfillment",
    "years": "7+",
    "shipments_per_month": "60 000+",
    "warehouses": 2,
    "location": "Бориспіль (біля Київ)",
    "email": "mtpgrouppromo@gmail.com",
    "phone": "+38 (050) 144-46-45",
    "phone_raw": "+380501444645",
    "website": "https://fulfillmentmtp.com.ua",
    "calendly": "https://calendly.com/mtpgrouppromo/30min",
    "instagram": "@nikolay_mtp",
}

MTP_CLIENTS = [
    {"name": "KRKR", "url": "https://krkr.com.ua"},
    {"name": "ORNER", "url": "https://orner.com.ua"},
    {"name": "ELEMIS", "url": "https://elemis.com.ua"},
]


def get_tariffs_prompt_text() -> str:
    """Structured tariffs text for Gemini prompt — prevents mixing up values."""
    t = MTP_TARIFFS
    return f"""Тарифна сітка (використовуй ТОЧНО ці значення, НЕ змішуй категорії):

ПРИЙМАННЯ товару на склад:
- Коробка: {t['receiving_box_display']}
- Палета: {t['receiving_pallet_display']}
- Поштучно: {t['receiving_unit_display']}

ЗБЕРІГАННЯ на складі:
- {t['storage_display']} (це вартість ЗБЕРІГАТИ товар на складі)

ВІДВАНТАЖЕННЯ замовлень (фулфілмент):
- B2C (кінцевому покупцю): {t['fulfillment_b2c_display']}
- B2B (оптове відвантаження): {t['fulfillment_b2b_display']}

ДОДАТКОВІ послуги:
- Доукомплектація: {t['replenishment_display']}

НЕ пиши мінімальний платіж ({t['min_payment']} грн) в таблиці тарифів — це умова договору, не тариф."""


def get_clients_text() -> str:
    """Clients reference text with links."""
    return ", ".join([f"{c['name']} ({c['url']})" for c in MTP_CLIENTS])


def get_company_contacts_text() -> str:
    """Company contacts text."""
    c = MTP_COMPANY
    return f"{c['email']}, {c['phone']}, {c['website']}"
