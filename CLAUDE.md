# MTP Fulfillment — Lead Generation Agent

## Компанія
MTP Fulfillment — 3PL/фулфілмент провайдер, Бориспіль, Україна.

## Тарифи МТП
- Прийом товару: 2 грн/одиниця
- Зберігання паллет: 800 грн/місяць
- Зберігання коробка: 80 грн/місяць
- Комплектація B2C (1-3 од.): 22 грн/замовлення
- Комплектація B2B: 45 грн/замовлення
- Пакування: 8 грн/замовлення
- Відправка НП: за тарифом Нової Пошти

## Архітектура
Мультиагентна система з 4 агентів:

1. **ResearchAgent** (`agents/research_agent.py`) — пошук лідів (Prom.ua, Google Maps)
2. **AnalysisAgent** (`agents/analysis_agent.py`) — аналіз через Gemini/Claude API
3. **ContentAgent** (`agents/content_agent.py`) — генерація PDF КП + email
4. **OutreachAgent** (`agents/outreach_agent.py`) — відправка/збереження контактів
5. **Orchestrator** (`agents/orchestrator.py`) — координація pipeline

## Запуск
```bash
python main.py           # 5 лідів
python main.py 10        # 10 лідів
python main.py 5 --send  # + автовідправка
```

## Результати
Зберігаються в `results/run_YYYYMMDD_HHMM/`:
- Папка на кожного клієнта з PDF + email.txt
- Зведений `leads_summary.csv`
