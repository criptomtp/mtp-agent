import { useEffect, useState } from "react";
import { api } from "../lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

interface AnalyticsData {
  kpis: { total_leads: number; emails_sent: number; proposals_viewed: number; calendly_clicks: number };
  rates: { email_open_rate: number; proposal_to_calendly: number; avg_score: number; zoom_booked: number; engaged_30s: number; scrolled_to_end: number };
  funnel: { label: string; value: number }[];
  leads_by_day: { date: string; count: number }[];
  top_niches: { niche: string; count: number }[];
  score_distribution: { A: number; B: number; C: number; D: number };
  recent_events: { client_name: string; event: string; ts: string }[];
}

// ── Helpers ──────────────────────────────────────────────────────────────────

const EVENT_META: Record<string, { icon: string; label: string; color: string }> = {
  email_open:     { icon: "📧", label: "Відкрив email",     color: "#90cdf4" },
  open:           { icon: "👁",  label: "Відкрив КП",       color: "#63b3ed" },
  engaged_30s:    { icon: "⏱",  label: "Читає 30+ сек",    color: "#f6e05e" },
  scrolled_to_end:{ icon: "📜", label: "Дочитав до кінця",  color: "#68d391" },
  calendly_click: { icon: "📅", label: "Клік на Calendly",  color: "#f6ad55" },
  zoom_booked:    { icon: "🎉", label: "Забронював Zoom!",  color: "#fc8181" },
  pdf_download:   { icon: "📥", label: "Завантажив PDF",    color: "#b794f4" },
};

function relativeTime(ts: string): string {
  try {
    const diff = Date.now() - new Date(ts).getTime();
    const min = Math.floor(diff / 60000);
    if (min < 1) return "щойно";
    if (min < 60) return `${min} хв тому`;
    const h = Math.floor(min / 60);
    if (h < 24) return `${h} год тому`;
    return `${Math.floor(h / 24)} дн тому`;
  } catch {
    return "";
  }
}

// ── Sub-components ───────────────────────────────────────────────────────────

