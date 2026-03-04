import { useEffect, useRef, useState } from "react";

export default function RunLog() {
  const [logs, setLogs] = useState<string[]>([]);
  const [connected, setConnected] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

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
        setLogs((prev) => [...prev, data.msg]);
      } catch {
        setLogs((prev) => [...prev, e.data]);
      }
    };

    return () => ws.close();
  }, []);

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
