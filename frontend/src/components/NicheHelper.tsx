import { useState } from "react";

interface NicheHelperProps {
  onSelect: (query: string) => void;
}

export default function NicheHelper({ onSelect }: NicheHelperProps) {
  const [business, setBusiness] = useState("");
  const [keywords, setKeywords] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    if (!business.trim()) return;
    setLoading(true);
    try {
      const r = await fetch(
        (import.meta.env.VITE_API_URL || "") + "/api/settings/suggest-niches",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ business }),
        }
      );
      const data = await r.json();
      setKeywords(data.keywords || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-5 mb-6">
      <h3 className="font-semibold text-gray-800 mb-1">AI-підбір ніш</h3>
      <p className="text-xs text-gray-500 mb-3">
        Опишіть свій бізнес — AI підбере ключові слова для пошуку клієнтів
      </p>
      <div className="flex gap-2 mb-3">
        <input
          value={business}
          onChange={(e) => setBusiness(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && generate()}
          placeholder="Наприклад: фулфілмент для e-commerce, юридичні послуги для IT..."
          className="flex-1 border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-mtp-blue/30"
        />
        <button
          onClick={generate}
          disabled={loading || !business.trim()}
          className="px-4 py-1.5 bg-mtp-blue text-white rounded text-sm font-medium hover:bg-mtp-blue/90 disabled:opacity-50 whitespace-nowrap"
        >
          {loading ? "..." : "Підібрати"}
        </button>
      </div>
      {keywords.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 mb-2">
            Клікніть щоб додати в поле пошуку:
          </p>
          <div className="flex flex-wrap gap-2">
            {keywords.map((kw) => (
              <button
                key={kw}
                onClick={() => onSelect(kw)}
                className="px-3 py-1 text-xs bg-mtp-blue/10 text-mtp-blue rounded-full hover:bg-mtp-blue/20 transition-colors"
              >
                + {kw}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
