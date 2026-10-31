import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowUpRight, RefreshCw } from 'lucide-react'
import api, { type Incident, type SitesResponse } from '../lib/api'

function ago(iso: string | null) {
  if (!iso) return 'never'
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}

function Stat({ label, value, hint, dark }: { label: string; value: number | string; hint: string; dark?: boolean }) {
  return (
    <div className={`rounded-2xl p-5 ${dark ? 'bg-gradient-to-br from-brand-500 to-brand-900 text-white' : 'bg-white'}`}>
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">{label}</p>
        <span className={`grid h-8 w-8 place-items-center rounded-full border ${dark ? 'border-white bg-white text-brand-900' : 'border-slate-300'}`}>
          <ArrowUpRight size={14} />
        </span>
      </div>
      <p className="mt-3 text-5xl font-semibold">{value}</p>
      <p className={`mt-2 text-xs ${dark ? 'text-white/75' : 'text-slate-500'}`}>{hint}</p>
    </div>
  )
}

function Status({ up }: { up: boolean | null }) {
  const [cls, text] =
    up === null ? ['bg-slate-100 text-slate-500', 'Not checked']
    : up ? ['bg-brand-50 text-brand-700', 'Up']
    : ['bg-red-50 text-red-700', 'Down']
  return <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${cls}`}>{text}</span>
}

export default function Dashboard() {
  const qc = useQueryClient()

  const sitesQ = useQuery({
    queryKey: ['sites'],
    queryFn: async () => (await api.get<SitesResponse>('/sites/')).data,
    refetchInterval: 30_000,
  })
  const incidentsQ = useQuery({
    queryKey: ['incidents'],
    queryFn: async () => (await api.get<Incident[]>('/sites/incidents/')).data,
    refetchInterval: 30_000,
  })
  const check = useMutation({
    mutationFn: (id: string) => api.post(`/sites/${id}/check/`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sites'] }),
  })

  const sites = sitesQ.data?.sites ?? []
  const incidents = incidentsQ.data ?? []
  const active = sites.filter((s) => s.is_active)
  const up = active.filter((s) => s.latest_is_up === true).length
  const down = active.filter((s) => s.latest_is_up === false).length

  return (
    <div>
      <h1 className="text-3xl font-semibold">Dashboard</h1>
      <p className="mt-1 text-sm text-slate-500">See which sites are up, and what the AI thinks went wrong when one isn’t.</p>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat dark label="Total sites" value={sitesQ.data?.total_sites ?? 0} hint={`${sitesQ.data?.total_inactive_sites ?? 0} paused`} />
        <Stat label="Up" value={up} hint="Latest check passed" />
        <Stat label="Down" value={down} hint="Latest check failed" />
        <Stat label="Incidents" value={incidents.length} hint="All time" />
      </div>

      {sitesQ.isError && (
        <p role="alert" className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
          Could not load your sites. Check that the API is running and CORS allows this origin.
        </p>
      )}

      <div className="mt-4 grid gap-4 xl:grid-cols-5">
        <section className="rounded-2xl bg-white p-5 xl:col-span-3">
          <h2 className="font-semibold">Sites</h2>
          {sites.length === 0 && !sitesQ.isLoading ? (
            <p className="mt-6 text-sm text-slate-500">No sites yet. Add your first one in the Django admin for now; the add-site form is the next screen to build.</p>
          ) : (
            <ul className="mt-3 divide-y divide-slate-100">
              {sites.map((s) => (
                <li key={s.id} className="flex items-center gap-3 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{s.name}</p>
                    <p className="truncate text-xs text-slate-400">{s.url}</p>
                  </div>
                  <div className="hidden text-right text-xs text-slate-500 sm:block">
                    <p>{s.latest_response_ms != null ? `${Math.round(s.latest_response_ms)} ms` : '–'}</p>
                    <p>{ago(s.last_checked_at)}</p>
                  </div>
                  <Status up={s.is_active ? s.latest_is_up : null} />
                  <button onClick={() => check.mutate(s.id)} disabled={check.isPending && check.variables === s.id}
                    aria-label={`Check ${s.name} now`}
                    className="grid h-8 w-8 place-items-center rounded-full border border-slate-200 text-slate-500 hover:border-brand-500 hover:text-brand-700 disabled:opacity-50">
                    <RefreshCw size={14} className={check.isPending && check.variables === s.id ? 'animate-spin' : ''} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rounded-2xl bg-white p-5 xl:col-span-2">
          <h2 className="font-semibold">Recent incidents</h2>
          {incidents.length === 0 ? (
            <p className="mt-6 text-sm text-slate-500">No incidents. An incident opens after 3 failed checks in a row.</p>
          ) : (
            <ul className="mt-3 space-y-3">
              {incidents.slice(0, 4).map((i) => (
                <li key={i.id} className="rounded-xl border border-slate-100 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="truncate text-sm font-medium">{i.site_name}</p>
                    <span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium ${i.is_ai_generated ? 'bg-brand-50 text-brand-700' : 'bg-slate-100 text-slate-500'}`}>
                      {i.is_ai_generated ? 'AI analysis' : 'Rule-based'}
                    </span>
                  </div>
                  <p className="mt-1 line-clamp-2 text-xs text-slate-600">{i.summary}</p>
                  <p className="mt-2 text-xs text-slate-400">
                    {ago(i.created_at)}
                    {i.confidence_score != null && ` · ${Math.round(i.confidence_score * 100)}% confidence`}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  )
}
