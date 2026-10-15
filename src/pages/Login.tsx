import { useState } from 'react'
import { Zap } from 'lucide-react'
import { useRole } from '../lib/role'

export default function Login() {
  const { login } = useRole()
  const [email, setEmail] = useState(''), [mk, setMk] = useState('')
  const [err, setErr] = useState(''), [busy, setBusy] = useState(false)
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true); setErr('')
    try { await login(email, mk) } catch (x) { setErr(x instanceof Error ? x.message : 'Đăng nhập thất bại') } finally { setBusy(false) }
  }
  return (
    <main className="min-h-screen grid place-items-center p-4">
      <form onSubmit={submit} className="card p-6 w-full max-w-sm space-y-4">
        <div className="flex items-center gap-2">
          <span className="grid place-items-center size-9 rounded-lg bg-amber2 text-ink"><Zap size={20} /></span>
          <div><h1 className="font-bold leading-none">TuyếnSố</h1><p className="text-xs text-ink/55 mt-1">Xây lắp điện · Tuấn Thành</p></div>
        </div>
        <label className="block text-sm font-semibold">Email
          <input type="email" required autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-lg border border-ink/15 px-3 min-h-[44px] font-normal" /></label>
        <label className="block text-sm font-semibold">Mật khẩu
          <input type="password" required autoComplete="current-password" value={mk} onChange={(e) => setMk(e.target.value)}
            className="mt-1 w-full rounded-lg border border-ink/15 px-3 min-h-[44px] font-normal" /></label>
        {err && <p role="alert" className="rounded-lg bg-danger/10 p-3 text-sm text-danger">{err}</p>}
        <button className="btn-primary w-full" disabled={busy}>{busy ? 'Đang đăng nhập…' : 'Đăng nhập'}</button>
        {import.meta.env.DEV && <p className="text-xs text-ink/50">Dữ liệu demo: tài khoản dạng <span className="num">giamdoc@demo.tuyenso.local</span> (mật khẩu: SEED_DEMO_PASSWORD trong .env).</p>}
      </form>
    </main>
  )
}
