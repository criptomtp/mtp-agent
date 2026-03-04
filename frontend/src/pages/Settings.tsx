import { useEffect, useState } from "react";
import { api } from "../lib/api";
import ApiKeyInput from "../components/ApiKeyInput";

const SERVICES = [
  { name: "gemini", label: "Gemini API Key" },
  { name: "anthropic", label: "Anthropic (Claude) API Key" },
  { name: "google_maps", label: "Google Maps API Key" },
];

export default function Settings() {
  const [configured, setConfigured] = useState<Set<string>>(new Set());

  useEffect(() => {
    api
      .getApiKeys()
      .then((keys) => {
        const active = new Set(
          keys.filter((k) => k.is_active).map((k) => k.service_name)
        );
        setConfigured(active);
      })
      .catch(() => {});
  }, []);

  return (
    <div>
      <h2 className="text-2xl font-bold text-mtp-blue mb-6">Settings</h2>

      <div className="space-y-4 max-w-xl">
        {SERVICES.map((s) => (
          <ApiKeyInput
            key={s.name}
            serviceName={s.name}
            label={s.label}
            isConfigured={configured.has(s.name)}
          />
        ))}
      </div>

      <div className="mt-8 bg-white rounded-lg shadow p-5 max-w-xl">
        <h3 className="font-semibold text-gray-800 mb-2">Supabase Connection</h3>
        <p className="text-sm text-gray-500">
          Configure Supabase URL and keys in your <code className="bg-gray-100 px-1 rounded">.env</code> file.
          Restart the backend after changes.
        </p>
      </div>
    </div>
  );
}
