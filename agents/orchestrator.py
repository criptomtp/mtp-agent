"""Orchestrator — координація всіх агентів."""

import os
import csv
import re
from datetime import datetime
from dataclasses import asdict
from typing import List, Dict, Any, Optional

from .research_agent import ResearchAgent, Lead
from .analysis_agent import AnalysisAgent
from .content_agent import ContentAgent
from .outreach_agent import OutreachAgent


class Orchestrator:
    """Координує pipeline: Research → Analysis → Content → Outreach."""

    def __init__(self, send_email: bool = False, api_keys: Optional[Dict[str, str]] = None, tariffs: Optional[List[Dict[str, Any]]] = None, channels: Optional[List[str]] = None):
        self.research = ResearchAgent(api_keys=api_keys, channels=channels)
        self.analysis = AnalysisAgent(api_keys=api_keys)
        self.content = ContentAgent()
        self.outreach = OutreachAgent()
        self.send_email = send_email
        self.tariffs = tariffs

    def run(self, count: int = 5) -> str:
        """Запускає повний pipeline. Повертає шлях до папки результатів."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        run_dir = os.path.join("results", f"run_{timestamp}")
        os.makedirs(run_dir, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"  MTP Fulfillment — Lead Generation Agent")
        print(f"  Запуск: {timestamp} | Лідів: {count}")
        print(f"{'='*60}\n")

        # 1. Research
        print("[1/4] ResearchAgent: пошук лідів...")
        leads = self.research.search(count)
        print(f"  Знайдено {len(leads)} лідів.\n")

        summary_rows: List[Dict[str, str]] = []

        for i, lead in enumerate(leads, 1):
            safe_name = re.sub(r"[^\w\s-]", "", lead.name).strip().replace(" ", "_")[:50]
            lead_dir = os.path.join(run_dir, f"{i:02d}_{safe_name}")
            os.makedirs(lead_dir, exist_ok=True)

            print(f"--- Лід {i}/{len(leads)}: {lead.name} ---")

            # 2. Analysis
            print(f"[2/4] AnalysisAgent: аналіз...")
            analysis = self.analysis.analyze(lead, tariffs=self.tariffs)

            # 3. Content
            print(f"[3/4] ContentAgent: генерація КП...")
            files = self.content.generate(lead, analysis, lead_dir, tariffs=self.tariffs)
            print(f"  PDF: {files['pdf']}")
            print(f"  Email: {files['email']}")

            # 4. Outreach
            print(f"[4/4] OutreachAgent: обробка контакту...")
            outreach_status = self.outreach.process(lead, lead_dir, self.send_email)
            print(f"  Статус: {outreach_status}\n")

            summary_rows.append({
                "name": lead.name,
                "website": lead.website,
                "email": lead.email,
                "phone": lead.phone,
                "city": lead.city,
                "source": lead.source,
                "outreach_status": outreach_status,
                "folder": lead_dir,
            })

        # Зведений CSV
        csv_path = os.path.join(run_dir, "leads_summary.csv")
        if summary_rows:
            with open(csv_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=summary_rows[0].keys())
                writer.writeheader()
                writer.writerows(summary_rows)

        print(f"{'='*60}")
        print(f"  Готово! Результати: {run_dir}")
        print(f"  Зведений CSV: {csv_path}")
        print(f"  Оброблено лідів: {len(leads)}")
        print(f"{'='*60}\n")

        return run_dir
