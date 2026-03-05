import { NavLink, Outlet } from "react-router-dom";

const links = [
  { to: "/", label: "Dashboard", icon: "\u{1F4CA}" },
  { to: "/leads", label: "Leads", icon: "\u{1F465}" },
  { to: "/runs", label: "Runs", icon: "\u{1F680}" },
  { to: "/settings", label: "Settings", icon: "\u2699\uFE0F" },
];

export default function Layout() {
  return (
    <div className="flex h-screen">
      <aside className="w-56 bg-mtp-blue text-white flex flex-col">
        <div className="p-5 border-b border-white/10">
          <h1 className="text-lg font-bold tracking-wide">MTP Fulfillment</h1>
          <p className="text-xs text-white/60 mt-1">Lead Generation Dashboard</p>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.to === "/"}
              className={({ isActive }) =>
                `block px-3 py-2 rounded text-sm transition-colors ${
                  isActive
                    ? "bg-white/20 font-medium"
                    : "hover:bg-white/10 text-white/80"
                }`
              }
            >
              <span className="mr-2">{l.icon}</span>
              {l.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
