import { useEffect, useState } from "react";
import { api } from "../lib/api";
import StatCard from "../components/StatCard";
import RunLog from "../components/RunLog";

export default function Dashboard() {
  const [stats, setStats] = useState({ total_runs: 0, total_leads: 0, active_runs: 0 });
  const [niche, setNiche] = useState("cosmetics");
  const [count, setCount] = useState(5);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    api.getStats().then(setStats).catch(() => {});
  }, []);

  const handleRun = async () => {
    setRunning(true);
    try {
      await api.runAgents(niche, count);
    } catch (err) {
      console.error(err);
    }
  };

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
      </div>

      <div>
        <h3 className="font-semibold text-gray-800 mb-3">Live Logs</h3>
        <RunLog />
      </div>
    </div>
  );
}
