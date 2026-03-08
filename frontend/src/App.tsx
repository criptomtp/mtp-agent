import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Leads from "./pages/Leads";
import Runs from "./pages/Runs";
import Settings from "./pages/Settings";
import ProposalPage from "./pages/ProposalPage";

export default function App() {
  return (
    <Routes>
      {/* Public route — no auth, no layout */}
      <Route path="/proposals/:slug" element={<ProposalPage />} />

      {/* Dashboard routes with layout */}
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/leads" element={<Leads />} />
        <Route path="/runs" element={<Runs />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
