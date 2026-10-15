import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, Check, Circle } from 'lucide-react'
import clsx from 'clsx'
import { getAnhViTri, getViTriCot, layAnhBlobUrl, xuatChietTinhViTri } from '../api'
import { lamLoi, nf, nfCoDinh } from '../lib/fmt'
import type { AnhViTri, ViTriCotChiTiet } from '../types'
import { Alert, Bar, Loading } from './ui'

const TAB = ['tong-quan', 'vat-tu', 'ho-so', 'anh'] as const
type Tab = (typeof TAB)[number]
const toneChip = { ok: 'bg-brand-soft text-brand', warn: 'bg-amber2/25 text-[#8a5a00]', info: 'bg-sky-100 text-sky-800', bad: 'bg-danger/10 text-danger', idle: 'bg-ink/8 text-ink/70' }

const Nhan = ({ children }: { children: string }) => <h3 className="mb-2 text-[11px] font-bold uppercase tracking-wider text-ink/55">{children}</h3>

function VatTu({ ct }: { ct: ViTriCotChiTiet }) {
  return (
    <div className="space-y-3">
      {ct.vatTu.map((v) => (
        <div key={v.ten}>
          <div className="flex items-baseline justify-between gap-2 text-sm"><span>{v.ten}</span>
            <span className="num font-semibold">{nf(v.daCap)} / {nf(v.dinhMuc)} {v.dvt}</span></div>
          <div className="mt-1"><Bar value={v.daCap} max={v.dinhMuc} tone={v.daCap >= v.dinhMuc ? 'brand' : 'warn'} /></div>
        </div>))}
      {ct.vatTu.length === 0 && <p className="text-sm text-ink/60">Vị trí này chưa có định mức vật tư.</p>}
      {ct.nhacVatTu && <p className="text-xs font-medium text-[#8a5a00]">Nhắc R10: {ct.nhacVatTu.charAt(0).toLowerCase() + ct.nhacVatTu.slice(1)}</p>}
    </div>
  )
}

function Anh({ id, tong }: { id: string; tong: number }) {
  const [d, setD] = useState<AnhViTri | null>(null), [urls, setUrls] = useState<string[]>([]), [err, setErr] = useState('')
  useEffect(() => {
    let ok = true
    const tao: string[] = []
    getAnhViTri(id).then(async (r) => {
      for (const a of r.tep.slice(0, 24)) tao.push(await layAnhBlobUrl(a.id))
      if (ok) { setD(r); setUrls(tao) }
    }).catch((e) => ok && setErr(lamLoi(e, 'Không tải được ảnh')))
    return () => { ok = false; tao.forEach((u) => URL.revokeObjectURL(u)) }
  }, [id])
  if (err) return <Alert>{err}</Alert>
  if (!d) return <Loading />
  const cho = Math.max(0, d.khaiBao)
  return (
    <div>
      <p className="mb-2 text-xs text-ink/60">{tong} ảnh trong nhật ký thi công{cho > 0 ? ` (${cho} ảnh mới chỉ khai báo số lượng, chưa có tệp trong kho)` : ''}.</p>
      <div className="grid grid-cols-3 gap-1.5">
        {urls.map((u) => <a key={u} href={u} target="_blank" rel="noreferrer"><img src={u} alt="Ảnh hiện trường" className="aspect-square w-full rounded-md object-cover" /></a>)}
        {Array.from({ length: Math.min(cho, 18) }, (_, i) => (
          <div key={i} className="aspect-square rounded-md bg-[repeating-linear-gradient(135deg,#e3e6df,#e3e6df_6px,#eef0ea_6px,#eef0ea_12px)]" aria-label="Ảnh chưa có tệp" />))}
      </div>
    </div>
  )
}

