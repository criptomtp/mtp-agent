import type { AgentMap } from "./RunLog";

const AGENT_META: Record<number, { icon: string; label: string }> = {
  1: { icon: "🔍", label: "Пошук лідів" },
  2: { icon: "🧠", label: "Аналіз Gemini" },
  3: { icon: "✍️", label: "Генерація КП" },
  4: { icon: "📧", label: "Розсилка" },
};

const STATUS_STYLES: Record<string, { bg: string; text: string; border: string; dot: string }> = {
  waiting: { bg: "bg-gray-50", text: "text-gray-400", border: "border-gray-200", dot: "bg-gray-300" },
  running: { bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-300", dot: "bg-blue-500 animate-pulse" },
  done: { bg: "bg-green-50", text: "text-green-700", border: "border-green-300", dot: "bg-green-500" },
  error: { bg: "bg-red-50", text: "text-red-700", border: "border-red-300", dot: "bg-red-500" },
};

interface AgentCardsProps {
  agents: AgentMap;
}

export default function AgentCards({ agents }: AgentCardsProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
      {[1, 2, 3, 4].map((id) => {
        const agent = agents[id];
        const meta = AGENT_META[id];
        const style = STATUS_STYLES[agent?.status || "waiting"];

        return (
          <div
            key={id}
            className={`rounded-lg border p-3 ${style.bg} ${style.border} transition-all duration-300`}
          >
            <div className="flex items-center gap-2 mb-1">
              <span className="text-lg">{meta.icon}</span>
              <span className={`font-semibold text-sm ${style.text}`}>{meta.label}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full flex-shrink-0 ${style.dot}`} />
              <span className="text-xs text-gray-500 truncate">
                {agent?.status === "waiting" && "Очікування..."}
                {agent?.status === "running" && (agent.detail || "Працює...")}
                {agent?.status === "done" && (agent.detail || "Готово")}
                {agent?.status === "error" && (agent.detail || "Помилка")}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
