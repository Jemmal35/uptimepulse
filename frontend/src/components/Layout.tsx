import { NavLink, Outlet } from 'react-router-dom'
import { AlertTriangle, Globe, LayoutDashboard, LogOut, Activity, type LucideIcon } from 'lucide-react'
import { useAuth } from '../lib/auth'

const nav: { to?: string; label: string; icon: LucideIcon; soon?: boolean }[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { label: 'Sites', icon: Globe, soon: true },
  { label: 'Incidents', icon: AlertTriangle, soon: true },
]

export default function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className="mx-auto flex min-h-screen max-w-[1400px] gap-4 p-4">
      <aside className="sticky top-4 hidden h-[calc(100vh-2rem)] w-60 shrink-0 flex-col rounded-3xl bg-white p-5 md:flex">
        <div className="flex items-center gap-2 px-2 text-lg font-semibold">
          <span className="grid h-8 w-8 place-items-center rounded-full bg-brand-700 text-white"><Activity size={16} /></span>
          Uptime Pulse
        </div>

        <p className="mt-8 px-2 text-xs text-slate-400">Menu</p>
        <nav className="mt-2 space-y-1">
          {nav.map(({ to, label, icon: Icon, soon }) =>
            to ? (
              <NavLink key={label} to={to} end
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium ${isActive ? 'bg-brand-50 text-brand-900' : 'text-slate-500 hover:bg-slate-50'}`}>
                <Icon size={18} /> {label}
              </NavLink>
            ) : (
              <div key={label} className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-300">
                <Icon size={18} /> {label}
                {soon && <span className="ml-auto rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-400">soon</span>}
              </div>
            ),
          )}
        </nav>

        <button onClick={logout}
          className="mt-auto flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-500 hover:bg-slate-50">
          <LogOut size={18} /> Log out
        </button>
      </aside>

      <main className="min-w-0 flex-1 rounded-3xl bg-white/60 p-4 sm:p-6">
        <div className="mb-6 flex justify-end">
          <div className="flex items-center gap-3 rounded-full bg-white py-1.5 pl-1.5 pr-4">
            <span className="grid h-9 w-9 place-items-center rounded-full bg-brand-100 font-semibold text-brand-900">
              {user?.username?.[0]?.toUpperCase()}
            </span>
            <div className="leading-tight">
              <p className="text-sm font-semibold">{user?.username}</p>
              <p className="text-xs text-slate-400">{user?.email}</p>
            </div>
          </div>
        </div>
        <Outlet />
      </main>
    </div>
  )
}
