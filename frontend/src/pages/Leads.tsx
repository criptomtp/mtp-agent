import { useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";
import LeadTable from "../components/LeadTable";

export default function Leads() {
  const [leads, setLeads] = useState<any[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState<any | null>(null);
  const [files, setFiles] = useState<any[]>([]);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api
      .getLeads({ status: statusFilter || undefined })
      .then(setLeads)
      .catch(() => {});
  }, [statusFilter]);

  const handleSelect = useCallback(async (lead: any) => {
    // Fetch full lead with files
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

  const pdfFile = files.find((f: any) => f.file_type === "pdf");
  const emailFile = files.find((f: any) => f.file_type === "email");
  const pdfUrl = pdfFile?.file_url;
  const emailText = emailFile?.content_text || "";

  const handleCopyEmail = useCallback(async () => {
    if (!emailText) return;
    try {
      await navigator.clipboard.writeText(emailText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
      const ta = document.createElement("textarea");
      ta.value = emailText;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [emailText]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-mtp-blue">Leads</h2>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-mtp-blue/30"
        >
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

      {selected && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl p-6 m-4 max-h-[85vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-lg font-bold text-mtp-blue">{selected.name}</h3>
              <button
                onClick={() => { setSelected(null); setFiles([]); }}
                className="text-gray-400 hover:text-gray-600 text-xl leading-none"
              >
                &times;
              </button>
            </div>

            {/* MTP Score */}
            {(() => {
              const score = selected.score ?? selected.analysis_json?.score ?? 0;
              const grade = selected.score_grade ?? selected.analysis_json?.grade ?? "D";
              const label = selected.analysis_json?.score_label ?? "";
              const reasons: string[] = selected.analysis_json?.score_reasons ?? [];
              const scoreColor = score >= 8 ? "bg-green-100 text-green-800 border-green-300"
                : score >= 6 ? "bg-yellow-100 text-yellow-800 border-yellow-300"
                : score >= 4 ? "bg-orange-100 text-orange-800 border-orange-300"
                : "bg-gray-100 text-gray-600 border-gray-300";
              return (
                <div className="bg-white rounded-lg p-4 mb-4 border border-gray-200">
                  <div className="flex items-center gap-3 mb-2">
                    <h4 className="text-sm font-semibold text-gray-700">Оцінка MTP:</h4>
                    <span className={`px-2.5 py-0.5 rounded-full text-sm font-bold border ${scoreColor}`}>
                      {score}/10
                    </span>
                    <span className="text-sm font-medium text-gray-600">{grade}</span>
                    {label && <span className="text-sm text-gray-500">{label}</span>}
                  </div>
                  {reasons.length > 0 && (
                    <ul className="text-xs text-gray-500 space-y-0.5 ml-1">
                      {reasons.map((r: string, i: number) => (
                        <li key={i}>- {r}</li>
                      ))}
                    </ul>
                  )}
                </div>
              );
            })()}

            {/* Contact Card */}
            <div className="bg-gray-50 rounded-lg p-4 mb-4 border border-gray-200">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Company Contacts</h4>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-gray-500">Name:</span>{" "}
                  <span className="font-medium">{selected.name}</span>
                </div>
                <div>
                  <span className="text-gray-500">City:</span>{" "}
                  <span className="font-medium">{selected.city || "-"}</span>
                </div>
                <div>
                  <span className="text-gray-500">Email:</span>{" "}
                  {selected.email ? (
                    <a href={`mailto:${selected.email}`} className="text-blue-600 hover:underline">
                      {selected.email}
                    </a>
                  ) : "-"}
                </div>
                <div>
                  <span className="text-gray-500">Phone:</span>{" "}
                  {selected.phone ? (
                    <a href={`tel:${selected.phone}`} className="text-blue-600 hover:underline">
                      {selected.phone}
                    </a>
                  ) : "-"}
                </div>
                <div className="col-span-2">
                  <span className="text-gray-500">Website:</span>{" "}
                  {selected.website ? (
                    <a href={selected.website} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                      {selected.website}
                    </a>
                  ) : "-"}
                </div>
              </div>
            </div>

            {/* Status & Source */}
            <div className="flex gap-4 mb-4 text-sm">
              <div>
                <span className="text-gray-500">Status:</span>{" "}
                <span className="font-medium">{selected.status}</span>
              </div>
              <div>
                <span className="text-gray-500">Source:</span>{" "}
                <span className="font-medium">{selected.source || "-"}</span>
              </div>
              {selected.outreach_status && (
                <div>
                  <span className="text-gray-500">Outreach:</span>{" "}
                  <span className="font-medium">{selected.outreach_status}</span>
                </div>
              )}
            </div>

            {/* PDF & Outreach Actions */}
            {(pdfUrl || emailText) && (
              <div className="flex gap-3 mb-4">
                {pdfUrl && (
                  <>
                    <a
                      href={pdfUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-mtp-blue text-white text-sm rounded hover:bg-blue-800 transition"
                    >
                      View PDF
                    </a>
                    <a
                      href={pdfUrl}
                      download
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-mtp-blue text-mtp-blue text-sm rounded hover:bg-blue-50 transition"
                    >
                      Download PDF
                    </a>
                  </>
                )}
                {emailText && (
                  <button
                    onClick={handleCopyEmail}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded transition ${
                      copied
                        ? "bg-green-100 text-green-700 border border-green-300"
                        : "bg-orange-50 text-orange-700 border border-orange-300 hover:bg-orange-100"
                    }`}
                  >
                    {copied ? "Copied!" : "Copy Email Text"}
                  </button>
                )}
              </div>
            )}

            {/* Email Preview */}
            {emailText && (
              <div className="mb-4">
                <h4 className="text-sm font-semibold text-gray-700 mb-1">Email Text</h4>
                <pre className="bg-gray-50 rounded p-3 text-xs overflow-x-auto whitespace-pre-wrap border border-gray-200 max-h-48">
                  {emailText}
                </pre>
              </div>
            )}

            {/* Analysis JSON */}
            {selected.analysis_json && Object.keys(selected.analysis_json).length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-1">Analysis</h4>
                <pre className="bg-gray-50 rounded p-3 text-xs overflow-x-auto border border-gray-200">
                  {JSON.stringify(selected.analysis_json, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
