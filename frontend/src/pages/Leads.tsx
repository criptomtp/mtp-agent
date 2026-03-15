import { useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";
import LeadTable from "../components/LeadTable";

function ScoreBadge({ score, grade, label }: { score: number; grade: string; label: string }) {
  const color = score >= 8 ? "bg-green-100 text-green-800 border-green-300"
    : score >= 6 ? "bg-yellow-100 text-yellow-800 border-yellow-300"
    : score >= 4 ? "bg-orange-100 text-orange-800 border-orange-300"
    : "bg-gray-100 text-gray-600 border-gray-300";
  const emoji = score >= 8 ? "🔥" : score >= 6 ? "⭐" : score >= 4 ? "📊" : "💤";
  return (
    <div className="flex items-center gap-2">
      <span className={`px-3 py-1 rounded-full text-sm font-bold border ${color}`}>
        {score}/10 {emoji}
      </span>
      <span className="text-sm font-semibold text-gray-600">{grade}</span>
      {label && <span className="text-sm text-gray-500">— {label}</span>}
    </div>
  );
}

function OutreachBadge({ status }: { status: string }) {
  if (!status) return null;
  const isReady = status.startsWith("ready");
  const isSent = status === "email_sent" || status.startsWith("sent:");
  const isError = status.startsWith("error:");
  const color = isSent ? "bg-green-100 text-green-700 border-green-300"
    : isReady ? "bg-blue-100 text-blue-700 border-blue-300"
    : isError ? "bg-red-100 text-red-700 border-red-300"
    : "bg-yellow-100 text-yellow-700 border-yellow-300";
  const emoji = isSent ? "✅" : isReady ? "📨" : isError ? "❌" : "✋";
  const label = isSent ? "відправлено" : isReady ? status.replace("ready:", "") : isError ? "помилка" : status;
  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${color}`}>
      {emoji} {label}
    </span>
  );
}

function ContactRow({ icon, label, value, href, external }: {
  icon: string; label: string; value?: string; href?: string; external?: boolean;
}) {
  if (!value) return null;
  return (
    <div className="flex items-center gap-2 py-1.5">
      <span className="text-lg">{icon}</span>
      <span className="text-xs text-gray-400 w-14">{label}</span>
      {href ? (
        <a href={href} target={external ? "_blank" : undefined} rel={external ? "noopener noreferrer" : undefined}
          className="text-sm text-blue-600 hover:underline truncate">
          {value}
        </a>
      ) : (
        <span className="text-sm font-medium text-gray-800">{value}</span>
      )}
    </div>
  );
}

function CollapsibleSection({ title, defaultOpen, children }: {
  title: string; defaultOpen?: boolean; children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen ?? false);
  return (
    <div className="border border-gray-200 rounded-lg mb-3">
      <button onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition">
        <span>{title}</span>
        <span className="text-gray-400">{open ? "▲" : "▼"}</span>
      </button>
      {open && <div className="px-4 pb-4">{children}</div>}
    </div>
  );
}

export default function Leads() {
  const [leads, setLeads] = useState<any[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState<any | null>(null);
  const [files, setFiles] = useState<any[]>([]);
  const [copied, setCopied] = useState(false);
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [sending, setSending] = useState(false);

  const reload = useCallback(() => {
    api.getLeads({ status: statusFilter || undefined }).then(setLeads).catch(() => {});
  }, [statusFilter]);

  useEffect(() => { reload(); }, [reload]);

  const handleSelect = useCallback(async (lead: any) => {
    try {
      const full = await api.getLead(lead.id);
      setSelected(full);
      setFiles(full.files || []);
    } catch {
      setSelected(lead);
      setFiles([]);
    }
    setCopied(false);
  }, []);

  const close = useCallback(() => { setSelected(null); setFiles([]); }, []);

  const htmlFile = files.find((f: any) => f.file_type === "html") || files.find((f: any) => f.file_type === "pdf");
  const pptxFile = files.find((f: any) => f.file_type === "pptx");
  const emailFile = files.find((f: any) => f.file_type === "email");
  const contactFile = files.find((f: any) => f.file_type === "contact_card");
  const proposalUrl = selected
    ? (selected.proposal_url || (htmlFile ? `${import.meta.env.VITE_API_URL || ""}/api/leads/${selected.id}/proposal` : null))
    : null;
  const pptxUrl = selected && pptxFile
    ? `${import.meta.env.VITE_API_URL || ""}/api/leads/${selected.id}/proposal.pptx`
    : null;
  const emailText = emailFile?.content_text || "";
  const contactText = contactFile?.content_text || "";

  const handleCopyEmail = useCallback(async () => {
    if (!emailText) return;
    try {
      await navigator.clipboard.writeText(emailText);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = emailText;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [emailText]);

  const handleMarkSent = useCallback(async () => {
    if (!selected) return;
    setUpdatingStatus(true);
    try {
      await api.updateLeadStatus(selected.id, "email_sent");
      setSelected({ ...selected, outreach_status: "email_sent" });
      reload();
    } catch { /* ignore */ }
    setUpdatingStatus(false);
  }, [selected, reload]);

  const handleSendEmail = useCallback(async () => {
    if (!selected?.email) return;
    if (!confirm(`Відправити email на ${selected.email} для ${selected.name}?`)) return;
    setSending(true);
    try {
      const BASE = import.meta.env.VITE_API_URL || "";
      const r = await fetch(`${BASE}/api/outreach/send/${selected.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const data = await r.json();
      if (data.ok) {
        setSelected({ ...selected, outreach_status: `sent:${selected.email}` });
        reload();
      } else {
        alert(`Помилка: ${data.error}`);
      }
    } catch (e) {
      alert(`Помилка відправки`);
    }
    setSending(false);
  }, [selected, reload]);

  // Parse analysis
  const analysis = selected?.analysis_json || {};
  const score = selected?.score ?? analysis.score ?? 0;
  const grade = selected?.score_grade ?? analysis.grade ?? "D";
  const label = analysis.score_label ?? "";
  const reasons: string[] = analysis.score_reasons ?? [];
  const painPoints: string[] = analysis.pain_points ?? [];
  const potential = analysis.potential ?? "";
  const companyAnalysis = analysis.company_analysis ?? "";
  const valueProposition = analysis.mtp_value_proposition ?? "";
  const personalization = analysis.personalization ?? "";

  const potentialColor = potential === "high" ? "text-green-700 bg-green-50"
    : potential === "medium" ? "text-yellow-700 bg-yellow-50"
    : "text-gray-600 bg-gray-50";

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-mtp-blue">Leads</h2>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
          className="border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-mtp-blue/30">
          <option value="">All statuses</option>
          <option value="new">New</option>
          <option value="contacted">Contacted</option>
          <option value="converted">Converted</option>
          <option value="rejected">Rejected</option>
        </select>
      </div>

      <div className="bg-white rounded-lg shadow p-5">
        <LeadTable leads={leads} onSelect={handleSelect} />
      </div>

      {/* ===== Lead Detail Modal ===== */}
      {selected && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={close}>
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl m-4 max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}>

            {/* ── Section 1: Header ── */}
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 rounded-t-xl z-10">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-xl font-bold text-mtp-blue mb-2">{selected.name}</h3>
                  <div className="flex items-center gap-3 flex-wrap">
                    <ScoreBadge score={score} grade={grade} label={label} />
                    <OutreachBadge status={selected.outreach_status} />
                    {selected.source && (
                      <span className="px-2 py-0.5 bg-gray-100 text-gray-500 text-xs rounded-full">
                        {selected.source}
                      </span>
                    )}
                  </div>
                </div>
                <button onClick={close}
                  className="text-gray-400 hover:text-gray-600 text-2xl leading-none px-2">
                  &times;
                </button>
              </div>
            </div>

            <div className="px-6 py-5 space-y-4">

              {/* ── Section 2: Contacts ── */}
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Контакти</h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6">
                  <ContactRow icon="📧" label="Email" value={selected.email} href={selected.email ? `mailto:${selected.email}` : undefined} />
                  <ContactRow icon="📞" label="Телефон" value={selected.phone} href={selected.phone ? `tel:${selected.phone}` : undefined} />
                  {selected.extra_phones && (
                    <ContactRow icon="📞" label="Додатково" value={selected.extra_phones} />
                  )}
                  <ContactRow icon="🌐" label="Сайт" value={selected.website} href={selected.website} external />
                  <ContactRow icon="📍" label="Місто" value={selected.city} />
                  {selected.instagram && (
                    <ContactRow icon="📸" label="Instagram" value={selected.instagram}
                      href={selected.instagram.startsWith("http") ? selected.instagram : `https://instagram.com/${selected.instagram}`} external />
                  )}
                  {selected.telegram && (
                    <ContactRow icon="✈️" label="Telegram" value={selected.telegram}
                      href={selected.telegram.startsWith("http") ? selected.telegram : `https://t.me/${selected.telegram}`} external />
                  )}
                  {selected.social_media && (() => {
                    try {
                      const social = typeof selected.social_media === 'string'
                        ? JSON.parse(selected.social_media)
                        : selected.social_media;
                      const platformIcons: Record<string, string> = {
                        instagram: "📸", facebook: "👤", tiktok: "🎵",
                        telegram: "✈️", youtube: "▶️", linkedin: "💼",
                      };
                      return Object.entries(social).map(([platform, url]) => (
                        <ContactRow key={platform}
                          icon={platformIcons[platform] || "🔗"}
                          label={platform}
                          value={url as string}
                          href={url as string}
                          external />
                      ));
                    } catch { return null; }
                  })()}
                </div>
                {!selected.email && !selected.phone && !selected.website && (
                  <p className="text-sm text-gray-400 italic mt-1">Контакти не знайдено</p>
                )}
              </div>

              {/* ── Section 3: Analysis ── */}
              <CollapsibleSection title="📊 Аналіз MTP" defaultOpen={true}>
                {potential && (
                  <div className="mb-3">
                    <span className="text-xs text-gray-400">Потенціал:</span>{" "}
                    <span className={`px-2 py-0.5 rounded text-sm font-semibold ${potentialColor}`}>
                      {potential}
                    </span>
                  </div>
                )}

                {companyAnalysis && (
                  <div className="mb-3">
                    <p className="text-xs text-gray-400 mb-1">Про компанію:</p>
                    <p className="text-sm text-gray-700">{companyAnalysis}</p>
                  </div>
                )}

                {valueProposition && (
                  <div className="mb-3">
                    <p className="text-xs text-gray-400 mb-1">Чому MTP підходить:</p>
                    <p className="text-sm text-gray-700">{valueProposition}</p>
                  </div>
                )}

                {personalization && (
                  <div className="mb-3">
                    <p className="text-xs text-gray-400 mb-1">Персоналізація:</p>
                    <p className="text-sm text-gray-700 italic">{personalization}</p>
                  </div>
                )}

                {painPoints.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs text-gray-400 mb-1">Болі клієнта:</p>
                    <ul className="space-y-1">
                      {painPoints.map((p: any, i: number) => (
                        <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                          <span className="text-orange-400 mt-0.5">•</span>
                          <span>
                            {typeof p === "object" ? (
                              <><strong>{p.title}</strong>{p.description && <> — {p.description}</>}</>
                            ) : p}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {analysis.key_benefits?.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs text-gray-400 mb-1">Ключові переваги:</p>
                    <ul className="space-y-1">
                      {analysis.key_benefits.map((b: any, i: number) => (
                        <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                          <span className="text-green-500 mt-0.5">✓</span>
                          <span>
                            {typeof b === "object" ? (
                              <>{b.benefit}{b.proof && <em className="text-gray-500"> ({b.proof})</em>}</>
                            ) : b}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {reasons.length > 0 && (
                  <div>
                    <p className="text-xs text-gray-400 mb-1">Scoring:</p>
                    <ul className="space-y-0.5">
                      {reasons.map((r: any, i: number) => (
                        <li key={i} className="text-xs text-gray-500">
                          — {typeof r === "object" ? JSON.stringify(r) : r}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {analysis.pricing_estimate && (
                  <div className="mt-3 bg-white rounded border border-gray-200 p-3">
                    <p className="text-xs text-gray-400 mb-2">Орієнтовний кошторис:</p>
                    {Object.entries(analysis.pricing_estimate).map(([k, v]) => (
                      <div key={k} className="flex justify-between text-sm py-0.5">
                        <span className="text-gray-600">{k.replace(/_/g, " ")}</span>
                        <span className="font-medium text-gray-800">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </CollapsibleSection>

              {/* ── Section 4: Documents ── */}
              <CollapsibleSection title="📄 Документи" defaultOpen={true}>
                {/* HTML Presentation */}
                {proposalUrl && (
                  <div className="flex items-center gap-3 mb-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                    <span className="text-2xl">🎯</span>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-800">Комерційна пропозиція</p>
                      <p className="text-xs text-gray-400">{selected?.proposal_url ? "web-версія для клієнта" : "proposal.html"}</p>
                    </div>
                    <a href={proposalUrl} target="_blank" rel="noopener noreferrer"
                      className="px-3 py-1.5 bg-mtp-blue text-white text-sm rounded hover:bg-blue-800 transition">
                      Відкрити КП
                    </a>
                  </div>
                )}

                {/* PPTX Download */}
                {pptxUrl && (
                  <div className="flex items-center gap-3 mb-3 p-3 bg-green-50 rounded-lg border border-green-200">
                    <span className="text-2xl">📊</span>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-800">Презентація PPTX</p>
                      <p className="text-xs text-gray-400">proposal.pptx</p>
                    </div>
                    <a href={pptxUrl} download
                      className="px-3 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition">
                      Завантажити
                    </a>
                  </div>
                )}

                {/* Email text */}
                {emailText && (
                  <div className="mb-3">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-sm font-medium text-gray-700">📧 Текст листа</p>
                    </div>
                    <pre className="bg-gray-50 rounded-lg p-3 text-xs overflow-x-auto whitespace-pre-wrap border border-gray-200 max-h-48 overflow-y-auto">
                      {emailText}
                    </pre>
                  </div>
                )}

                {/* Contact card */}
                {contactText && (
                  <div>
                    <p className="text-sm font-medium text-gray-700 mb-2">📇 Контактна картка</p>
                    <pre className="bg-gray-50 rounded-lg p-3 text-xs overflow-x-auto whitespace-pre-wrap border border-gray-200 max-h-32 overflow-y-auto">
                      {contactText}
                    </pre>
                  </div>
                )}

                {!proposalUrl && !pptxUrl && !emailText && !contactText && (
                  <p className="text-sm text-gray-400 italic">Документи ще не згенеровані</p>
                )}
              </CollapsibleSection>

              {/* ── Section 5: Actions ── */}
              <div className="flex items-center gap-3 pt-2 border-t border-gray-200 flex-wrap">
                {selected.email && !selected.outreach_status?.startsWith("sent:") && selected.outreach_status !== "email_sent" && (
                  <button onClick={handleSendEmail} disabled={sending}
                    className="inline-flex items-center gap-1.5 px-4 py-2 bg-mtp-blue text-white text-sm rounded-lg hover:bg-blue-800 transition font-medium disabled:opacity-50">
                    {sending ? "Відправляю..." : "📧 Відправити email"}
                  </button>
                )}
                {emailText && (
                  <button onClick={handleCopyEmail}
                    className={`inline-flex items-center gap-1.5 px-4 py-2 text-sm rounded-lg transition font-medium ${
                      copied
                        ? "bg-green-100 text-green-700 border border-green-300"
                        : "bg-orange-50 text-orange-700 border border-orange-300 hover:bg-orange-100"
                    }`}>
                    {copied ? "✅ Скопійовано!" : "📋 Копіювати email текст"}
                  </button>
                )}
                {selected.outreach_status !== "email_sent" && !selected.outreach_status?.startsWith("sent:") && selected.email && (
                  <button onClick={handleMarkSent} disabled={updatingStatus}
                    className="inline-flex items-center gap-1.5 px-4 py-2 bg-green-50 text-green-700 border border-green-300 text-sm rounded-lg hover:bg-green-100 transition font-medium disabled:opacity-50">
                    {updatingStatus ? "..." : "✅ Позначити як відправлено"}
                  </button>
                )}
                <button onClick={close}
                  className="ml-auto inline-flex items-center gap-1.5 px-4 py-2 bg-gray-100 text-gray-600 text-sm rounded-lg hover:bg-gray-200 transition font-medium">
                  Закрити
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
