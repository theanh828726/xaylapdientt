import { LogOut } from 'lucide-react'
import { useRole } from '../lib/role'
import { PageHeader } from '../components/ui'
import { ten2chu } from '../lib/fmt'

export default function Toi() {
  const { user, role, duAn, duAnId, chonDuAn, logout } = useRole()
  return (
    <div className="mx-auto max-w-xl">
      <PageHeader title="Tôi" />
      <section className="card mb-3 flex items-center gap-4 p-4">
        <span className="grid size-14 place-items-center rounded-full bg-brand text-lg font-bold text-white">{ten2chu(user?.hoTen ?? '')}</span>
        <div><div className="text-lg font-bold">{user?.hoTen}</div><div className="text-sm text-ink/65">{role}{user?.donVi ? ` · ${user.donVi}` : ''}</div><div className="text-xs text-ink/50">{user?.email}</div></div>
      </section>
      <section className="card mb-3 p-4">
        <label htmlFor="da" className="text-sm font-bold">Dự án đang làm việc</label>
        <select id="da" className="mt-2 w-full rounded-lg border border-ink/20 bg-white px-3 py-2.5" value={duAnId ?? ''} onChange={(e) => e.target.value !== duAnId && chonDuAn(e.target.value)}>
          {duAn.map((d) => <option key={d.id} value={d.id}>{d.ma} · {d.ten}</option>)}</select>
      </section>
      <button className="btn-ghost w-full justify-center" onClick={logout}><LogOut size={16} />Đăng xuất</button>
    </div>
  )
}
