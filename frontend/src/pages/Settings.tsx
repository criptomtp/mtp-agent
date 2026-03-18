import { useEffect, useState } from "react";
import { api } from "../lib/api";

const TABS = ["Pipeline", "Бізнес", "Промпти", "Виключення", "Тест Ліда"] as const;
type Tab = (typeof TABS)[number];

const AGENT_INFO: Record<string, { label: string; desc: string; hasModel: boolean }> = {
  research: { label: "Research Agent", desc: "Пошук лідів через Google Maps, Prom.ua", hasModel: false },
  analysis: { label: "Analysis Agent", desc: "AI аналіз компанії та генерація пропозиції", hasModel: true },
  content: { label: "Content Agent", desc: "Генерація PDF та email", hasModel: true },
  outreach: { label: "Outreach Agent", desc: "Відправка email та контакт", hasModel: false },
};

export default function Settings() {
  const [tab, setTab] = useState<Tab>("Pipeline");
  const [settings, setSettings] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.getPipelineSettings().then(setSettings).catch(console.error);
  }, []);

  if (!settings) {
    return <div className="text-gray-500">Завантаження...</div>;
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-mtp-blue mb-6">Settings</h2>

      {/* Tabs */}
      <div className="flex space-x-1 mb-6 bg-gray-100 rounded-lg p-1 max-w-md">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              tab === t
                ? "bg-white text-mtp-blue shadow"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "Pipeline" && (
        <PipelineTab
          settings={settings}
          setSettings={setSettings}
          saving={saving}
          setSaving={setSaving}
          saved={saved}
          setSaved={setSaved}
        />
      )}
      {tab === "Бізнес" && <BusinessTab />}
      {tab === "Промпти" && (
        <PromptsTab
          settings={settings}
          setSettings={setSettings}
          saving={saving}
          setSaving={setSaving}
          saved={saved}
          setSaved={setSaved}
        />
      )}
      {tab === "Виключення" && <ExclusionsTab />}
      {tab === "Тест Ліда" && <TestLeadTab />}
    </div>
  );
}

/* ─── Tab 1: Pipeline ─── */

