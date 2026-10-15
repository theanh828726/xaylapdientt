import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Check, Clock, FileDown, Lock } from 'lucide-react'
import clsx from 'clsx'
import { duyetBuoc, inDeXuat, listDeXuatVatTu } from '../api'
import { useRole } from '../lib/role'
import { dm, gio, homNay, lamLoi, nf, vnd } from '../lib/fmt'
import { Alert, Badge, Empty, Loading, PageHeader } from '../components/ui'
import type { BuocDuyet, DeXuatVatTu } from '../types'

const TT = { cho_duyet: ['warn', 'Đang chờ duyệt'], da_duyet: ['ok', 'Đã duyệt'], tu_choi: ['bad', 'Đã trả lại'] } as const

function ThoiGian({ b, dau }: { b: BuocDuyet; dau: boolean }) {
  if (!b.thoiGianIso) return null
  const cungNgay = b.thoiGianIso.slice(0, 10) === homNay()
  const t = cungNgay ? gio(b.thoiGianIso) : `${dm(b.thoiGianIso)} ${gio(b.thoiGianIso)}`
  return <>{b.trangThai === 'tu_choi' ? 'trả lại' : dau ? 'gửi' : 'duyệt'} {t}</>
}

function LuongDuyet({ d }: { d: DeXuatVatTu }) {
  return (
    <section className="card p-5" aria-label="Luồng duyệt">
      <h2 className="mb-4 font-semibold">Luồng duyệt</h2>
      <ol className="space-y-4">
        {d.chuoiDuyet.map((b, i) => {
          const hienTai = b.trangThai === 'dang'
          const ten = b.vaiTroMa === 'ky_thuat' ? 'Kỹ thuật hiện trường' : b.vaiTro
          return (
            <li key={b.vaiTroMa} className="flex gap-3">
              <span className={clsx('grid size-6 shrink-0 place-items-center rounded-full border-2',
                b.trangThai === 'xong' ? 'border-brand bg-brand text-white' : hienTai ? 'border-amber2 bg-white text-amber2' : b.trangThai === 'tu_choi' ? 'border-danger bg-danger text-white' : 'border-ink/25 bg-white')}>
                {b.trangThai === 'xong' ? <Check size={13} strokeWidth={3} /> : hienTai ? <Clock size={12} strokeWidth={3} /> : null}</span>
              <div className="min-w-0 text-sm">
                <div className="font-semibold">{ten}{hienTai && d.coTheDuyet && <span className="text-[#8a5a00]"> · bạn</span>}</div>
                {b.trangThai === 'xong' || b.trangThai === 'tu_choi'
                  ? <div className="text-ink/60">{b.nguoi} · <ThoiGian b={b} dau={i === 0} />{b.lyDo && <span> · “{b.lyDo}”</span>}</div>
                  : <div className={clsx(hienTai ? 'text-[#8a5a00]' : 'text-ink/55')}>{hienTai && !d.coTheDuyet && <>{b.nguoi} · </>}{b.goiY}</div>}
              </div>
            </li>)
        })}
      </ol>
    </section>
  )
}

function YKien({ d, xong }: { d: DeXuatVatTu; xong: () => void }) {
  const [gc, setGc] = useState(''), [busy, setBusy] = useState(''), [loi, setLoi] = useState('')
  const lam = async (q: 'duyet' | 'tu_choi') => {
    setBusy(q); setLoi('')
    try { await duyetBuoc('de_xuat', d.id, q, gc.trim() || undefined); xong() } catch (e) { setLoi(lamLoi(e)) } finally { setBusy('') }
  }
  if (!d.coTheDuyet) return (
    <section className="card p-5"><h2 className="mb-2 font-semibold">Ý kiến của bạn</h2>
      <p className="text-sm text-ink/60">{d.trangThai === 'cho_duyet' ? `Chưa đến lượt bạn duyệt (${d.buocHienTai}).` : `Hồ sơ đã ${d.trangThai === 'da_duyet' ? 'được duyệt xong' : 'bị trả lại'}.`}</p></section>)
  return (
    <section className="card p-5" aria-label="Ý kiến của bạn">
      <h2 className="mb-3 font-semibold">Ý kiến của bạn</h2>
      {d.lyDoVuot && <p className="mb-3 rounded-lg bg-danger/10 p-3 text-sm"><b>Lý do vượt định mức (kỹ thuật):</b> {d.lyDoVuot}</p>}
      <label className="block text-xs text-ink/55">Ghi chú duyệt
        <textarea value={gc} onChange={(e) => setGc(e.target.value)} rows={3} maxLength={2000} className="mt-1 w-full rounded-lg border border-ink/15 p-3 text-sm text-ink" /></label>
      {loi && <div className="mt-2"><Alert>{loi}</Alert></div>}
      <div className="mt-3 space-y-2">
        <button className="btn-ghost w-full" disabled={!!busy || !gc.trim()} title={!gc.trim() ? 'Trả lại cần ghi rõ lý do vào ô ghi chú' : undefined} onClick={() => lam('tu_choi')}>Trả lại</button>
        <button className="btn-primary w-full" disabled={!!busy} onClick={() => lam('duyet')}>{busy === 'duyet' ? 'Đang duyệt…' : d.vaiTroTiep ? `Duyệt, chuyển ${d.vaiTroTiep}` : 'Duyệt (bước cuối)'}</button>
      </div>
    </section>
  )
}

