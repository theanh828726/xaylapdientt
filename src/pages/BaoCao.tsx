import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { AlertTriangle, Camera, Lock, Minus, Plus, WifiOff } from 'lucide-react'
import clsx from 'clsx'
import { getFormBaoCao, listViTriCot } from '../api'
import { useRole } from '../lib/role'
import { dongBo, guiMuc, luuCho } from '../lib/offline'
import { homNay, lamLoi, nf, thuNgay, vtHien } from '../lib/fmt'
import { Alert, Loading } from '../components/ui'
import type { FormBaoCao, ViTriCot } from '../types'

interface Nhap { congTacMa: string; khoiLuong: string; thoiTiet: string; toDoi: string; nhanLuc: number; may: string[]; ghiChu: string; hoanThanh: boolean }
const THOI_TIET = ['Nắng', 'Nhiều mây', 'Mưa nhẹ', 'Mưa to']
const khoaNhap = (id: string) => `tuyenso.nhap.${id}`

function khoangCach(a: { lat: number; lon: number }, b: { lat: number; lon: number }) {
  const R = 6371000, r = (x: number) => (x * Math.PI) / 180
  const h = Math.sin(r(b.lat - a.lat) / 2) ** 2 + Math.cos(r(a.lat)) * Math.cos(r(b.lat)) * Math.sin(r(b.lon - a.lon) / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(h))
}

interface Anh { id: string; blob: Blob; url: string; lat?: number; lon?: number }