function KpiCard({ title, value, sub, color }: { title: string; value: string | number; sub?: string; color: string }) {
  return (
    <div className="bg-[#161b22] rounded-xl p-5 border border-white/5">
      <p className="text-xs text-gray-400 mb-1">{title}</p>
      <p className="text-3xl font-bold" style={{ color }}>{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  );
}

function RateCard({ title, value, sub, color }: { title: string; value: string; sub?: string; color: string }) {
  return (
    <div className="bg-[#161b22] rounded-xl p-5 border border-white/5">
      <p className="text-xs text-gray-400 mb-1">{title}</p>
      <p className="text-2xl font-bold" style={{ color }}>{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  );
}

function LineChart({ data }: { data: { date: string; count: number }[] }) {
  const max = Math.max(...data.map((d) => d.count), 1);
  const W = 560, H = 110, PAD_X = 8, PAD_Y = 12;
  const pts = data.map((d, i) => {
    const x = PAD_X + (i / (data.length - 1)) * (W - 2 * PAD_X);
    const y = H - PAD_Y - (d.count / max) * (H - 2 * PAD_Y);
    return [x, y] as [number, number];
  });
  const pointsStr = pts.map(([x, y]) => `${x},${y}`).join(" ");
  const areaPath =
    `M${pts[0][0]},${H - PAD_Y} ` +
    pts.map(([x, y]) => `L${x},${y}`).join(" ") +
    ` L${pts[pts.length - 1][0]},${H - PAD_Y} Z`;

  // Show every 5th label
  const labels = data.filter((_, i) => i % 5 === 0 || i === data.length - 1);

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-28" preserveAspectRatio="none">
        <defs>
          <linearGradient id="lineGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#48bb78" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#48bb78" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={areaPath} fill="url(#lineGrad)" />
        <polyline points={pointsStr} fill="none" stroke="#48bb78" strokeWidth="1.5" strokeLinejoin="round" />
        {pts.map(([x, y], i) =>
          data[i].count > 0 ? (
            <circle key={i} cx={x} cy={y} r="2.5" fill="#48bb78" />
          ) : null
        )}
      </svg>
      <div className="flex justify-between px-1 mt-1">
        {labels.map((d) => (
          <span key={d.date} className="text-[10px] text-gray-500">{d.date}</span>
        ))}
      </div>
    </div>
  );
}

function Funnel({ steps }: { steps: { label: string; value: number }[] }) {
  const max = steps[0]?.value || 1;
  const colors = ["#63b3ed", "#48bb78", "#f6ad55", "#fc8181"];
  return (
    <div className="space-y-2.5">
      {steps.map((step, i) => {
        const pct = max > 0 ? Math.round((step.value / max) * 100) : 0;
        const conv = i > 0 && steps[i - 1].value > 0
          ? `${Math.round((step.value / steps[i - 1].value) * 100)}%`
          : null;
        return (
          <div key={step.label}>
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs text-gray-300">{step.label}</span>
              <div className="flex items-center gap-2">
                {conv && (
                  <span className="text-[10px] text-gray-500">→ {conv}</span>
                )}
                <span className="text-sm font-bold" style={{ color: colors[i] }}>
                  {step.value}
                </span>
              </div>
            </div>
            <div className="h-5 bg-gray-800 rounded overflow-hidden">
              <div
                className="h-full rounded transition-all duration-700"
                style={{ width: `${Math.max(pct, step.value > 0 ? 2 : 0)}%`, backgroundColor: colors[i], opacity: 0.85 }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function NicheBar({ niches }: { niches: { niche: string; count: number }[] }) {
  const max = niches[0]?.count || 1;
  return (
    <div className="space-y-2">
      {niches.map((n) => (
        <div key={n.niche}>
          <div className="flex justify-between items-center mb-0.5">
            <span className="text-xs text-gray-300 truncate max-w-[140px]">{n.niche}</span>
            <span className="text-xs font-semibold text-gray-200">{n.count}</span>
          </div>
          <div className="h-3 bg-gray-800 rounded overflow-hidden">
            <div
              className="h-full rounded bg-[#b794f4]"
              style={{ width: `${Math.round((n.count / max) * 100)}%`, opacity: 0.8 }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function ScoreBar({ dist }: { dist: { A: number; B: number; C: number; D: number } }) {
  const total = Object.values(dist).reduce((a, b) => a + b, 0) || 1;
  const grades: { grade: string; color: string }[] = [
    { grade: "A", color: "#68d391" },
    { grade: "B", color: "#63b3ed" },
    { grade: "C", color: "#f6ad55" },
    { grade: "D", color: "#fc8181" },
  ];
  return (
    <div className="space-y-2">
      {grades.map(({ grade, color }) => {
        const count = dist[grade as keyof typeof dist];
        const pct = Math.round((count / total) * 100);
        return (
          <div key={grade} className="flex items-center gap-3">
            <span className="text-sm font-bold w-4" style={{ color }}>{grade}</span>
            <div className="flex-1 h-4 bg-gray-800 rounded overflow-hidden">
              <div className="h-full rounded" style={{ width: `${pct}%`, backgroundColor: color, opacity: 0.8 }} />
            </div>
            <span className="text-xs text-gray-400 w-12 text-right">{count} ({pct}%)</span>
          </div>
        );
      })}
    </div>
  );
}

function RecentEvents({ events }: { events: { client_name: string; event: string; ts: string }[] }) {
  if (events.length === 0) {
    return <p className="text-xs text-gray-500 text-center py-6">Поки немає подій</p>;
  }
  return (
    <div className="space-y-2 overflow-y-auto max-h-64">
      {events.map((e, i) => {
        const meta = EVENT_META[e.event] || { icon: "📌", label: e.event, color: "#a0aec0" };
        return (
          <div key={i} className="flex items-start gap-2.5 py-2 border-b border-white/5 last:border-0">
            <span className="text-base leading-none mt-0.5">{meta.icon}</span>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-gray-200 truncate">{e.client_name}</p>
              <p className="text-xs" style={{ color: meta.color }}>{meta.label}</p>
            </div>
            <span className="text-[10px] text-gray-500 whitespace-nowrap">{relativeTime(e.ts)}</span>
          </div>
        );
      })}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function Analytics() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getAnalytics()
      .then(setData)
      .catch(() => setError("Не вдалося завантажити аналітику"))
      .finally(() => setLoading(false));
  }, []);

  const today = new Date().toLocaleDateString("uk-UA", { day: "numeric", month: "long", year: "numeric" });

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0d1117] flex items-center justify-center">
        <p className="text-gray-400 text-sm animate-pulse">Завантаження аналітики...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-[#0d1117] flex items-center justify-center">
        <p className="text-red-400 text-sm">{error || "Помилка"}</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0d1117] text-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-7">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">MTP Analytics</h1>
          <p className="text-xs text-gray-500 mt-0.5">Вирва аутрічу · відкриття КП · Calendly</p>
        </div>
        <span className="text-sm text-gray-500">{today}</span>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-4 gap-4 mb-4">
        <KpiCard title="Лідів знайдено" value={data.kpis.total_leads} color="#63b3ed" sub="всього в базі" />
        <KpiCard title="Email надіслано" value={data.kpis.emails_sent} color="#48bb78"
          sub={`ще ${data.kpis.total_leads - data.kpis.emails_sent} в черзі`} />
        <KpiCard title="КП відкрито" value={data.kpis.proposals_viewed} color="#f6ad55"
          sub={data.kpis.emails_sent > 0 ? `${data.rates.email_open_rate}% open rate` : undefined} />
        <KpiCard title="Calendly кліки" value={data.kpis.calendly_clicks} color="#fc8181"
          sub={data.rates.zoom_booked > 0 ? `${data.rates.zoom_booked} зустрічей заброньовано` : "зустрічей ще немає"} />
      </div>

      {/* Rate cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <RateCard
          title="Email open rate"
          value={`${data.rates.email_open_rate}%`}
          sub={`${data.kpis.proposals_viewed} з ${data.kpis.emails_sent} надісланих`}
          color={data.rates.email_open_rate >= 30 ? "#48bb78" : data.rates.email_open_rate >= 15 ? "#f6ad55" : "#fc8181"}
        />
        <RateCard
          title="КП → Calendly"
          value={`${data.rates.proposal_to_calendly}%`}
          sub={`${data.kpis.calendly_clicks} з ${data.kpis.proposals_viewed} переглянутих`}
          color={data.rates.proposal_to_calendly >= 10 ? "#48bb78" : "#f6ad55"}
        />
        <RateCard
          title="Середній скор"
          value={data.rates.avg_score > 0 ? `${data.rates.avg_score} / 10` : "—"}
          sub={`${data.rates.scrolled_to_end} прочитали до кінця · ${data.rates.engaged_30s} читали 30+ сек`}
          color={data.rates.avg_score >= 7 ? "#48bb78" : data.rates.avg_score >= 5 ? "#f6ad55" : "#fc8181"}
        />
      </div>

      {/* Chart + Recent events */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="col-span-2 bg-[#161b22] rounded-xl p-5 border border-white/5">
          <p className="text-sm font-semibold text-gray-200 mb-3">Ліди за 30 днів</p>
          <LineChart data={data.leads_by_day} />
        </div>
        <div className="bg-[#161b22] rounded-xl p-5 border border-white/5">
          <p className="text-sm font-semibold text-gray-200 mb-3">Активність з КП</p>
          <RecentEvents events={data.recent_events} />
        </div>
      </div>

      {/* Funnel + Top niches */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="bg-[#161b22] rounded-xl p-5 border border-white/5">
          <p className="text-sm font-semibold text-gray-200 mb-4">Вирва аутрічу</p>
          <Funnel steps={data.funnel} />
        </div>
        <div className="bg-[#161b22] rounded-xl p-5 border border-white/5">
          <p className="text-sm font-semibold text-gray-200 mb-4">Топ ніші</p>
          {data.top_niches.length > 0
            ? <NicheBar niches={data.top_niches} />
            : <p className="text-xs text-gray-500">Ніш поки немає</p>
          }
        </div>
      </div>

      {/* Score distribution */}
      <div className="bg-[#161b22] rounded-xl p-5 border border-white/5">
        <p className="text-sm font-semibold text-gray-200 mb-4">Розподіл скорингу</p>
        <ScoreBar dist={data.score_distribution} />
      </div>
    </div>
  );
}