function ChiTiet({ d, lamMoi }: { d: DeXuatVatTu; lamMoi: () => void }) {
  const { thayGia, thayGiaKhoan } = useRole()
  const [loi, setLoi] = useState('')
  const soViTri = (() => { const m = /(\d+)\D+(\d+)/.exec(d.doan ?? ''); return m ? Number(m[2]) - Number(m[1]) + 1 : null })()
  const [tt, nhan] = TT[d.trangThai]
  return (
    <>
      <PageHeader eyebrow={<><Link to="/de-xuat" className="font-semibold text-brand underline">Đề xuất vật tư</Link> / <span className="num">{d.ma}</span></>}
        title={`Đề xuất vật tư · ${d.doan ?? d.ma}`}
        actions={<>
          {d.trangThai === 'cho_duyet' ? <Badge tone="warn" className="px-3 py-1 text-sm">{d.coTheDuyet ? `Chờ bạn duyệt · ${d.buocHienTai?.split('– ')[1]}` : d.buocHienTai}</Badge> : <Badge tone={tt} className="px-3 py-1 text-sm">{nhan}</Badge>}
          <button className="btn-ghost" onClick={() => inDeXuat(d.id).catch((e) => setLoi(lamLoi(e)))}><FileDown size={16} />Xuất phiếu .docx</button></>} />
      <p className="-mt-3 mb-4 flex flex-wrap gap-x-5 gap-y-1 text-sm text-ink/70">
        <span>Người lập: <b className="text-ink">{d.nguoiLap.replace('Kỹ thuật –', 'KT.')}</b></span>
        {d.canHang && <span>Cần hàng: <b className="num text-ink">{dm(d.canHang, true)}</b></span>}
        {d.giaoTai && <span>Giao tại: <b className="text-ink">{d.giaoTai}</b></span>}
        <span>Lần đề xuất thứ <b className="text-ink">{d.lanDeXuat}</b> cho đoạn này</span></p>
      {loi && <div className="mb-3"><Alert>{loi}</Alert></div>}
      <div className="grid items-start gap-4 xl:grid-cols-[1fr_340px]">
        <section className="card overflow-hidden" aria-label="Danh mục vật tư">
          <div className="flex flex-wrap items-baseline justify-between gap-2 p-4">
            <h2 className="font-semibold">{d.dong.length} dòng vật tư <span className="ml-2 text-xs font-normal text-ink/55">{soViTri ? `Định mức tính từ thư viện mã cấu kiện của ${soViTri} vị trí` : ''}</span></h2>
            <span className="flex items-center gap-1.5 text-xs text-ink/55">
              {thayGia || thayGiaKhoan
                ? <>{thayGiaKhoan && d.giaKhoan != null && <>Giá khoán <b className="num text-ink">{vnd(d.giaKhoan)}</b></>}{thayGia && d.giaHopDong != null && <> · Giá hợp đồng <b className="num text-ink">{vnd(d.giaHopDong)}</b></>}</>
                : <><Lock size={13} />Đơn giá ẩn với vai trò của bạn</>}</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px] text-sm">
              <thead><tr className="bg-paper text-left text-xs font-semibold text-ink/65">
                <th className="px-4 py-3">Vật tư</th><th>ĐVT</th><th className="text-right">Định mức TK</th><th className="text-right">Đã đề xuất</th>
                <th className="text-right">Còn lại</th><th className="text-right">Tồn kho CT</th><th className="text-right">Lần này</th><th className="pl-5 pr-4">Quy đổi để mua</th></tr></thead>
              <tbody>
                {d.dong.map((r) => (
                  <tr key={r.ten} className={clsx('border-t border-ink/8 align-top', r.canhBao && 'bg-danger/[0.06]')}>
                    <td className="px-4 py-3"><div className="font-semibold">{r.ten}</div>{r.moTa && <div className="num text-xs text-ink/55">{r.moTa}</div>}</td>
                    <td className="py-3">{r.dvt}</td>
                    <td className="num py-3 text-right">{nf(r.theoDinhMuc)}</td><td className="num py-3 text-right">{nf(r.daDeXuat)}</td><td className="num py-3 text-right">{nf(r.conLai)}</td>
                    <td className="num py-3 text-right">{r.tonKho == null ? '–' : nf(r.tonKho)}</td>
                    <td className={clsx('num py-3 text-right font-bold', r.canhBao && 'text-danger')}>{nf(r.deXuat)}</td>
                    <td className="py-3 pl-5 pr-4 text-xs leading-relaxed">{(r.quyDoi ?? '').split('\n').map((l, i) => <div key={i} className={i === 0 ? 'text-[13px]' : 'text-brand'}>{l}</div>)}
                      {r.canhBao && <div className="font-semibold text-danger">{r.canhBao}</div>}</td>
                  </tr>))}
              </tbody>
            </table>
          </div>
          {d.doiChieu.tong > 0 && (
            <p className="border-t border-ink/8 bg-paper p-4 text-sm"><b>Đối chiếu hợp đồng:</b> {d.doiChieu.khop}/{d.doiChieu.tong} dòng khớp phụ lục khối lượng.{d.doiChieu.ghiChu && <> {d.doiChieu.ghiChu} — <Link to="/doi-soat" className="font-semibold text-brand underline">xem đối soát</Link>.</>}</p>)}
        </section>
        <div className="space-y-4"><LuongDuyet d={d} /><YKien d={d} xong={lamMoi} /></div>
      </div>
    </>
  )
}

