import { Link } from 'react-router-dom'
import { Camera } from 'lucide-react'
import { getDem, listBaoCao, listViTriCot } from '../api'
import { useAsync } from '../lib/useAsync'
import { useRole } from '../lib/role'
import { thuNgay } from '../lib/fmt'
import { Bar, Loading } from '../components/ui'
import { BUOC_STYLE, BUOC_THU_TU } from '../lib/buoc'

export default function TongQuan() {
  const { user, can } = useRole()
  const dem = useAsync(getDem), poles = useAsync(listViTriCot), bc = useAsync(() => listBaoCao({ limit: 5 }))
  if (!dem || !poles || !bc) return <Loading />
  const so = (b: string) => poles.filter((p) => p.buoc === b).length
  const xong = so('da_keo_day') + so('da_dung_cot') + so('mong_da_nghiem_thu')
  const canhBao = poles.filter((p) => p.canhBaoMuc).length
  return (
    <div className="mx-auto max-w-2xl space-y-3">
      <header><div className="text-xs text-ink/55">{thuNgay()}</div><h1 className="text-xl font-bold">Xin chào, {user?.hoTen}</h1></header>
      <section className="card p-4">
        <div className="flex items-baseline justify-between"><h2 className="text-sm font-bold">Tiến độ tuyến</h2><span className="num text-sm font-semibold">{xong}/{poles.length} vị trí</span></div>
        <div className="mt-2"><Bar value={xong} max={poles.length} /></div>
        <ul className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
          {BUOC_THU_TU.map((b) => <li key={b} className="flex items-center gap-2"><i className="size-3 rounded-full" style={{ background: BUOC_STYLE[b].bg }} />{BUOC_STYLE[b].nhan} · <b className="num">{so(b)}</b></li>)}
        </ul>
      </section>
      <div className="grid grid-cols-3 gap-2">
        <Link to="/qaqc" className="card p-3"><div className="num text-2xl font-bold text-danger">{dem.loiChan}</div><div className="text-xs text-ink/65">Lỗi chặn</div></Link>
        <Link to="/duyet" className="card p-3"><div className="num text-2xl font-bold text-[#8a5a00]">{dem.choToi}</div><div className="text-xs text-ink/65">Chờ bạn duyệt</div></Link>
        <Link to="/ban-do" className="card p-3"><div className="num text-2xl font-bold">{canhBao}</div><div className="text-xs text-ink/65">Vị trí có cảnh báo</div></Link>
      </div>
      {dem.choToiItems.length > 0 && (
        <section className="card p-4"><h2 className="mb-2 text-sm font-bold">Cần xử lý</h2>
          <ul className="divide-y divide-ink/8">{dem.choToiItems.map((i) => <li key={i.ma}><Link to="/duyet" className="block py-2 text-sm"><b className="num">{i.ma}</b> · <span className="text-ink/60">{i.nhan.toLowerCase()}</span><span className="block truncate text-ink/75">{i.tieuDe}</span></Link></li>)}</ul></section>)}
      <section className="card p-4"><h2 className="mb-2 text-sm font-bold">Báo cáo gần đây</h2>
        {bc.length === 0 ? <p className="text-sm text-ink/60">Chưa có báo cáo.</p> : <ul className="space-y-1.5 text-sm">{bc.slice(0, 4).map((b) => <li key={b.id}><span className="num text-ink/55">{b.ngay}</span> · <b>{b.viTri}</b> · {b.congTac ?? b.noiDung}</li>)}</ul>}
      </section>
      {can('bao_cao.gui') && <Link to="/bao-cao" className="btn-primary fixed inset-x-4 bottom-20 z-20 justify-center shadow-lg lg:hidden"><Camera size={18} />Báo cáo hiện trường</Link>}
    </div>
  )
}
