import { lazy, Suspense, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Download } from 'lucide-react'
import clsx from 'clsx'
import { getBanDoGeoJSON, importKmz, listTuyen, listViTriCot } from '../api'
import { useAsync } from '../lib/useAsync'
import { useRole } from '../lib/role'
import { lamLoi } from '../lib/fmt'
import { Alert, Loading } from '../components/ui'
import PanelViTri from '../components/PanelViTri'
import { BUOC_STYLE, BUOC_THU_TU } from '../lib/buoc'

const MapView = lazy(() => import('../components/MapView'))  // tách chunk: maplibre-gl nặng, chỉ tải ở trang này

export default function BanDo() {
  // `rev` tăng sau khi nhập KMZ để tải lại dữ liệu bản đồ.
  const [rev, setRev] = useState(0)
  return <BanDoNoiDung key={rev} onImported={() => setRev((r) => r + 1)} />
}

function BanDoNoiDung({ onImported }: { onImported: () => void }) {
  const poles = useAsync(listViTriCot), geo = useAsync(getBanDoGeoJSON), tuyen = useAsync(listTuyen)
  const { can } = useRole()
  const [sp, setSp] = useSearchParams()
  const [tat, setTat] = useState<string[]>([])               // mã tuyến đang tắt
  const [chiCanhBao, setChiCanhBao] = useState(false)
  const [trongKhung, setTrongKhung] = useState<string[] | null>(null)
  const [msg, setMsg] = useState(''), [loi, setLoi] = useState(''), [busy, setBusy] = useState(false)
  const file = useRef<HTMLInputElement>(null)
  const danhSach = useMemo(() => (poles ?? []).filter((p) => !chiCanhBao || p.canhBaoMuc), [poles, chiCanhBao])
  const bat = useMemo(() => (tuyen ?? []).map((t) => t.ma).filter((m) => !tat.includes(m)), [tuyen, tat])
  if (!poles || !geo || !tuyen) return <Loading />
  if (poles.length === 0) return <Alert tone="warn">Dự án này chưa có vị trí cột nào{can('du_an.quan_ly') ? '. Nhập KMZ hoặc thêm vị trí để bắt đầu.' : '.'}</Alert>

  const chonId = sp.get('vt') ?? ''
  const chon = poles.find((p) => p.id === chonId) ?? poles.find((p) => p.buoc === 'dang_thi_cong_mong') ?? poles[0]
  const dem = Object.fromEntries(BUOC_THU_TU.map((b) => [b, 0])) as Record<string, number>
  const idsKhung = new Set(trongKhung ?? danhSach.map((p) => p.id))
  for (const p of danhSach) if (idsKhung.has(p.id)) dem[p.buoc]++

  const nhap = async (f?: File) => {
    if (!f) return
    setBusy(true); setMsg(''); setLoi('')
    try {
      const r = await importKmz(f)
      setMsg(`Đã nhập ${r.tuyen} tuyến, cập nhật toạ độ ${r.cotCapNhat} vị trí cột${r.khongKhop.length ? `; không khớp tên: ${r.khongKhop.slice(0, 8).join(', ')}${r.khongKhop.length > 8 ? '…' : ''}` : ''}.`)
      setTimeout(onImported, 1800)
    } catch (e) { setLoi(lamLoi(e, 'Không nhập được file')) } finally { setBusy(false); if (file.current) file.current.value = '' }
  }
  const chip = (on: boolean) => clsx('min-h-[38px] rounded-full border px-4 text-sm font-semibold', on ? 'border-brand bg-brand text-white' : 'border-ink/20 bg-white text-ink/80 hover:bg-brand-soft')

  return (
    <div className="-m-4 flex min-h-full flex-col lg:-m-6 lg:h-full lg:flex-row">
      <section className="flex min-w-0 flex-1 flex-col gap-3 p-4 lg:p-5">
        <div className="flex flex-wrap items-center gap-2" aria-label="Lớp tuyến">
          {tuyen.map((t) => {
            const on = !tat.includes(t.ma)
            return <button key={t.id} aria-pressed={on} className={chip(on)} onClick={() => setTat(on ? [...tat, t.ma] : tat.filter((x) => x !== t.ma))}>
              {t.loai === 'cu' ? `${t.ten}` : t.ten}</button>
          })}
          <button aria-pressed={chiCanhBao} className={chip(chiCanhBao)} onClick={() => setChiCanhBao(!chiCanhBao)}>Chỉ vị trí có cảnh báo</button>
        </div>
        {can('du_an.quan_ly') && (
          <div>
            <input ref={file} type="file" accept=".kmz,.kml" hidden onChange={(e) => nhap(e.target.files?.[0])} />
            <button className="btn-ghost" disabled={busy} onClick={() => file.current?.click()}><Download size={16} />{busy ? 'Đang nhập…' : 'Import KMZ / bảng kê'}</button>
          </div>
        )}
        {msg && <Alert tone="ok">{msg}</Alert>}
        {loi && <Alert>{loi}</Alert>}
        <div className="relative min-h-[420px] flex-1">
          <Suspense fallback={<Loading />}>
            <MapView poles={danhSach} geo={geo} tuyenHienThi={bat} selectedId={chon.id} onSelect={(id) => setSp({ vt: id }, { replace: true })} onViewport={setTrongKhung} />
          </Suspense>
          <div className="absolute bottom-3 left-3 z-10 rounded-lg bg-white/95 p-3 text-xs shadow-lg" aria-label="Chú giải bước thi công">
            <div className="mb-1.5 font-bold">Bước thi công</div>
            <ul className="space-y-1">
              {BUOC_THU_TU.map((b) => (
                <li key={b} className="flex items-center gap-2">
                  <i className="size-3 rounded-full" style={{ background: BUOC_STYLE[b].bg, border: `2px solid ${BUOC_STYLE[b].vien === '#fff' ? BUOC_STYLE[b].bg : BUOC_STYLE[b].vien}` }} />
                  <span>{BUOC_STYLE[b].nhan} · <span className="num font-semibold">{dem[b]}</span></span></li>))}
              <li className="flex items-center gap-2"><i className="w-4 border-t-2 border-dashed border-ink/50" /><span>Tuyến cũ, chờ thu hồi</span></li>
            </ul>
          </div>
        </div>
      </section>
      <aside className="w-full shrink-0 overflow-y-auto border-ink/10 bg-white lg:w-[372px] lg:border-l" aria-label="Chi tiết vị trí">
        <PanelViTri id={chon.id} tuyenTen={tuyen.find((t) => t.ma === chon.tuyenMa)?.ten} />
      </aside>
    </div>
  )
}
