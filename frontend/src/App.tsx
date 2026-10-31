import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './lib/auth'
import Layout from './components/Layout'
import AuthPage from './pages/AuthPage'
import Dashboard from './pages/Dashboard'

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } })

function Protected() {
  const { user, loading } = useAuth()
  if (loading) return <div className="grid min-h-screen place-items-center text-slate-500">Loading…</div>
  return user ? <Layout /> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<AuthPage />} />
            <Route element={<Protected />}>
              <Route index element={<Dashboard />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}
