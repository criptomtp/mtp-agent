import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import StatCard from "../components/StatCard";
import RunLog, { type AgentMap } from "../components/RunLog";
import AgentCards from "../components/AgentCards";

const INITIAL_AGENTS: AgentMap = {
  1: { name: "Research", status: "waiting", detail: "" },
  2: { name: "Analysis", status: "waiting", detail: "" },
  3: { name: "Content", status: "waiting", detail: "" },
  4: { name: "Outreach", status: "waiting", detail: "" },
};

export default function Dashboard() {
  const [stats, setStats] = useState({ total_runs: 0, total_leads: 0, active_runs: 0 });
  const [niche, setNiche] = useState("cosmetics");
  const [count, setCount] = useState(5);
  const [running, setRunning] = useState(false);
  const [agents, setAgents] = useState<AgentMap>(INITIAL_AGENTS);
  const [savedNiches, setSavedNiches] = useState<{ id: string; name: string; icon: string; search_queries: string[] }[]>([]);

  useEffect(() => {
    api.getStats().then(setStats).catch(() => {});
    // Load saved niches from user settings
    api.getUserSettings().then(async (us) => {
      if (us?.selected_niches?.length && us?.business_type_id) {
        try {
          const bts = await api.getBusinessTypes();
          const bt = bts.find((b: any) => b.id === us.business_type_id);
          if (bt) {
            const allNiches = await api.getNiches(bt.slug);
            const selected = allNiches.filter((n: any) =>
              us.selected_niches.includes(n.id)
            );
            setSavedNiches(selected.map((n: any) => ({ id: n.id, name: n.name, icon: n.icon, search_queries: n.search_queries || [] })));
          }
        } catch { /* ignore */ }
      }
    }).catch(() => {});
  }, []);

  const handleRun = async () => {
    setRunning(true);
    setAgents(INITIAL_AGENTS);
    try {
      await api.runAgents(niche, count);
    } catch (err) {
      console.error(err);
    }
  };

  const handleAgentUpdate = useCallback((updated: AgentMap) => {
    setAgents(updated);
  }, []);

  return (
    <div>
      <h2 className="text-2xl font-bold text-mtp-blue mb-6">Dashboard</h2>

      <div className="grid grid-cols-3 gap-4 mb-8">
        <StatCard title="Total Runs" value={stats.total_runs} />
        <StatCard title="Total Leads" value={stats.total_leads} />
        <StatCard
          title="Active Runs"
          value={stats.active_runs}
          subtitle={stats.active_runs > 0 ? "Pipeline running" : "Idle"}
        />
      </div>

      <div className="bg-white rounded-lg shadow p-5 mb-6">
        <h3 className="font-semibold text-gray-800 mb-4">Run Agents</h3>
        <div className="flex gap-3 items-end">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Niche</label>
            <input
              value={niche}
              onChange={(e) => setNiche(e.target.value)}
              className="border rounded px-3 py-1.5 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-mtp-blue/30"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Lead Count</label>
            <input
              type="number"
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              min={1}
              max={50}
              className="border rounded px-3 py-1.5 text-sm w-20 focus:outline-none focus:ring-2 focus:ring-mtp-blue/30"
            />
          </div>
          <button
            onClick={handleRun}
            disabled={running}
            className="px-5 py-1.5 bg-mtp-orange text-white rounded font-medium text-sm hover:bg-mtp-orange/90 disabled:opacity-50"
          >
            {running ? "Running..." : "Start Pipeline"}
          </button>
        </div>
        {savedNiches.length > 0 && (
          <div className="mt-3">
            <span className="text-xs text-gray-500 mr-2">Збережені ніші:</span>
            <div className="inline-flex flex-wrap gap-1.5">
              {savedNiches.map((n) => {
                const query = n.search_queries[0] || n.name;
                return (
                  <button
                    key={n.id}
                    onClick={() => setNiche(query)}
                    className={`px-2.5 py-1 rounded-full text-xs border transition-colors ${
                      niche === query
                        ? "bg-mtp-blue text-white border-mtp-blue"
                        : "bg-gray-50 text-gray-700 border-gray-200 hover:border-mtp-blue"
                    }`}
                  >
                    {n.icon} {n.name}
                  </button>
                );
              })}
              <button
                onClick={async () => {
                  setRunning(true);
                  setAgents(INITIAL_AGENTS);
                  for (const n of savedNiches) {
                    const query = n.search_queries[0] || n.name;
                    setNiche(query);
                    try {
                      await api.runAgents(query, count);
                    } catch (err) {
                      console.error(err);
                    }
                  }
                }}
                disabled={running}
                className="px-2.5 py-1 rounded-full text-xs border border-mtp-orange/30 bg-mtp-orange/10 text-mtp-orange hover:bg-mtp-orange/20 transition-colors font-medium disabled:opacity-50"
              >
                Всі ніші
              </button>
            </div>
          </div>
        )}
      </div>

      <AgentCards agents={agents} />

      <div>
        <h3 className="font-semibold text-gray-800 mb-3">Live Logs</h3>
        <RunLog onAgentUpdate={handleAgentUpdate} />
      </div>
    </div>
  );
}
