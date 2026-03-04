import { useEffect, useState } from "react";
import { api } from "../lib/api";
import LeadTable from "../components/LeadTable";

export default function Leads() {
  const [leads, setLeads] = useState<any[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState<any | null>(null);

  useEffect(() => {
    api
      .getLeads({ status: statusFilter || undefined })
      .then(setLeads)
      .catch(() => {});
  }, [statusFilter]);

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
        <LeadTable leads={leads} onSelect={setSelected} />
      </div>

      {selected && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6 m-4 max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-lg font-bold text-mtp-blue">{selected.name}</h3>
              <button
                onClick={() => setSelected(null)}
                className="text-gray-400 hover:text-gray-600 text-xl leading-none"
              >
                &times;
              </button>
            </div>
            <div className="space-y-2 text-sm">
              <p><span className="text-gray-500">Email:</span> {selected.email || "-"}</p>
              <p><span className="text-gray-500">Phone:</span> {selected.phone || "-"}</p>
              <p><span className="text-gray-500">City:</span> {selected.city || "-"}</p>
              <p><span className="text-gray-500">Website:</span> {selected.website || "-"}</p>
              <p><span className="text-gray-500">Source:</span> {selected.source || "-"}</p>
              <p><span className="text-gray-500">Status:</span> {selected.status}</p>
              {selected.analysis_json && Object.keys(selected.analysis_json).length > 0 && (
                <div>
                  <p className="text-gray-500 mb-1">Analysis:</p>
                  <pre className="bg-gray-50 rounded p-3 text-xs overflow-x-auto">
                    {JSON.stringify(selected.analysis_json, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
