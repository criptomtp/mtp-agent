import { useState } from "react";

interface NicheHelperProps {
  onSelect: (query: string) => void;
  onSelectMultiple: (queries: string[]) => void;
}

export default function NicheHelper({ onSelect, onSelectMultiple }: NicheHelperProps) {
  const [business, setBusiness] = useState("");
  const [keywords, setKeywords] = useState<string[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [isFallback, setIsFallback] = useState(false);

  const generate = async (append = false) => {
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
      const newKw: string[] = data.keywords || [];
      setIsFallback(!!data.fallback);
      if (append) {
        setKeywords((prev) => {
          const existing = new Set(prev);
          const unique = newKw.filter((k) => !existing.has(k));
          return [...prev, ...unique];
        });
      } else {
        setKeywords(newKw);
        setSelected(new Set());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const toggleSelect = (kw: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(kw)) next.delete(kw);
      else next.add(kw);
      return next;
    });
  };

  const selectAll = () => {
    if (selected.size === keywords.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(keywords));
    }
  };

  const addSelected = () => {
    if (selected.size > 0) {
      onSelectMultiple(Array.from(selected));
      setSelected(new Set());
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-5 mb-6">
      <h3 className="font-semibold text-gray-800 mb-1">Пошук цільових клієнтів</h3>
      <p className="text-xs text-gray-500 mb-3">
        Опишіть свій бізнес — AI визначить хто ваші потенційні клієнти
      </p>
      <div className="flex gap-2 mb-3">
        <input
          value={business}
          onChange={(e) => setBusiness(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && generate()}
          placeholder="Наприклад: фулфілмент, юридичні послуги, підбір персоналу..."
          className="flex-1 border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-mtp-blue/30"
        />
        <button
          onClick={() => generate(false)}
          disabled={loading || !business.trim()}
          className="px-4 py-1.5 bg-mtp-blue text-white rounded text-sm font-medium hover:bg-mtp-blue/90 disabled:opacity-50 whitespace-nowrap"
        >
          {loading ? "..." : "Знайти клієнтів"}
        </button>
      </div>
      {keywords.length > 0 && (
        <div>
          <div className="flex items-center gap-3 mb-2">
            <p className="text-xs text-gray-500">
              Оберіть запити для пошуку:
            </p>
            <button
              onClick={selectAll}
              className="text-xs text-mtp-blue hover:underline"
            >
              {selected.size === keywords.length ? "Зняти всі" : "Обрати всі"}
            </button>
            {selected.size > 0 && (
              <button
                onClick={addSelected}
                className="text-xs px-3 py-0.5 bg-mtp-orange text-white rounded-full font-medium hover:bg-mtp-orange/90"
              >
                Додати обрані ({selected.size})
              </button>
            )}
            <button
              onClick={() => generate(true)}
              disabled={loading}
              className="text-xs text-mtp-blue hover:underline disabled:opacity-50 ml-auto"
            >
              {loading ? "..." : "+ Ще"}
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {keywords.map((kw) => (
              <button
                key={kw}
                onClick={() => toggleSelect(kw)}
                className={`px-3 py-1 text-xs rounded-full transition-colors ${
                  selected.has(kw)
                    ? "bg-mtp-blue text-white"
                    : "bg-mtp-blue/10 text-mtp-blue hover:bg-mtp-blue/20"
                }`}
              >
                {kw}
              </button>
            ))}
          </div>
          {isFallback && (
            <p className="text-xs text-gray-400 mt-1">* базові запити (AI тимчасово недоступний)</p>
          )}
        </div>
      )}
    </div>
  );
}
