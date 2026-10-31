import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { Activity } from 'lucide-react'
import { useAuth } from '../lib/auth'
import { errorText } from '../lib/api'

export default function AuthPage() {
  const { user, login, register } = useAuth()
  const navigate = useNavigate()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [form, setForm] = useState({ email: '', username: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to="/" replace />

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value })

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      if (mode === 'login') await login(form.email, form.password)
      else await register(form.email, form.username, form.password)
      navigate('/')
    } catch (err) {
      setError(errorText(err))
    } finally {
      setBusy(false)
    }
  }

  const input = 'w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100'

  return (
    <div className="grid min-h-screen place-items-center p-4">
      <form onSubmit={submit} className="w-full max-w-sm rounded-3xl bg-white p-8 shadow-sm">
        <span className="grid h-10 w-10 place-items-center rounded-full bg-brand-700 text-white"><Activity size={18} /></span>
        <h1 className="mt-5 text-2xl font-semibold">{mode === 'login' ? 'Welcome back' : 'Create your account'}</h1>
        <p className="mt-1 text-sm text-slate-500">
          {mode === 'login' ? 'Log in to see how your sites are doing.' : 'Start monitoring your sites in a minute.'}
        </p>

        <div className="mt-6 space-y-3">
          <input className={input} type="email" placeholder="Email" required value={form.email} onChange={set('email')} />
          {mode === 'register' && (
            <input className={input} placeholder="Username" required value={form.username} onChange={set('username')} />
          )}
          <input className={input} type="password" placeholder="Password" required minLength={8} value={form.password} onChange={set('password')} />
        </div>

        {error && <p role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

        <button disabled={busy}
          className="mt-5 w-full rounded-full bg-brand-700 py-3 text-sm font-semibold text-white hover:bg-brand-900 disabled:opacity-60">
          {busy ? 'Please wait…' : mode === 'login' ? 'Log in' : 'Create account'}
        </button>

        <button type="button" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}
          className="mt-4 w-full text-center text-sm text-slate-500 hover:text-brand-700">
          {mode === 'login' ? 'New here? Create an account' : 'Already have an account? Log in'}
        </button>
      </form>
    </div>
  )
}
