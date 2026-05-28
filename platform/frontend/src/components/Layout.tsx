import { NavLink, Outlet } from "react-router-dom";

const navItems = [
  { to: "/", label: "Repositories", icon: "📁" },
  { to: "/portfolio", label: "Portfolio", icon: "📊" },
  { to: "/upload", label: "Upload", icon: "⬆️" },
];

export default function Layout() {
  return (
    <div className="flex min-h-screen bg-bg">
      {/* Sidebar */}
      <aside className="w-56 bg-sidebar text-sidebar-text flex flex-col">
        <div className="px-5 py-4 border-b border-gray-700">
          <h1 className="text-lg font-bold tracking-tight">Pharabius</h1>
          <p className="text-xs text-gray-400 mt-0.5">Technical Debt Platform</p>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-2 px-3 py-2 rounded text-sm transition-colors ${
                  isActive
                    ? "bg-primary text-white"
                    : "text-gray-300 hover:bg-gray-700 hover:text-white"
                }`
              }
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="px-4 py-3 border-t border-gray-700 text-xs text-gray-500">
          v2.2.3 · MVP
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="max-w-6xl mx-auto px-6 py-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
