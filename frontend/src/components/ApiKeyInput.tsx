import { useState } from "react";
import { api } from "../lib/api";

interface Props {
  serviceName: string;
  label: string;
  isConfigured?: boolean;
}

export default function ApiKeyInput({ serviceName, label, isConfigured }: Props) {
  const [value, setValue] = useState("");
  const [status, setStatus] = useState<"idle" | "testing" | "valid" | "invalid" | "saved">("idle");

  const test = async () => {
    if (!value.trim()) return;
    setStatus("testing");
    try {
      const result = await api.testApiKey(serviceName, value);
      setStatus(result.valid ? "valid" : "invalid");
    } catch {
      setStatus("invalid");
    }
  };

  const save = async () => {
    if (!value.trim()) return;
    try {
      await api.saveApiKey(serviceName, value);
      setStatus("saved");
      setValue("");
    } catch {
      setStatus("invalid");
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center justify-between mb-2">
        <label className="text-sm font-medium text-gray-700">{label}</label>
        {isConfigured && (
          <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
            Configured
          </span>
        )}
      </div>
      <div className="flex gap-2">
        <input
          type="password"
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            setStatus("idle");
          }}
          placeholder={isConfigured ? "Enter new key to update" : "Enter API key"}
          className="flex-1 border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-mtp-blue/30"
        />
        <button
          onClick={test}
          disabled={!value.trim() || status === "testing"}
          className="px-3 py-1.5 text-sm border rounded hover:bg-gray-50 disabled:opacity-40"
        >
          {status === "testing" ? "Testing..." : "Test"}
        </button>
        <button
          onClick={save}
          disabled={!value.trim()}
          className="px-3 py-1.5 text-sm bg-mtp-blue text-white rounded hover:bg-mtp-blue/90 disabled:opacity-40"
        >
          Save
        </button>
      </div>
      {status === "valid" && <p className="text-xs text-green-600 mt-1">Key is valid</p>}
      {status === "invalid" && <p className="text-xs text-red-600 mt-1">Key is invalid</p>}
      {status === "saved" && <p className="text-xs text-green-600 mt-1">Saved successfully</p>}
    </div>
  );
}
