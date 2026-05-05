import { createFileRoute, redirect, useNavigate, useRouter } from '@tanstack/react-router'
import { useState } from 'react'
import { api } from '../api/client'
import { getToken, setSession, type AuthUser } from '../lib/auth'
import { Button, Card, CardBody, Input } from '../components/ui'

export const Route = createFileRoute('/login')({
  beforeLoad: () => {
    if (getToken()) throw redirect({ to: '/' })
  },
  component: LoginPage,
})

function LoginPage() {
  const navigate = useNavigate()
  const router = useRouter()
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const { data, error } = await api.POST('/api/auth/login', {
        body: { username, password },
      })
      if (error) throw error
      const resp = data as { token: string; user: AuthUser }
      if (!resp?.token) throw new Error('No token in response')
      setSession(resp.token, resp.user)
      await router.invalidate()
      navigate({ to: '/' })
    } catch (err) {
      const e = err as { message?: string; detail?: { message?: string } }
      setError(e?.detail?.message ?? e?.message ?? 'Login failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-blue-50 px-4">
      <Card className="w-full max-w-sm">
        <CardBody className="p-8">
          <div className="text-center mb-6">
            <div className="text-2xl font-bold text-slate-900">
              Vidhisa <span className="text-blue-600">Admin</span>
            </div>
            <div className="text-sm text-slate-500 mt-1">เข้าสู่ระบบเพื่อใช้งาน</div>
          </div>
          <form onSubmit={onSubmit} className="grid gap-4">
            <label className="grid gap-1">
              <span className="text-sm font-medium text-slate-700">Username</span>
              <Input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus required />
            </label>
            <label className="grid gap-1">
              <span className="text-sm font-medium text-slate-700">Password</span>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>
            {error && (
              <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2">{error}</div>
            )}
            <Button type="submit" disabled={busy} className="w-full">
              {busy ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>
        </CardBody>
      </Card>
    </div>
  )
}