export default function PanelViTri({ id, tuyenTen, onXemHoSo }: { id: string; tuyenTen?: string; onXemHoSo?: () => void }) {
  const nav = useNavigate()
  const [ct, setCt] = useState<ViTriCotChiTiet | null>(null), [err, setErr] = useState('')
  const [tab, setTab] = useState<Tab>('tong-quan')
  const [idCu, setIdCu] = useState(id)
  if (id !== idCu) { setIdCu(id); setCt(null); setErr(''); setTab('tong-quan') }
  useEffect(() => {
    let ok = true
    getViTriCot(id).then((r) => ok && setCt(r), (e) => ok && setErr(lamLoi(e, 'Không tải được chi tiết vị trí')))
    return () => { ok = false }
  }, [id])
  if (err) return <div className="p-4"><Alert>{err}</Alert></div>
  if (!ct) return <Loading />
  const so = ct.ten.replace('VT', '')
  const TENTAB: Record<Tab, string> = { 'tong-quan': 'Tổng quan', 'vat-tu': 'Vật tư', 'ho-so': `Hồ sơ (${ct.hoSo.dat}/${ct.hoSo.tong})`, anh: `Ảnh (${ct.anh.tong})` }
  const tk = ct.thietKe
  const o = (k: string, v: string | null) => (
    <div><div className="text-xs text-ink/50">{k}</div><div className="num mt-0.5 break-words text-[13px] font-medium">{v ?? '—'}</div></div>)

  return (
    <div className="flex flex-col">
      <div className="p-5 pb-3">
        <div className="text-xs text-ink/55">{(ct.tuyen?.ten ?? tuyenTen ?? '').split(' · ')[0]} / {ct.doan}</div>
        <h2 className="mt-1 text-2xl font-bold leading-tight">Vị trí {so}{ct.kieuCot && <span className="ml-2 text-sm font-normal text-ink/60">{ct.kieuCot} · {ct.kmText}</span>}</h2>
        <div className="mt-2 flex flex-wrap gap-1.5">{ct.chips.map((c) => <span key={c.text} className={clsx('rounded-full px-2.5 py-0.5 text-xs font-semibold', toneChip[c.tone])}>{c.text}</span>)}</div>
      </div>
      <div role="tablist" className="flex border-b border-ink/10 px-5 text-sm">
        {TAB.map((k) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={clsx('-mb-px min-h-[44px] border-b-2 px-3 font-semibold', tab === k ? 'border-brand text-brand' : 'border-transparent text-ink/55')}>{TENTAB[k]}</button>))}
      </div>
      <div className="space-y-5 p-5">
        {tab === 'tong-quan' && <>
          {ct.canhBao.map((c) => (
            <div key={c.ma + c.thongBao} role="alert" className={clsx('flex gap-2.5 rounded-lg border p-3 text-sm', c.muc === 'Chặn' ? 'border-danger/30 bg-danger/10' : 'border-amber2/40 bg-amber2/15')}>
              <AlertTriangle size={18} className={clsx('mt-0.5 shrink-0', c.muc === 'Chặn' ? 'text-danger' : 'text-amber2')} />
              <p><b className="num">{c.ma} · </b>{c.thongBao}{c.chiTiet && <span className="block text-xs text-ink/65">{c.chiTiet}</span>}</p>
            </div>))}
          <section>
            <Nhan>Thiết kế</Nhan>
            <div className="grid grid-cols-2 gap-x-4 gap-y-3">
              {o('Cột', tk.cot ? `${tk.cot}${tk.cotNpc ? ` (${tk.cotNpc})` : ''}` : null)}{o('Móng', tk.mong)}
              {o('Xà', tk.xa)}{o('Tiếp địa', tk.tiepDia)}{o('Cấp đất · K', tk.capDat)}{o('Khoảng cách trước / sau', tk.khoangCach)}
            </div>
          </section>
          <section>
            <div className="mb-2 flex items-center justify-between"><h3 className="text-[11px] font-bold uppercase tracking-wider text-ink/55">Chiết tính móng</h3>
              <button className="text-xs font-semibold text-brand underline" onClick={() => xuatChietTinhViTri(ct.id).catch((e) => setErr(lamLoi(e)))}>Xuất bảng chiết tính</button></div>
            <div className="grid grid-cols-3 gap-2">
              {[['Đào đất', `${nfCoDinh(ct.chietTinh.daoDat, 1)} m³`], ['Diện tích miệng', `${nfCoDinh(ct.chietTinh.dienTichMieng, 1)} m²`], ['Diện tích đáy', `${nfCoDinh(ct.chietTinh.dienTichDay, 1)} m²`]].map(([k, v]) => (
                <div key={k} className="rounded-lg bg-paper p-2.5"><div className="text-[11px] text-ink/55">{k}</div><div className="num mt-0.5 text-[15px] font-bold">{v}</div></div>))}
            </div>
            <p className="mt-1.5 text-[11px] text-ink/55">{ct.chietTinh.ghiChu}. Khối lượng tính theo công thức hình chóp cụt.</p>
          </section>
          <section>
            <Nhan>Lịch sử thi công</Nhan>
            <ol className="space-y-3">
              {ct.lichSu.map((r) => (
                <li key={r.ma} className="flex gap-3">
                  <span className={clsx('mt-1 grid size-4 shrink-0 place-items-center rounded-full border-2',
                    r.trangThai === 'xong' ? 'border-brand bg-brand text-white' : r.trangThai === 'dang' ? 'border-amber2 bg-white' : 'border-ink/25 bg-white')}>
                    {r.trangThai === 'xong' && <Check size={9} strokeWidth={4} />}</span>
                  <div className="min-w-0 flex-1"><div className="text-sm font-semibold leading-snug">{r.ten}</div>
                    {r.ghiChu && <div className="text-xs text-ink/60">{r.ghiChu}</div>}</div>
                  <div className="num shrink-0 text-right text-xs"><div className="text-ink/55">{r.ngay ?? ''}</div>
                    <div className={clsx('font-semibold', r.trangThai === 'xong' ? 'text-brand' : r.trangThai === 'dang' ? 'text-[#8a5a00]' : 'text-ink/35')}>{r.nhan}</div></div>
                </li>))}
            </ol>
          </section>
          <section><Nhan>Vật tư theo định mức</Nhan><VatTu ct={ct} /></section>
          <div className="grid grid-cols-2 gap-2 pt-1">
            <button className="btn-primary" onClick={() => nav('/de-xuat')}>Đề xuất vật tư</button>
            <button className="btn-ghost" onClick={() => { setTab('ho-so'); onXemHoSo?.() }}>Xem hồ sơ vị trí</button>
          </div>
        </>}
        {tab === 'vat-tu' && <VatTu ct={ct} />}
        {tab === 'ho-so' && (
          <ul className="space-y-2">
            {ct.hoSo.muc.map((m) => (
              <li key={m.ten} className="flex items-center gap-2.5 text-sm">
                <span className={clsx('grid size-5 place-items-center rounded-full', m.ok ? 'bg-brand text-white' : 'border border-ink/25 text-transparent')}>{m.ok ? <Check size={12} strokeWidth={3} /> : <Circle size={4} />}</span>
                <span className={m.ok ? '' : 'text-ink/60'}>{m.ten}</span></li>))}
          </ul>
        )}
        {tab === 'anh' && <Anh id={ct.id} tong={ct.anh.tong} />}
      </div>
    </div>
  )
}
