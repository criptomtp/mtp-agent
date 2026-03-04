import { useEffect, useState } from "react";
import { api } from "../lib/api";

export default function Runs() {
  const [runs, setRuns] = useState<any[]>([]);
  const [selected, setSelected] = useState<any | null>(null);

  useEffect(() => {
    api.getRuns().then(setRuns).catch(() => {});
  }, []);

  const viewRun = async (id: string) => {
    const data = await api.getRun(id);
    setSelected(data);
  };

  const statusColors: Record<string, string> = {
    running: "bg-yellow-100 text-yellow-800",
    completed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-mtp-blue mb-6">Runs</h2>

      <div className="bg-white rounded-lg shadow">
        {runs.length === 0 ? (
          <p className="text-gray-400 text-center py-8">No runs yet</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-gray-500">
                <th className="p-3 font-medium">Niche</th>
                <th className="p-3 font-medium">Leads</th>
                <th className="p-3 font-medium">Status</th>
                <th className="p-3 font-medium">Started</th>
                <th className="p-3 font-medium">Finished</th>
                <th className="p-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id} className="border-b hover:bg-gray-50">
                  <td className="p-3 font-medium">{run.niche}</td>
                  <td className="p-3">{run.leads_count}</td>
                  <td className="p-3">
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs ${
                        statusColors[run.status] || "bg-gray-100"
                      }`}
                    >
                      {run.status}
                    </span>
                  </td>
                  <td className="p-3 text-gray-500">
                    {new Date(run.started_at).toLocaleString()}
                  </td>
                  <td className="p-3 text-gray-500">
                    {run.finished_at
                      ? new Date(run.finished_at).toLocaleString()
                      : "-"}
                  </td>
                  <td className="p-3 space-x-2">
                    <button
                      onClick={() => viewRun(run.id)}
                      className="text-mtp-blue hover:underline text-xs"
                    >
                      View
                    </button>
                    <a
                      href={`/api/runs/${run.id}/csv`}
                      className="text-mtp-orange hover:underline text-xs"
                    >
                      CSV
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {selected && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl p-6 m-4 max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-lg font-bold text-mtp-blue">
                Run: {selected.niche}
              </h3>
              <button
                onClick={() => setSelected(null)}
                className="text-gray-400 hover:text-gray-600 text-xl leading-none"
              >
                &times;
              </button>
            </div>
            <p className="text-sm text-gray-500 mb-4">
              {selected.leads_count} leads &middot; {selected.status}
            </p>
            {selected.leads?.length > 0 && (
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b text-left text-gray-500">
                    <th className="pb-2">Name</th>
                    <th className="pb-2">Email</th>
                    <th className="pb-2">City</th>
                    <th className="pb-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {selected.leads.map((lead: any) => (
                    <tr key={lead.id} className="border-b">
                      <td className="py-1.5">{lead.name}</td>
                      <td className="py-1.5 text-gray-500">{lead.email || "-"}</td>
                      <td className="py-1.5 text-gray-500">{lead.city || "-"}</td>
                      <td className="py-1.5">{lead.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
