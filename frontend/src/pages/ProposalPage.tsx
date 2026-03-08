import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_URL || "https://mtp-agent-production.up.railway.app";

interface Proposal {
  id: string;
  slug: string;
  client_name: string;
  client_data: {
    hook?: string;
    client_insight?: string;
    pain_points?: Array<{ title: string; description: string } | string>;
    key_benefits?: Array<{ benefit: string; proof: string } | string>;
    mtp_fit?: string;
    score?: number;
    grade?: string;
    city?: string;
    products_count?: number;
    website?: string;
  };
  pricing_data: {
    tariffs?: Array<{ name: string; price: string }>;
    estimate?: Record<string, string>;
  };
  calendly_url: string;
}

function track(proposalId: string, event: string) {
  fetch(`${API_BASE}/api/proposals/track`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ proposal_id: proposalId, event, ts: new Date().toISOString() }),
  }).catch(() => {});
}

export default function ProposalPage() {
  const { slug } = useParams<{ slug: string }>();
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!slug) return;
    fetch(`${API_BASE}/api/proposals/${slug}`)
      .then((r) => {
        if (!r.ok) throw new Error("Not found");
        return r.json();
      })
      .then((data) => {
        setProposal(data);
        track(data.id, "open");
      })
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#080810] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[#d4a843] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (notFound || !proposal) {
    return (
      <div className="min-h-screen bg-[#080810] flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-[#e8e4dc] mb-4">404</h1>
          <p className="text-[#6e6a64]">Пропозицію не знайдено</p>
        </div>
      </div>
    );
  }

  const d = proposal.client_data;
  const p = proposal.pricing_data;
  const pains = d.pain_points || [];
  const benefits = d.key_benefits || [];
  const tariffs = p.tariffs || [
    { name: "Прийом товару", price: "2 грн / од." },
    { name: "Зберігання (паллет)", price: "800 грн / міс" },
    { name: "Зберігання (коробка)", price: "80 грн / міс" },
    { name: "Комплектація B2C", price: "22 грн / замовлення" },
    { name: "Комплектація B2B", price: "45 грн / замовлення" },
    { name: "Пакування", price: "8 грн / замовлення" },
    { name: "Відправка НП", price: "за тарифом НП" },
  ];
  const estimate = p.estimate || {};

  const handleCalendly = () => {
    track(proposal.id, "calendly_click");
    window.open(proposal.calendly_url, "_blank");
  };

  const handlePdf = () => {
    track(proposal.id, "pdf_download");
    window.print();
  };

  return (
    <div className="min-h-screen bg-[#080810] text-[#e8e4dc]" style={{ fontFamily: "'Inter', sans-serif" }}>
      {/* Google Fonts */}
      <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet" />

      {/* Print styles */}
      <style>{`
        @media print {
          body { background: #080810 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
          .no-print { display: none !important; }
          .print-break { page-break-before: always; }
        }
      `}</style>

      {/* ══════ HERO ══════ */}
      <section className="relative min-h-screen flex flex-col justify-center px-6 md:px-16 lg:px-24 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-[#080810] via-[#0d0d1a] to-[#121225]" />
        <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-[#d4a843]/5 rounded-full blur-[150px]" />

        <div className="relative z-10 max-w-6xl mx-auto w-full">
          <div className="mb-12">
            <span className="text-[#d4a843] text-sm tracking-[0.3em] uppercase" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
              MTP Fulfillment
            </span>
          </div>

          <h1
            className="text-5xl md:text-7xl lg:text-8xl font-bold mb-6 leading-[1.05]"
            style={{ fontFamily: "'Playfair Display', serif" }}
          >
            {proposal.client_name}
          </h1>

          <p className="text-xl md:text-2xl text-[#6e6a64] max-w-2xl mb-16 leading-relaxed">
            {d.hook || "Комерційна пропозиція"}
          </p>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-12">
            {[
              { num: "7+", label: "років на ринку" },
              { num: "60K+", label: "відправок / міс" },
              { num: "2", label: "склади під Києвом" },
              { num: "30с", label: "середній час збірки" },
            ].map((s) => (
              <div key={s.label}>
                <div className="text-4xl md:text-5xl font-bold text-[#d4a843]" style={{ fontFamily: "'Playfair Display', serif" }}>
                  {s.num}
                </div>
                <div className="text-xs text-[#6e6a64] mt-2 uppercase tracking-wider" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                  {s.label}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 no-print">
          <div className="w-px h-16 bg-gradient-to-b from-transparent to-[#d4a843]/40" />
        </div>
      </section>

      {/* ══════ YOUR BUSINESS ══════ */}
      {d.client_insight && (
        <section className="py-24 px-6 md:px-16 lg:px-24 print-break">
          <div className="max-w-6xl mx-auto">
            <SectionLabel text="Ваш бізнес" />
            <h2 className="text-3xl md:text-4xl font-bold mb-12" style={{ fontFamily: "'Playfair Display', serif" }}>
              Ми розуміємо вашу специфіку
            </h2>
            <div className="grid md:grid-cols-2 gap-6">
              {[
                { icon: "📦", title: d.products_count ? `${d.products_count}+ SKU` : "Широкий асортимент", desc: "позицій у вашому каталозі" },
                { icon: "📍", title: d.city || "Україна", desc: "географія вашого бізнесу" },
                { icon: "🌐", title: d.website ? "Онлайн-продажі" : "E-commerce", desc: "канал дистрибуції" },
                { icon: "📈", title: `Оцінка: ${d.score || "—"}/10`, desc: `Потенціал: ${d.grade || "—"}` },
              ].map((card) => (
                <div
                  key={card.title}
                  className="bg-[#0d0d1a] border border-[#1a1a2e] rounded-2xl p-6 hover:border-[#d4a843]/30 transition-colors"
                >
                  <span className="text-3xl mb-4 block">{card.icon}</span>
                  <h3 className="text-lg font-bold mb-1">{card.title}</h3>
                  <p className="text-sm text-[#6e6a64]">{card.desc}</p>
                </div>
              ))}
            </div>
            <p className="text-lg text-[#6e6a64] mt-8 leading-relaxed max-w-3xl">
              {d.client_insight}
            </p>
          </div>
        </section>
      )}

      {/* ══════ PAIN POINTS ══════ */}
      {pains.length > 0 && (
        <section className="py-24 px-6 md:px-16 lg:px-24 bg-[#0a0a14] print-break">
          <div className="max-w-6xl mx-auto">
            <SectionLabel text="Що болить" />
            <h2 className="text-3xl md:text-4xl font-bold mb-12" style={{ fontFamily: "'Playfair Display', serif" }}>
              Де втрачається ефективність
            </h2>
            <div className="space-y-8">
              {pains.slice(0, 3).map((pain, i) => {
                const title = typeof pain === "string" ? pain : pain.title;
                const desc = typeof pain === "string" ? "" : pain.description;
                return (
                  <div key={i} className="flex gap-6 md:gap-10 items-start">
                    <div
                      className="text-5xl md:text-6xl font-bold text-[#d4a843]/20 flex-shrink-0 w-20 text-right"
                      style={{ fontFamily: "'Playfair Display', serif" }}
                    >
                      {String(i + 1).padStart(2, "0")}
                    </div>
                    <div className="border-l border-[#d4a843]/30 pl-6 md:pl-10 pb-4">
                      <h3 className="text-xl md:text-2xl font-bold mb-2">{title}</h3>
                      {desc && <p className="text-[#6e6a64] leading-relaxed">{desc}</p>}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      )}

      {/* ══════ WHY MTP ══════ */}
      {benefits.length > 0 && (
        <section className="py-24 px-6 md:px-16 lg:px-24 print-break">
          <div className="max-w-6xl mx-auto">
            <SectionLabel text="Чому MTP" />
            <h2 className="text-3xl md:text-4xl font-bold mb-12" style={{ fontFamily: "'Playfair Display', serif" }}>
              Ключові переваги
            </h2>
            <div className="grid md:grid-cols-2 gap-6">
              {benefits.slice(0, 4).map((kb, i) => {
                const benefit = typeof kb === "string" ? kb : kb.benefit;
                const proof = typeof kb === "string" ? "" : kb.proof;
                return (
                  <div
                    key={i}
                    className="bg-[#0d0d1a] border border-[#1a1a2e] rounded-2xl p-8 hover:border-[#d4a843]/30 transition-colors group"
                  >
                    <div className="text-[#d4a843] text-xs tracking-widest mb-4" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                      0{i + 1}
                    </div>
                    <h3 className="text-lg font-bold mb-3 group-hover:text-[#d4a843] transition-colors">
                      {benefit}
                    </h3>
                    {proof && <p className="text-sm text-[#6e6a64] leading-relaxed">{proof}</p>}
                  </div>
                );
              })}
            </div>
            {d.mtp_fit && (
              <p className="text-lg text-[#6e6a64] mt-8 leading-relaxed max-w-3xl">
                {d.mtp_fit}
              </p>
            )}
          </div>
        </section>
      )}

      {/* ══════ HOW IT WORKS ══════ */}
      <section className="py-24 px-6 md:px-16 lg:px-24 bg-[#0a0a14] print-break">
        <div className="max-w-6xl mx-auto">
          <SectionLabel text="Як це працює" />
          <h2 className="text-3xl md:text-4xl font-bold mb-16" style={{ fontFamily: "'Playfair Display', serif" }}>
            Від заявки до першої відправки
          </h2>
          <div className="grid md:grid-cols-4 gap-8">
            {[
              { day: "День 1", title: "Знайомство", desc: "Zoom-дзвінок, обговорення потреб і процесів" },
              { day: "День 3-5", title: "Інтеграція", desc: "Підключення API, налаштування складу та логістики" },
              { day: "День 7", title: "Тестова партія", desc: "Прийом товару, тестова комплектація та відправка" },
              { day: "День 14", title: "Повний запуск", desc: "Все працює на автоматі, ви контролюєте з кабінету" },
            ].map((step, i) => (
              <div key={i} className="relative">
                {i < 3 && (
                  <div className="hidden md:block absolute top-8 left-full w-full h-px bg-gradient-to-r from-[#d4a843]/30 to-transparent" />
                )}
                <div className="text-[#d4a843] text-xs tracking-widest mb-4" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                  {step.day}
                </div>
                <div className="w-4 h-4 rounded-full bg-[#d4a843] mb-6" />
                <h3 className="text-lg font-bold mb-2">{step.title}</h3>
                <p className="text-sm text-[#6e6a64] leading-relaxed">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══════ PRICING ══════ */}
      <section className="py-24 px-6 md:px-16 lg:px-24 print-break">
        <div className="max-w-6xl mx-auto">
          <SectionLabel text="Тарифи" />
          <h2 className="text-3xl md:text-4xl font-bold mb-12" style={{ fontFamily: "'Playfair Display', serif" }}>
            Прозоре ціноутворення
          </h2>
          <div className="grid lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2">
              <div className="bg-[#0d0d1a] border border-[#1a1a2e] rounded-2xl overflow-hidden">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-[#1a1a2e]">
                      <th
                        className="text-left p-4 text-xs text-[#6e6a64] uppercase tracking-wider"
                        style={{ fontFamily: "'JetBrains Mono', monospace" }}
                      >
                        Послуга
                      </th>
                      <th
                        className="text-right p-4 text-xs text-[#6e6a64] uppercase tracking-wider"
                        style={{ fontFamily: "'JetBrains Mono', monospace" }}
                      >
                        Тариф
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {tariffs.map((t, i) => (
                      <tr key={i} className="border-b border-[#1a1a2e]/50 hover:bg-[#d4a843]/5 transition-colors">
                        <td className="p-4 text-sm">{t.name}</td>
                        <td className="p-4 text-sm text-right text-[#d4a843] font-medium">{t.price}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {Object.keys(estimate).length > 0 && (
              <div className="bg-gradient-to-br from-[#d4a843]/10 to-[#0d0d1a] border border-[#d4a843]/20 rounded-2xl p-8">
                <h3
                  className="text-[#d4a843] text-xs tracking-widest uppercase mb-6"
                  style={{ fontFamily: "'JetBrains Mono', monospace" }}
                >
                  Орієнтовний кошторис
                </h3>
                <div className="space-y-4">
                  {Object.entries(estimate).map(([key, val], i, arr) => (
                    <div key={key}>
                      <div className="flex justify-between items-baseline">
                        <span className="text-sm text-[#6e6a64]">{key.replace(/_/g, " ")}</span>
                        <span className={`text-sm font-medium ${i === arr.length - 1 ? "text-[#d4a843] text-lg font-bold" : ""}`}>
                          {val}
                        </span>
                      </div>
                      {i < arr.length - 1 && <div className="h-px bg-[#1a1a2e] mt-4" />}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ══════ TRUST ══════ */}
      <section className="py-24 px-6 md:px-16 lg:px-24 bg-[#0a0a14] print-break">
        <div className="max-w-6xl mx-auto text-center">
          <SectionLabel text="Нам довіряють" center />
          <h2 className="text-3xl md:text-4xl font-bold mb-16" style={{ fontFamily: "'Playfair Display', serif" }}>
            Наші клієнти
          </h2>
          <div className="flex flex-wrap justify-center gap-12 md:gap-20 items-center">
            {["KRKR", "ORNER", "ELEMIS"].map((name) => (
              <div
                key={name}
                className="text-3xl md:text-4xl font-bold text-[#6e6a64]/40 hover:text-[#d4a843]/60 transition-colors"
                style={{ fontFamily: "'Playfair Display', serif" }}
              >
                {name}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══════ CTA ══════ */}
      <section className="py-32 px-6 md:px-16 lg:px-24 relative print-break">
        <div className="absolute inset-0 bg-gradient-to-t from-[#d4a843]/5 to-transparent" />
        <div className="relative max-w-4xl mx-auto text-center">
          <SectionLabel text="Наступний крок" center />
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-8" style={{ fontFamily: "'Playfair Display', serif" }}>
            Готові масштабуватись?
          </h2>
          <p className="text-xl text-[#6e6a64] mb-12 max-w-2xl mx-auto">
            Запишіться на безкоштовну Zoom-консультацію. Покажемо, як саме MTP може змінити вашу логістику.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center no-print">
            <button
              onClick={handleCalendly}
              className="px-10 py-4 bg-[#d4a843] text-[#080810] font-bold rounded-xl text-lg hover:bg-[#e0b854] transition-colors"
            >
              Записатись на Zoom
            </button>
            <button
              onClick={handlePdf}
              className="px-10 py-4 border border-[#d4a843]/40 text-[#d4a843] rounded-xl text-lg hover:bg-[#d4a843]/10 transition-colors"
            >
              Зберегти як PDF
            </button>
          </div>
        </div>
      </section>

      {/* ══════ FOOTER ══════ */}
      <footer className="py-12 px-6 md:px-16 border-t border-[#1a1a2e] no-print">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="text-[#d4a843] text-sm tracking-widest" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
            MTP FULFILLMENT
          </div>
          <div className="flex flex-wrap gap-6 text-sm text-[#6e6a64]">
            <a href="mailto:mtpgrouppromo@gmail.com" className="hover:text-[#d4a843] transition-colors">
              mtpgrouppromo@gmail.com
            </a>
            <span>+38 (050) 144-46-45</span>
            <a href="https://fulfillmentmtp.com.ua" target="_blank" rel="noopener noreferrer" className="hover:text-[#d4a843] transition-colors">
              fulfillmentmtp.com.ua
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}

function SectionLabel({ text, center }: { text: string; center?: boolean }) {
  return (
    <div
      className={`text-[#d4a843] text-xs tracking-[0.3em] uppercase mb-4 ${center ? "text-center" : ""}`}
      style={{ fontFamily: "'JetBrains Mono', monospace" }}
    >
      {text}
    </div>
  );
}
