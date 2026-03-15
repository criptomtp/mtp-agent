import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import StatCard from "../components/StatCard";
import RunLog, { type AgentMap } from "../components/RunLog";
import AgentCards from "../components/AgentCards";
import NicheHelper from "../components/NicheHelper";

const INITIAL_AGENTS: AgentMap = {
  1: { name: "Research", status: "waiting", detail: "" },
  2: { name: "Analysis", status: "waiting", detail: "" },
  3: { name: "Content", status: "waiting", detail: "" },
  4: { name: "Outreach", status: "waiting", detail: "" },
};

export default function Dashboard() {
  const [stats, setStats] = useState({ total_runs: 0, total_leads: 0, active_runs: 0 });
  const [niches, setNiches] = useState("");
  const [count, setCount] = useState(5);
  const [running, setRunning] = useState(false);
  const [agents, setAgents] = useState<AgentMap>(INITIAL_AGENTS);

  useEffect(() => {
    api.getStats().then(setStats).catch(() => {});
  }, []);

  const handleRun = async () => {
    const queries = niches.split("\n").map((q) => q.trim()).filter(Boolean);
    if (queries.length === 0) return;
    setRunning(true);
    setAgents(INITIAL_AGENTS);
    for (const query of queries) {
      try {
        await api.runAgents(query, count);
      } catch (err) {
        console.error(err);
      }
    }
    setRunning(false);
  };

  const handleAddNiche = (kw: string) => {
    setNiches((prev) => (prev ? prev + "\n" + kw : kw));
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

      <NicheHelper onSelect={handleAddNiche} />

      <div className="bg-white rounded-lg shadow p-5 mb-6">
        <h3 className="font-semibold text-gray-800 mb-4">Run Agents</h3>
        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <label className="block text-xs text-gray-500 mb-1">
              Ніші (один запит на рядок)
            </label>
            <textarea
              value={niches}
              onChange={(e) => setNiches(e.target.value)}
              placeholder={"косметика інтернет-магазин\nіграшки дитячі\nодяг Ukraine"}
              rows={3}
              className="w-full border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-mtp-blue/30 resize-none"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Лідів</label>
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
            disabled={running || !niches.trim()}
            className="px-5 py-1.5 bg-mtp-orange text-white rounded font-medium text-sm hover:bg-mtp-orange/90 disabled:opacity-50"
          >
            {running ? "Running..." : "Start Pipeline"}
          </button>
        </div>
      </div>

      <AgentCards agents={agents} />

      <div>
        <h3 className="font-semibold text-gray-800 mb-3">Live Logs</h3>
        <RunLog onAgentUpdate={handleAgentUpdate} />
      </div>
    </div>
  );
}
