import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listBaoCao } from '../api'
import { lamLoi, nf, vtHien } from '../lib/fmt'
import { Alert, Badge, Empty, Loading, PageHeader } from '../components/ui'
import type { BaoCaoHienTruong } from '../types'

const TRANG = 50

export default function NhatKy() {
  const [ds, setDs] = useState<BaoCaoHienTruong[] | null>(null), [het, setHet] = useState(false)
  const [tu, setTu] = useState(''), [den, setDen] = useState(''), [loi, setLoi] = useState(''), [busy, setBusy] = useState(false)

  const tai = useCallback((offset: number, giu: BaoCaoHienTruong[]) => {
    setBusy(true)
    listBaoCao({ limit: TRANG, offset, tu: tu || undefined, den: den || undefined })
      .then((r) => { setDs([...giu, ...r]); setHet(r.length < TRANG); setLoi('') }, (e) => setLoi(lamLoi(e)))
      .finally(() => setBusy(false))
  }, [tu, den])
  useEffect(() => { tai(0, []) }, [tai])

  const loc = (e: React.ChangeEvent<HTMLInputElement>, set: (v: string) => void) => { setDs(null); set(e.target.value) }
  return (
    <>
      <PageHeader eyebrow="Hiện trường" title="Nhật ký thi công" sub="Báo cáo hằng ngày từ hiện trường — nguồn của biên bản nghiệm thu." actions={<Link to="/bao-cao" className="btn-primary">Báo cáo mới</Link>} />
      <div className="mb-3 flex flex-wrap items-end gap-3 text-sm">
        <label className="flex flex-col gap-1 font-medium">Từ ngày<input type="date" value={tu} max={den || undefined} onChange={(e) => loc(e, setTu)} className="rounded-lg border border-ink/20 bg-white px-3 py-2" /></label>
        <label className="flex flex-col gap-1 font-medium">Đến ngày<input type="date" value={den} min={tu || undefined} onChange={(e) => loc(e, setDen)} className="rounded-lg border border-ink/20 bg-white px-3 py-2" /></label>
        {(tu || den) && <button className="btn-ghost" onClick={() => { setDs(null); setTu(''); setDen('') }}>Bỏ lọc</button>}
      </div>
      {loi && <div className="mb-3"><Alert>{loi}</Alert></div>}
      {!ds ? <Loading /> : ds.length === 0 ? <Empty>Không có báo cáo hiện trường nào{tu || den ? ' trong khoảng ngày này' : ''}.</Empty> : (
        <>
          <section className="card overflow-x-auto"><table className="w-full min-w-[760px] text-sm">
            <thead><tr className="bg-paper text-left text-xs font-semibold text-ink/65"><th className="px-4 py-3">Ngày</th><th>Vị trí</th><th>Công tác</th><th>Khối lượng</th><th>Tổ đội · nhân lực</th><th>Ảnh</th><th>Người báo cáo</th><th>Đồng bộ</th></tr></thead>
            <tbody>{ds.map((b) => (
              <tr key={b.id} className="border-t border-ink/8 align-top">
                <td className="num px-4 py-3">{b.ngay}</td>
                <td><Link className="font-semibold text-brand underline" to={`/ban-do?vt=${b.viTriId}`}>{vtHien(b.viTri)}</Link></td>
                <td>{b.congTac ?? '—'}{b.noiDung && <div className="text-xs text-ink/55">{b.noiDung}</div>}</td>
                <td className="num">{b.khoiLuong != null ? nf(b.khoiLuong) : '—'}</td>
                <td>{b.toDoi ?? '—'}{b.nhanLuc != null && <span className="text-ink/55"> · {b.nhanLuc} người</span>}</td>
                <td className="num">{b.anh}</td><td>{b.nguoi}</td>
                <td><Badge tone={b.dongBo === 'da_dong_bo' ? 'ok' : 'warn'}>{b.dongBo === 'da_dong_bo' ? 'Đã đồng bộ' : 'Chờ đồng bộ'}</Badge></td>
              </tr>))}</tbody></table></section>
          <div className="mt-3 flex items-center justify-between text-sm text-ink/60">
            <span>Đang hiện {ds.length} báo cáo{het ? ' (đã hết)' : ''}</span>
            {!het && <button className="btn-ghost" disabled={busy} onClick={() => tai(ds.length, ds)}>{busy ? 'Đang tải…' : 'Tải thêm'}</button>}
          </div>
        </>)}
    </>
  )
}
