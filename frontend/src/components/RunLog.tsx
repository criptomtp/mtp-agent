import { useEffect, useRef, useState } from "react";

interface AgentStatus {
  name: string;
  status: "waiting" | "running" | "done" | "error";
  detail: string;
}

export type AgentMap = Record<number, AgentStatus>;

interface RunLogProps {
  onAgentUpdate?: (agents: AgentMap) => void;
}

export default function RunLog({ onAgentUpdate }: RunLogProps) {
  const [logs, setLogs] = useState<string[]>([]);
  const [connected, setConnected] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const agentsRef = useRef<AgentMap>({
    1: { name: "Research", status: "waiting", detail: "" },
    2: { name: "Analysis", status: "waiting", detail: "" },
    3: { name: "Content", status: "waiting", detail: "" },
    4: { name: "Outreach", status: "waiting", detail: "" },
  });

  useEffect(() => {
    const wsUrl =
      (import.meta.env.VITE_API_URL || window.location.origin)
        .replace("http", "ws") + "/ws/logs";

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.type === "agent_progress") {
          const current = agentsRef.current[data.agent];
          // Don't downgrade from "done" back to "running"
          const keepStatus =
            current?.status === "done" && data.status === "running"
              ? "done"
              : data.status;
          agentsRef.current = {
            ...agentsRef.current,
            [data.agent]: {
              name: data.name,
              status: keepStatus,
              detail:
                keepStatus === "done" && current?.status === "done"
                  ? current.detail
                  : (data.detail || ""),
            },
          };
          onAgentUpdate?.({ ...agentsRef.current });
        }
        if (data.msg) {
          setLogs((prev) => [...prev, data.msg]);
          // Set all agents to done when pipeline completes
          if (data.msg.includes("Pipeline completed")) {
            agentsRef.current = Object.fromEntries(
              Object.entries(agentsRef.current).map(([k, v]) => [
                k,
                { ...v, status: "done" as const },
              ])
            ) as AgentMap;
            onAgentUpdate?.({ ...agentsRef.current });
          }
        }
      } catch {
        setLogs((prev) => [...prev, e.data]);
      }
    };

    return () => ws.close();
  }, [onAgentUpdate]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <div className="bg-gray-900 rounded-lg p-4 h-64 overflow-y-auto font-mono text-xs">
      <div className="flex items-center gap-2 mb-2">
        <span
          className={`w-2 h-2 rounded-full ${connected ? "bg-green-400" : "bg-red-400"}`}
        />
        <span className="text-gray-400">
          {connected ? "Connected" : "Disconnected"}
        </span>
      </div>
      {logs.length === 0 && (
        <p className="text-gray-500">Waiting for pipeline logs...</p>
      )}
      {logs.map((line, i) => (
        <div key={i} className="text-green-400 leading-relaxed">
          {line}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