function Form({ viTriId, poles }: { viTriId: string; poles: ViTriCot[] }) {
  const nav = useNavigate()
  const { duAnId } = useRole()
  const [f, setF] = useState<FormBaoCao | null>(null)
  const [n, setN] = useState<Nhap>(() => {
    try { const s = localStorage.getItem(khoaNhap(viTriId)); if (s) return JSON.parse(s) as Nhap } catch { /* bỏ qua */ }
    return { congTacMa: '', khoiLuong: '', thoiTiet: 'Nắng', toDoi: '', nhanLuc: 5, may: [], ghiChu: '', hoanThanh: false }
  })
  const [anh, setAnh] = useState<Anh[]>([]), [gps, setGps] = useState<{ lat: number; lon: number } | null>(null)
  const [online, setOnline] = useState(navigator.onLine), [loi, setLoi] = useState(''), [msg, setMsg] = useState(''), [busy, setBusy] = useState(false)
  const file = useRef<HTMLInputElement>(null)

  useEffect(() => {
    let ok = true
    getFormBaoCao(viTriId).then((r) => {
      if (!ok) return
      setF(r)
      setN((x) => ({ ...x, congTacMa: x.congTacMa || r.congTacMacDinh || '', toDoi: x.toDoi || r.toDoi[0] || '' }))
    }, (e) => ok && setLoi(lamLoi(e)))
    return () => { ok = false }
  }, [viTriId])
  useEffect(() => {
    const b = () => setOnline(true), t = () => setOnline(false)
    window.addEventListener('online', b); window.addEventListener('offline', t)
    return () => { window.removeEventListener('online', b); window.removeEventListener('offline', t) }
  }, [])
  useEffect(() => {
    const id = navigator.geolocation?.watchPosition((p) => setGps({ lat: p.coords.latitude, lon: p.coords.longitude }), () => {}, { enableHighAccuracy: true })
    return () => { if (id != null) navigator.geolocation.clearWatch(id) }
  }, [])
  useEffect(() => () => anh.forEach((a) => URL.revokeObjectURL(a.url)), []) // eslint-disable-line
  useEffect(() => { try { localStorage.setItem(khoaNhap(viTriId), JSON.stringify(n)) } catch { /* bỏ qua */ } }, [n, viTriId])

  const kc = useMemo(() => (f?.viTri.lat != null && f.viTri.lon != null && gps ? khoangCach(gps, { lat: f.viTri.lat, lon: f.viTri.lon! }) : null), [f, gps])
  if (!f) return loi ? <Alert>{loi}</Alert> : <Loading />
  const ct = f.congTac.find((c) => c.ma === n.congTacMa)
  const set = <K extends keyof Nhap>(k: K, v: Nhap[K]) => setN((x) => ({ ...x, [k]: v }))
  const thieuAnh = Math.max(0, f.anhToiThieu - anh.length)

  const themAnh = (fl: FileList | null) => {
    const ds = Array.from(fl ?? [])   // sao chép trước khi xoá input
    if (file.current) file.current.value = ''
    setAnh((x) => [...x, ...ds.map((b) => ({ id: crypto.randomUUID(), blob: b, url: URL.createObjectURL(b), ...(gps ?? {}) }))])
  }
  const gui = async (nhap: boolean) => {
    setLoi(''); setMsg('')
    if (!nhap) {
      if (!n.congTacMa) return setLoi('Chọn công tác trước khi gửi.')
      if (thieuAnh > 0) return setLoi(`Cần tối thiểu ${f.anhToiThieu} ảnh, còn thiếu ${thieuAnh}.`)
    }
    if (nhap) { setMsg('Đã lưu nháp trên máy.'); return }
    setBusy(true)
    const muc = {
      clientId: crypto.randomUUID(), duAnId: duAnId ?? '',
      baoCao: { viTri: viTriId, ngay: homNay(), noiDung: n.ghiChu, soAnh: anh.length, congTacMa: n.congTacMa, khoiLuong: n.khoiLuong ? Number(n.khoiLuong.replace(',', '.')) : undefined,
        hoanThanh: n.hoanThanh, thoiTiet: n.thoiTiet, toDoi: n.toDoi, nhanLuc: n.nhanLuc, mayThiCong: n.may, ...(gps ?? {}) },
      anh: anh.map((a) => ({ clientId: a.id, blob: a.blob, lat: a.lat, lon: a.lon })),
    }
    try {
      if (!online) throw new Error('offline')
      await guiMuc(muc)
      try { localStorage.removeItem(khoaNhap(viTriId)) } catch { /* bỏ qua */ }
      setMsg('Đã gửi báo cáo.'); setTimeout(() => nav('/tong-quan'), 900)
    } catch (e) {
      if (!online || (e instanceof TypeError)) {
        await luuCho(muc); try { localStorage.removeItem(khoaNhap(viTriId)) } catch { /* bỏ qua */ }; setMsg('Đang offline — báo cáo và ảnh đã lưu trên máy, sẽ tự gửi khi có mạng.')
      } else setLoi(lamLoi(e))
    } finally { setBusy(false) }
  }

  return (
    <div className="mx-auto max-w-xl pb-28">
      <header className="mb-3 flex items-center justify-between">
        <div><div className="text-xs text-ink/55">{thuNgay()}</div><h1 className="text-xl font-bold">Báo cáo hiện trường</h1></div>
        {!online && <span className="flex items-center gap-1 rounded-full bg-amber2/25 px-3 py-1 text-xs font-bold text-[#8a5a00]"><WifiOff size={13} />Offline</span>}
      </header>
      <section className="card mb-3 p-4">
        <div className="text-xs text-ink/55">Vị trí</div>
        <div className="flex items-baseline justify-between gap-2"><div className="text-lg font-bold">{vtHien(f.viTri.ten)} <span className="text-sm font-normal text-ink/60">{f.viTri.kmText} · {f.viTri.loaiMong}</span></div>
          <select aria-label="Đổi vị trí" className="min-h-[44px] rounded-lg border border-ink/20 bg-white px-2 text-sm" value={viTriId} onChange={(e) => nav(`/bao-cao/${e.target.value}`, { replace: true })}>
            {poles.map((p) => <option key={p.id} value={p.id}>{vtHien(p.ten)}</option>)}</select></div>
        <div className="mt-1 text-xs text-ink/60">{kc != null ? <>Cách vị trí thiết kế <b className="num">{nf(Math.round(kc))} m</b>{kc > 100 && <span className="font-semibold text-danger"> — ngoài phạm vi 100 m</span>}</>
          : 'Chưa có GPS — hãy bật định vị để xác nhận bạn đang ở hiện trường.'}</div>
      </section>
      {f.canhBao.map((c) => (
        <div key={c} role="alert" className="mb-3 flex gap-2 rounded-lg border border-amber2/40 bg-amber2/15 p-3 text-sm"><AlertTriangle size={17} className="mt-0.5 shrink-0 text-amber2" />{c}</div>))}
      <section className="card mb-3 p-4">
        <h2 className="mb-2 text-sm font-bold">Công tác hôm nay</h2>
        <div className="flex flex-wrap gap-2">
          {f.congTac.map((c) => (
            <button key={c.ma} disabled={c.khoa} aria-pressed={n.congTacMa === c.ma} onClick={() => set('congTacMa', c.ma)} title={c.lyDoKhoa ?? undefined}
              className={clsx('flex min-h-[44px] items-center gap-1.5 rounded-full border px-3.5 text-sm font-semibold', n.congTacMa === c.ma ? 'border-brand bg-brand text-white' : 'border-ink/20 bg-white', c.khoa && 'opacity-45')}>
              {c.khoa && <Lock size={13} />}{c.ten}</button>))}
        </div>
        {ct?.khoa && ct.lyDoKhoa && <p className="mt-2 text-xs text-danger">{ct.lyDoKhoa}</p>}
        <label className="mt-3 block text-sm font-medium" htmlFor="kl">Khối lượng thực hiện {f.khoiLuongThietKe.dvt && <span className="font-normal text-ink/55">(thiết kế {nf(f.khoiLuongThietKe.daoMong)} {f.khoiLuongThietKe.dvt})</span>}</label>
        <input id="kl" inputMode="decimal" className="mt-1 w-full rounded-lg border border-ink/20 px-3 py-2.5" value={n.khoiLuong} onChange={(e) => set('khoiLuong', e.target.value)} placeholder="0" />
        <label className="mt-3 flex items-center gap-2 text-sm"><input type="checkbox" checked={n.hoanThanh} onChange={(e) => set('hoanThanh', e.target.checked)} className="size-5" />Đã hoàn thành công tác này</label>
      </section>
      <details className="card mb-3 p-4 [&_summary]:min-h-[44px]">
        <summary className="flex cursor-pointer items-center justify-between text-sm font-bold">Thông tin thêm <span className="text-xs font-normal text-ink/55">thời tiết, tổ đội, nhân lực, máy, ghi chú (đã điền sẵn)</span></summary>
      <div className="space-y-3 pt-3">
        <div><div className="mb-1 text-sm font-medium">Thời tiết</div>
          <div className="flex flex-wrap gap-2">{THOI_TIET.map((t) => (
            <button key={t} aria-pressed={n.thoiTiet === t} onClick={() => set('thoiTiet', t)} className={clsx('min-h-[44px] rounded-full border px-4 text-sm', n.thoiTiet === t ? 'border-brand bg-brand-soft font-semibold text-brand' : 'border-ink/20')}>{t}</button>))}</div></div>
        <div><label className="mb-1 block text-sm font-medium" htmlFor="td">Tổ đội</label>
          <select id="td" className="w-full rounded-lg border border-ink/20 bg-white px-3 py-2.5" value={n.toDoi} onChange={(e) => set('toDoi', e.target.value)}>{f.toDoi.map((t) => <option key={t}>{t}</option>)}</select></div>
        <div className="flex items-center justify-between"><span className="text-sm font-medium">Nhân lực</span>
          <span className="flex items-center gap-3"><button aria-label="Giảm" className="grid size-11 place-items-center rounded-lg border border-ink/20" onClick={() => set('nhanLuc', Math.max(0, n.nhanLuc - 1))}><Minus size={16} /></button>
            <b className="num w-8 text-center text-lg">{n.nhanLuc}</b>
            <button aria-label="Tăng" className="grid size-11 place-items-center rounded-lg border border-ink/20" onClick={() => set('nhanLuc', n.nhanLuc + 1)}><Plus size={16} /></button></span></div>
        <div><div className="mb-1 text-sm font-medium">Máy thi công</div>
          <div className="flex flex-wrap gap-2">{f.mayThiCong.map((m) => {
            const on = n.may.includes(m)
            return <button key={m} aria-pressed={on} onClick={() => set('may', on ? n.may.filter((x) => x !== m) : [...n.may, m])} className={clsx('min-h-[44px] rounded-full border px-4 text-sm', on ? 'border-brand bg-brand-soft font-semibold text-brand' : 'border-ink/20')}>{m}</button>
          })}</div></div>
        <div><label className="mb-1 block text-sm font-medium" htmlFor="gc">Ghi chú</label>
          <textarea id="gc" rows={2} className="w-full rounded-lg border border-ink/20 px-3 py-2" value={n.ghiChu} onChange={(e) => set('ghiChu', e.target.value)} /></div>
      </div>
      </details>
      <section className="card p-4">
        <div className="mb-2 flex items-baseline justify-between"><h2 className="text-sm font-bold">Ảnh hiện trường</h2>
          <span className={clsx('text-xs font-semibold', thieuAnh > 0 ? 'text-danger' : 'text-brand')}>{anh.length}/{f.anhToiThieu} ảnh tối thiểu</span></div>
        <input ref={file} type="file" accept="image/*" capture="environment" multiple hidden onChange={(e) => themAnh(e.target.files)} />
        <div className="grid grid-cols-4 gap-2">
          {anh.map((a) => <img key={a.id} src={a.url} alt="Ảnh vừa chụp" className="aspect-square w-full rounded-lg object-cover" />)}
          <button aria-label="Chụp hoặc chọn ảnh" onClick={() => file.current?.click()} className="grid aspect-square place-items-center rounded-lg border-2 border-dashed border-ink/25 text-ink/60"><Camera size={22} /></button>
        </div>
        <p className="mt-2 text-xs text-ink/55">Ảnh gắn toạ độ GPS lúc chụp (chỉ dùng để xác nhận bạn đang ở hiện trường){gps ? '' : '; chưa có GPS'}.</p>
      </section>
      {loi && <div className="mt-3"><Alert>{loi}</Alert></div>}
      {msg && <div className="mt-3"><Alert tone="ok">{msg}</Alert></div>}
      <div className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-2 gap-3 border-t border-ink/10 bg-white p-3">
        <button className="btn-ghost justify-center" disabled={busy} onClick={() => gui(true)}>Lưu nháp</button>
        <button className="btn-primary justify-center" disabled={busy || !!ct?.khoa} onClick={() => gui(false)}>{busy ? 'Đang gửi…' : 'Gửi báo cáo'}</button>
      </div>
    </div>
  )
}

export default function BaoCao() {
  const { viTriId } = useParams()
  const nav = useNavigate()
  const [poles, setPoles] = useState<ViTriCot[] | null>(null)
  const { duAnId } = useRole()
  useEffect(() => { listViTriCot().then(setPoles, () => setPoles([])); dongBo(duAnId ?? undefined) }, [duAnId])
  useEffect(() => { if (poles?.length && !viTriId) nav(`/bao-cao/${(poles.find((p) => p.buoc === 'dang_thi_cong_mong') ?? poles[0]).id}`, { replace: true }) }, [poles, viTriId, nav])
  if (!poles) return <Loading />
  if (!viTriId) return <Alert tone="warn">Dự án này chưa có vị trí cột.</Alert>
  return <Form key={viTriId} viTriId={viTriId} poles={poles} />
}