function PipelineTab({
  settings,
  setSettings,
  saving,
  setSaving,
  saved,
  setSaved,
}: any) {
  const agents = settings.agents || {};
  const models: string[] = settings.available_models || [];

  const toggleAgent = (key: string) => {
    const updated = {
      ...settings,
      agents: {
        ...agents,
        [key]: { ...agents[key], enabled: !agents[key]?.enabled },
      },
    };
    setSettings(updated);
  };

  const setModel = (key: string, model: string) => {
    const updated = {
      ...settings,
      agents: {
        ...agents,
        [key]: { ...agents[key], model },
      },
    };
    setSettings(updated);
  };

  const save = async () => {
    setSaving(true);
    setSaved(false);
    try {
      const res = await api.savePipelineSettings({ agents: settings.agents });
      setSettings(res);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      console.error(e);
    }
    setSaving(false);
  };

  return (
    <div>
      <h3 className="text-lg font-semibold text-gray-800 mb-4">Конфігурація Pipeline</h3>
      <div className="space-y-4 max-w-2xl">
        {Object.entries(AGENT_INFO).map(([key, info]) => {
          const agent = agents[key] || {};
          return (
            <div
              key={key}
              className="bg-white rounded-lg shadow p-5 flex items-start justify-between"
            >
              <div className="flex-1">
                <div className="flex items-center space-x-3">
                  <button
                    onClick={() => toggleAgent(key)}
                    className={`w-11 h-6 rounded-full transition-colors relative ${
                      agent.enabled ? "bg-green-500" : "bg-gray-300"
                    }`}
                  >
                    <span
                      className={`block w-5 h-5 bg-white rounded-full shadow absolute top-0.5 transition-transform ${
                        agent.enabled ? "translate-x-5" : "translate-x-0.5"
                      }`}
                    />
                  </button>
                  <span className="font-medium text-gray-800">{info.label}</span>
                </div>
                <p className="text-sm text-gray-500 mt-1 ml-14">{info.desc}</p>
              </div>
              {info.hasModel && (
                <select
                  value={agent.model || models[0]}
                  onChange={(e) => setModel(key, e.target.value)}
                  className="ml-4 border border-gray-300 rounded-md px-3 py-1.5 text-sm bg-white"
                >
                  {models.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              )}
            </div>
          );
        })}
      </div>
      <button
        onClick={save}
        disabled={saving}
        className="mt-6 px-6 py-2 bg-mtp-blue text-white rounded-md hover:bg-blue-800 disabled:opacity-50"
      >
        {saving ? "Зберігаю..." : saved ? "Збережено!" : "Зберегти"}
      </button>

      <CalendlySection />
    </div>
  );
}

/* ─── Calendly Section (Pipeline tab) ─── */

function CalendlySection() {
  const [calendlyUrl, setCalendlyUrl] = useState("");
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getUserSettings().then((us) => {
      setCalendlyUrl(us?.calendly_url || "https://calendly.com/mtpgrouppromo/30min");
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    await api.saveUserSettings({ calendly_url: calendlyUrl });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  if (loading) return null;

  return (
    <div className="mt-8 max-w-2xl">
      <div className="bg-white rounded-lg shadow p-5 mb-4">
        <h3 className="font-semibold text-gray-800 mb-1">Calendly — запис на зустріч</h3>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4 text-xs text-blue-800">
          <p className="font-semibold mb-1">Як знайти своє посилання Calendly:</p>
          <ol className="list-decimal ml-4 space-y-1">
            <li>Зайди на <a href="https://calendly.com" target="_blank" rel="noopener noreferrer" className="underline">calendly.com</a> і увійди в акаунт</li>
            <li>Натисни на будь-який тип зустрічі (наприклад "30 хвилин")</li>
            <li>Скопіюй посилання з адресного рядка браузера</li>
            <li>Або зайди в <strong>Event Types → Share →</strong> скопіюй посилання</li>
          </ol>
          <p className="mt-2">Посилання виглядає так: <code className="bg-blue-100 px-1 rounded">calendly.com/ваш-акаунт/30min</code></p>
        </div>

        <label className="block text-xs text-gray-500 mb-1">Ваше посилання Calendly</label>
        <input
          value={calendlyUrl}
          onChange={(e) => setCalendlyUrl(e.target.value)}
          placeholder="https://calendly.com/ваш-акаунт/30min"
          className="border rounded px-3 py-1.5 text-sm w-full focus:outline-none focus:ring-2 focus:ring-mtp-blue/30"
        />
        <button
          onClick={handleSave}
          className="mt-3 px-5 py-1.5 bg-mtp-blue text-white text-sm rounded hover:bg-blue-800"
        >
          {saved ? "Збережено!" : "Зберегти"}
        </button>
      </div>
    </div>
  );
}

/* ─── Tab 2: Промпти ─── */

function PromptsTab({
  settings,
  setSettings,
  saving,
  setSaving,
  saved,
  setSaved,
}: any) {
  const [which, setWhich] = useState<"analysis_system" | "analysis_user_template">(
    "analysis_system"
  );
  const prompts = settings.prompts || {};
  const defaults = settings.default_prompts || {};
  const currentValue = prompts[which] || "";
  const defaultValue = defaults[which] || "";
  const displayValue = currentValue || defaultValue;

  const updatePrompt = (value: string) => {
    setSettings({
      ...settings,
      prompts: { ...prompts, [which]: value },
    });
  };

  const save = async () => {
    setSaving(true);
    setSaved(false);
    try {
      const res = await api.savePipelineSettings({ prompts: settings.prompts });
      setSettings(res);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      console.error(e);
    }
    setSaving(false);
  };

  const reset = async () => {
    try {
      const res = await api.resetPrompts();
      // Reload full settings to get default_prompts
      const full = await api.getPipelineSettings();
      setSettings(full);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="max-w-3xl">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">Редактор промптів</h3>

      <div className="mb-4">
        <select
          value={which}
          onChange={(e) => setWhich(e.target.value as any)}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm bg-white"
        >
          <option value="analysis_system">System Prompt</option>
          <option value="analysis_user_template">User Template</option>
        </select>
      </div>

      <textarea
        value={displayValue}
        onChange={(e) => updatePrompt(e.target.value)}
        rows={20}
        className="w-full border border-gray-300 rounded-lg p-4 text-sm font-mono bg-white focus:border-mtp-blue focus:ring-1 focus:ring-mtp-blue"
      />

      <div className="mt-2 text-xs text-gray-400">
        Доступні змінні:{" "}
        <code className="bg-gray-100 px-1 rounded">{"{{company_name}}"}</code>,{" "}
        <code className="bg-gray-100 px-1 rounded">{"{{city}}"}</code>,{" "}
        <code className="bg-gray-100 px-1 rounded">{"{{website}}"}</code>,{" "}
        <code className="bg-gray-100 px-1 rounded">{"{{description}}"}</code>,{" "}
        <code className="bg-gray-100 px-1 rounded">{"{{products_count}}"}</code>,{" "}
        <code className="bg-gray-100 px-1 rounded">{"{{source}}"}</code>,{" "}
        <code className="bg-gray-100 px-1 rounded">{"{{tariffs}}"}</code>,{" "}
        <code className="bg-gray-100 px-1 rounded">{"{{website_data}}"}</code>
      </div>

      <div className="mt-4 flex space-x-3">
        <button
          onClick={save}
          disabled={saving}
          className="px-6 py-2 bg-mtp-blue text-white rounded-md hover:bg-blue-800 disabled:opacity-50"
        >
          {saving ? "Зберігаю..." : saved ? "Збережено!" : "Зберегти"}
        </button>
        <button
          onClick={reset}
          className="px-6 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
        >
          Скинути до дефолту
        </button>
      </div>
    </div>
  );
}

/* ─── Tab: Бізнес ─── */

interface BusinessType {
  id: string;
  name: string;
  slug: string;
  icon: string;
}
interface UserSettingsData {
  business_type_id: string | null;
  ai_model: string;
  email_tone: string;
  language: string;
}

function BusinessTab() {
  const [businessTypes, setBusinessTypes] = useState<BusinessType[]>([]);
  const [userSettings, setUserSettings] = useState<UserSettingsData>({
    business_type_id: null,
    ai_model: "gemini-2.0-flash",
    email_tone: "friendly",
    language: "uk",
  });
  const [selectedBtSlug, setSelectedBtSlug] = useState("");
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getBusinessTypes(),
      api.getUserSettings(),
    ]).then(([bts, us]) => {
      setBusinessTypes(bts);
      if (us) setUserSettings(us);
      // Load niches for the saved business type
      if (us?.business_type_id && bts.length) {
        const bt = bts.find((b: BusinessType) => b.id === us.business_type_id);
        if (bt) {
          setSelectedBtSlug(bt.slug);
        }
      }
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const handleBusinessTypeSelect = (bt: BusinessType) => {
    setSelectedBtSlug(bt.slug);
    setUserSettings((s) => ({ ...s, business_type_id: bt.id }));
  };

  const handleSave = async () => {
    await api.saveUserSettings(userSettings);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  if (loading) return <div className="text-gray-500">Завантаження...</div>;

  return (
    <div className="max-w-2xl">
      {/* Business Type */}
      <div className="bg-white rounded-lg shadow p-5 mb-4">
        <h3 className="font-semibold text-gray-800 mb-4">Тип бізнесу</h3>
        <div className="grid grid-cols-2 gap-2">
          {businessTypes.map((bt) => (
            <button
              key={bt.id}
              onClick={() => handleBusinessTypeSelect(bt)}
              className={`flex items-center gap-2 p-3 rounded-lg border-2 text-left transition-all ${
                userSettings.business_type_id === bt.id
                  ? "border-mtp-blue bg-mtp-blue/5 font-medium"
                  : "border-gray-200 hover:border-gray-300"
              }`}
            >
              <span className="text-xl">{bt.icon}</span>
              <span className="text-sm">{bt.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* AI Settings */}
      <div className="bg-white rounded-lg shadow p-5 mb-4">
        <h3 className="font-semibold text-gray-800 mb-4">AI Налаштування</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Тон листа</label>
            <select
              value={userSettings.email_tone}
              onChange={(e) =>
                setUserSettings((s) => ({ ...s, email_tone: e.target.value }))
              }
              className="border rounded px-3 py-1.5 text-sm w-full focus:outline-none focus:ring-2 focus:ring-mtp-blue/30"
            >
              <option value="friendly">Дружній</option>
              <option value="formal">Формальний</option>
              <option value="bold">Напористий</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Мова</label>
            <select
              value={userSettings.language}
              onChange={(e) =>
                setUserSettings((s) => ({ ...s, language: e.target.value }))
              }
              className="border rounded px-3 py-1.5 text-sm w-full focus:outline-none focus:ring-2 focus:ring-mtp-blue/30"
            >
              <option value="uk">Українська</option>
              <option value="en">English</option>
            </select>
          </div>
        </div>
      </div>

      <button
        onClick={handleSave}
        className="px-6 py-2 bg-mtp-blue text-white rounded font-medium hover:bg-mtp-blue/90 transition-colors"
      >
        {saved ? "Збережено!" : "Зберегти налаштування"}
      </button>
    </div>
  );
}

/* ─── Tab: Виключення ─── */

function ExclusionsTab() {
  const BASE = import.meta.env.VITE_API_URL || "";
  const [domains, setDomains] = useState<{ id: string; domain: string; reason: string }[]>([]);
  const [newDomain, setNewDomain] = useState("");
  const [loading, setLoading] = useState(true);

  const loadDomains = () => {
    fetch(`${BASE}/api/settings/excluded-domains`)
      .then((r) => r.json())
      .then((data) => {
        setDomains(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    loadDomains();
  }, []);

  const addDomain = async () => {
    if (!newDomain.trim()) return;
    await fetch(`${BASE}/api/settings/excluded-domains`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ domain: newDomain, reason: "client" }),
    });
    setNewDomain("");
    loadDomains();
  };

  const removeDomain = async (domain: string, id: string) => {
    await fetch(`${BASE}/api/settings/excluded-domains/${domain}`, {
      method: "DELETE",
    });
    setDomains((ds) => ds.filter((x) => x.id !== id));
  };

  if (loading) return <div className="text-gray-500">Завантаження...</div>;

  return (
    <div className="max-w-2xl">
      <div className="bg-white rounded-lg shadow p-5">
        <h3 className="font-semibold text-gray-800 mb-1">Виключені домени</h3>
        <p className="text-xs text-gray-500 mb-4">
          Сайти ваших клієнтів або вже оброблених компаній — система їх ігноруватиме при пошуку лідів.
          Домени додаються автоматично після відправки email.
        </p>

        <div className="flex gap-2 mb-4">
          <input
            value={newDomain}
            onChange={(e) => setNewDomain(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addDomain()}
            placeholder="example.com або https://example.com"
            className="flex-1 border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-mtp-blue/30"
          />
          <button
            onClick={addDomain}
            className="px-4 py-1.5 bg-mtp-blue text-white rounded text-sm font-medium hover:bg-mtp-blue/90"
          >
            + Додати
          </button>
        </div>

        <div className="space-y-2">
          {domains.map((d) => (
            <div
              key={d.id}
              className="flex items-center justify-between bg-gray-50 rounded px-3 py-2"
            >
              <div>
                <span className="text-sm font-medium">{d.domain}</span>
                <span className="ml-2 text-xs text-gray-400">
                  {d.reason === "client" ? "клієнт" : d.reason === "contacted" ? "відправлено" : d.reason}
                </span>
              </div>
              <button
                onClick={() => removeDomain(d.domain, d.id)}
                className="text-red-400 hover:text-red-600 text-sm"
              >
                ✕
              </button>
            </div>
          ))}
          {domains.length === 0 && (
            <p className="text-xs text-gray-400 text-center py-4">
              Список порожній
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Tab: Тест Ліда ─── */

function TestLeadTab() {
  const [form, setForm] = useState({
    name: "",
    city: "",
    website: "",
    description: "",
    products_count: 0,
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [savingLead, setSavingLead] = useState(false);
  const [leadSaved, setLeadSaved] = useState(false);

  const run = async () => {
    if (!form.name.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await api.testLead(form);
      setResult(res);
    } catch (e: any) {
      setError(e.message || "Помилка");
    }
    setLoading(false);
  };

  const saveLead = async () => {
    if (!result?.analysis) return;
    setSavingLead(true);
    try {
      const BASE = import.meta.env.VITE_API_URL || "";
      await fetch(`${BASE}/api/leads/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: form.name,
          city: form.city,
          website: form.website,
          email: "",
          phone: "",
          source: "manual_test",
          status: "new",
          analysis_json: result.analysis,
          score: result.analysis.score || 0,
          score_grade: result.analysis.grade || "D",
        }),
      });
      setLeadSaved(true);
      setTimeout(() => setLeadSaved(false), 3000);
    } catch (e) {
      console.error(e);
    }
    setSavingLead(false);
  };

  const a = result?.analysis || {};
  const gradeColors: Record<string, string> = {
    A: "bg-green-100 text-green-800 border-green-300",
    B: "bg-blue-100 text-blue-800 border-blue-300",
    C: "bg-yellow-100 text-yellow-800 border-yellow-300",
    D: "bg-red-100 text-red-800 border-red-300",
  };

  return (
    <div className="max-w-3xl">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">
        Ручний тест без парсингу
      </h3>

      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Назва компанії *
          </label>
          <input
            type="text"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            placeholder="Наприклад: BeautyBox Ukraine"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Місто</label>
            <input
              type="text"
              value={form.city}
              onChange={(e) => setForm({ ...form, city: e.target.value })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              placeholder="Київ"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Сайт</label>
            <input
              type="text"
              value={form.website}
              onChange={(e) => setForm({ ...form, website: e.target.value })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              placeholder="https://example.com"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Опис бізнесу
          </label>
          <textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            rows={3}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            placeholder="Інтернет-магазин корейської косметики..."
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Кількість товарів
          </label>
          <input
            type="number"
            value={form.products_count || ""}
            onChange={(e) =>
              setForm({ ...form, products_count: parseInt(e.target.value) || 0 })
            }
            className="w-48 border border-gray-300 rounded-md px-3 py-2 text-sm"
            placeholder="500"
          />
        </div>

        <button
          onClick={run}
          disabled={loading || !form.name.trim()}
          className="px-6 py-2.5 bg-mtp-orange text-white rounded-md hover:bg-orange-600 disabled:opacity-50 font-medium"
        >
          {loading ? "Аналізую..." : "Запустити аналіз"}
        </button>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-md p-3 text-sm">
            {error}
          </div>
        )}
      </div>

      {/* Results */}
      {result && (
        <div className="mt-6 space-y-4">
          {/* Score + Grade */}
          <div className="bg-white rounded-lg shadow p-5">
            <div className="flex items-center space-x-4">
              <div className="text-4xl font-bold text-mtp-blue">
                {a.score || 0}/10
              </div>
              <span
                className={`px-3 py-1 rounded-full text-sm font-medium border ${
                  gradeColors[a.grade] || gradeColors.D
                }`}
              >
                {a.grade} — {a.score_label}
              </span>
            </div>
          </div>

          {/* Hook */}
          {a.hook && (
            <div className="bg-white rounded-lg shadow p-5">
              <p className="text-xl font-bold text-mtp-orange">{a.hook}</p>
            </div>
          )}

          {/* Pain Points */}
          {a.pain_points?.length > 0 && (
            <div className="bg-white rounded-lg shadow p-5">
              <h4 className="font-semibold text-gray-800 mb-3">Pain Points</h4>
              <ul className="space-y-2">
                {a.pain_points.map((p: any, i: number) => (
                  <li key={i} className="text-sm">
                    <span className="font-medium text-gray-800">{p.title}:</span>{" "}
                    <span className="text-gray-600">{p.description}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Email */}
          {(a.email_subject || result.email_text) && (
            <div className="bg-white rounded-lg shadow p-5">
              <h4 className="font-semibold text-gray-800 mb-2">Email</h4>
              {a.email_subject && (
                <p className="text-sm mb-2">
                  <span className="font-medium">Тема:</span> {a.email_subject}
                </p>
              )}
              {a.email_opening && (
                <p className="text-sm text-gray-600">{a.email_opening}</p>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="flex space-x-3">
            {result.html_url && (
              <a
                href={result.html_url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-5 py-2 bg-mtp-blue text-white rounded-md hover:bg-blue-800"
              >
                Відкрити презентацію
              </a>
            )}
            {result.pptx_url && (
              <a
                href={result.pptx_url}
                download
                className="px-5 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
              >
                Завантажити PPTX
              </a>
            )}
            <button
              onClick={saveLead}
              disabled={savingLead}
              className="px-5 py-2 border border-mtp-blue text-mtp-blue rounded-md hover:bg-blue-50 disabled:opacity-50"
            >
              {savingLead
                ? "Зберігаю..."
                : leadSaved
                ? "Збережено!"
                : "Зберегти як лід"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