export default function DeXuat() {
  const { ma } = useParams()
  const nav = useNavigate()
  const [ds, setDs] = useState<DeXuatVatTu[] | null>(null), [loi, setLoi] = useState('')
  const tai = useCallback(() => { listDeXuatVatTu().then(setDs, (e) => setLoi(lamLoi(e))) }, [])
  useEffect(() => { tai() }, [tai])
  if (loi) return <Alert>{loi}</Alert>
  if (!ds) return <Loading />
  if (ma) {
    const d = ds.find((x) => x.ma === decodeURIComponent(ma))
    return d ? <ChiTiet d={d} lamMoi={tai} /> : <Empty>Không tìm thấy đề xuất {decodeURIComponent(ma)}.</Empty>
  }
  return (
    <>
      <PageHeader title="Đề xuất vật tư" sub={`${ds.length} đề xuất của dự án`} />
      {ds.length === 0 ? <Empty>Dự án này chưa có đề xuất vật tư nào.</Empty> : (
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead><tr className="bg-paper text-left text-xs font-semibold text-ink/65"><th className="px-4 py-3">Mã</th><th>Đoạn</th><th>Người lập</th><th>Cần hàng</th><th className="text-right">Số dòng</th><th className="pl-5">Trạng thái</th></tr></thead>
            <tbody>
              {ds.map((d) => (
                <tr key={d.id} tabIndex={0} onClick={() => nav(`/de-xuat/${d.ma}`)} onKeyDown={(e) => e.key === 'Enter' && nav(`/de-xuat/${d.ma}`)}
                  className="cursor-pointer border-t border-ink/8 hover:bg-brand-soft/40 focus:bg-brand-soft/40 focus:outline-none">
                  <td className="num px-4 py-3 font-semibold text-brand">{d.ma}</td><td>{d.doan ?? '—'}</td><td>{d.nguoiLapTen}</td>
                  <td className="num">{dm(d.canHang, true)}</td><td className="num text-right">{d.dong.length}</td>
                  <td className="py-3 pl-5">{d.trangThai === 'cho_duyet'
                    ? <Badge tone={d.coTheDuyet ? 'warn' : 'info'}>{d.coTheDuyet ? 'Chờ bạn duyệt' : d.buocHienTai}</Badge> : <Badge tone={TT[d.trangThai][0]}>{TT[d.trangThai][1]}</Badge>}</td>
                </tr>))}
            </tbody>
          </table>
        </div>)}
    </>
  )
}
