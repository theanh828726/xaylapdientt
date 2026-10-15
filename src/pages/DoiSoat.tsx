import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import clsx from 'clsx'
import { getHangMucDoiSoat, listHangMucDoiSoat, taoPhieuDoiSoat, xacNhanDoiSoat } from '../api'
import { useRole } from '../lib/role'
import { lamLoi } from '../lib/fmt'
import { Alert, Empty, Loading, PageHeader } from '../components/ui'
import { SidebarPortal } from '../components/Layout'
import type { DoiSoatDong, DoiSoatHangMuc, DoiSoatHangMucTom } from '../types'

const KL = {
  lech: 'bg-danger text-white', khop: 'bg-brand-soft text-brand', thieu_hd: 'bg-amber2/25 text-[#8a5a00]',
  thieu_bv: 'bg-amber2/25 text-[#8a5a00]', thieu_cd: 'bg-amber2/25 text-[#8a5a00]',
} as const

function Cot({ gia, trich }: { gia: string; trich?: string }) {
  return <td className="px-3 py-3 align-top"><div className="font-semibold">{gia}</div>{trich && <div className="text-xs text-ink/55">{trich}</div>}</td>
}

function BangChung({ r }: { r: DoiSoatDong }) {
  return (
    <section className="card p-5" aria-label="Bằng chứng">
      <div className="mb-3 flex flex-wrap items-baseline gap-x-3"><h2 className="font-semibold">Bằng chứng · {r.thongSo}</h2>
        <span className="text-xs text-ink/55">Vùng AI đọc được khoanh trên tài liệu gốc</span></div>
      {r.bangChung.length === 0
        ? <p className="text-sm text-ink/60">Dòng này chưa có vùng bằng chứng trên tài liệu gốc (cần AI trích xuất tài liệu).</p>
        : <div className="grid gap-4 md:grid-cols-2">
          {r.bangChung.map((b) => (
            <figure key={b.nhan}>
              <div className="relative h-44 overflow-hidden rounded-lg border border-ink/10 bg-[repeating-linear-gradient(135deg,#e6e9e2,#e6e9e2_8px,#f1f3ee_8px,#f1f3ee_16px)]">
                <span className="num absolute left-2 top-1.5 text-[11px] text-ink/60">{b.nhan}</span>
                <div className={clsx('absolute rounded border-2', b.tone === 'bad' ? 'border-danger bg-danger/10' : 'border-brand bg-brand/10')}
                  style={{ left: `${b.bbox.x * 100}%`, top: `${b.bbox.y * 100}%`, width: `${b.bbox.w * 100}%`, height: `${b.bbox.h * 100}%` }} aria-label={`Vùng ${b.nguon}`} />
              </div>
              <figcaption className="mt-1.5 text-sm text-ink/70">{b.chu_thich}</figcaption>
            </figure>))}
        </div>}
    </section>
  )
}

export default function DoiSoat() {
  const { can } = useRole()
  const [sp, setSp] = useSearchParams()
  const [ds, setDs] = useState<DoiSoatHangMucTom[] | null>(null), [hm, setHm] = useState<DoiSoatHangMuc | null>(null)
  const [dong, setDong] = useState(''), [loi, setLoi] = useState(''), [msg, setMsg] = useState(''), [busy, setBusy] = useState('')
  const chonId = sp.get('hm') ?? ds?.find((h) => h.soCanXuLy > 0)?.id ?? ds?.[0]?.id

  const taiDs = useCallback(() => { listHangMucDoiSoat().then(setDs, (e) => setLoi(lamLoi(e))) }, [])
  const taiHm = useCallback((id: string) => { getHangMucDoiSoat(id).then(setHm, (e) => setLoi(lamLoi(e))) }, [])
  useEffect(() => { taiDs() }, [taiDs])
  useEffect(() => { if (chonId) taiHm(chonId) }, [chonId, taiHm])

  const lam = async (r: DoiSoatDong) => {
    setBusy(r.id); setLoi(''); setMsg('')
    try {
      if (r.hanhDong === 'xac_nhan') { await xacNhanDoiSoat(r.id, 'chap_nhan'); setMsg(`Đã xác nhận “${r.thongSo}”.`) }
      else { const k = await taoPhieuDoiSoat(r.id); setMsg(`Đã mở phiếu ${k.phieu?.ma} cho “${r.thongSo}”, chuyển vào luồng phê duyệt.`) }
      taiDs(); if (chonId) taiHm(chonId)
    } catch (e) { setLoi(lamLoi(e)) } finally { setBusy('') }
  }

  const sidebar = (
    <SidebarPortal>
      <div className="p-3">
        <Link to="/ban-do" className="mb-4 flex min-h-[40px] items-center px-2 text-sm font-semibold text-brand">← Về bản đồ tuyến</Link>
        <div className="mb-1.5 px-2 text-[11px] font-bold uppercase tracking-wider text-ink/50">Hạng mục · {ds?.length ?? 0}</div>
        <ul className="space-y-1">
          {ds?.map((h) => (
            <li key={h.id}><button onClick={() => { setSp({ hm: h.id }, { replace: true }); setDong(''); setMsg('') }} aria-current={h.id === chonId}
              className={clsx('flex min-h-[42px] w-full items-center gap-2 rounded-lg px-3 text-left text-sm font-medium', h.id === chonId ? 'bg-brand-soft text-brand' : 'text-ink/75 hover:bg-ink/5')}>
              <span className="flex-1">{h.ten}</span>
              {h.soCanXuLy > 0 ? <span className="num rounded-full bg-danger px-2 py-0.5 text-[11px] font-bold text-white">{h.soCanXuLy}</span> : <span className="text-xs font-semibold text-brand">Khớp</span>}
            </button></li>))}
        </ul>
      </div>
    </SidebarPortal>
  )

  if (loi && !hm) return <>{sidebar}<Alert>{loi}</Alert></>
  if (!ds) return <>{sidebar}<Loading /></>
  if (ds.length === 0) return <>{sidebar}<Empty>Dự án này chưa có dữ liệu đối soát.</Empty></>
  if (!hm || hm.id !== chonId) return <>{sidebar}<Loading /></>
  const hang = dong ? hm.rows.find((r) => r.id === dong) : hm.rows.find((r) => r.ketLuan === 'lech') ?? hm.rows[0]

  return (
    <>
      {sidebar}
      <PageHeader eyebrow="Đối soát Hợp đồng – Bản vẽ – Chỉ dẫn kỹ thuật" title={hm.tieuDe}
        actions={<button className="btn-ghost" disabled title="Cần AI service đọc PDF/OCR (chưa triển khai)">Chạy lại AI trích xuất</button>} />
      {loi && <div className="mb-3"><Alert>{loi}</Alert></div>}
      {msg && <div className="mb-3"><Alert tone="ok">{msg}</Alert></div>}
      <div className="mb-4 grid gap-3 md:grid-cols-3">
        {hm.nguon.map((n) => (
          <div key={n.nhan} className="card p-4"><div className="text-[11px] font-bold uppercase tracking-wider text-ink/50">{n.nhan}</div>
            <div className="mt-1 font-semibold leading-snug">{n.ten}</div><div className="mt-0.5 text-xs text-ink/55">{n.mo_ta}</div></div>))}
      </div>
      <section className="card mb-4 overflow-hidden" aria-label="Các thông số đối soát">
        <div className="flex flex-wrap items-baseline gap-x-3 p-4"><h2 className="font-semibold">
          {hm.soThongSo} thông số{hm.soLech > 0 && ` · ${hm.soLech} lệch`}{hm.soThieu > 0 && ` · ${hm.soThieu} thiếu trong hợp đồng`}</h2>
          <span className="text-xs text-ink/55">AI đề xuất, người duyệt xác nhận từng dòng</span></div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-sm">
            <thead><tr className="bg-paper text-left text-xs font-semibold text-ink/65"><th className="px-4 py-3">Thông số</th><th>Hợp đồng</th><th>Bản vẽ / bảng kê</th><th>Chỉ dẫn KT</th><th>Kết luận</th><th className="pr-4" /></tr></thead>
            <tbody>
              {hm.rows.map((r) => {
                const quyen = r.hanhDong === 'xac_nhan' ? can('doi_soat.xac_nhan') : can('doi_soat.xac_nhan') && can('de_xuat.lap')
                const nut = r.hanhDong === 'tao_phieu' ? 'Tạo phiếu xử lý' : r.hanhDong === 'phat_sinh' ? 'Lập phát sinh' : 'Xác nhận'
                return (
                  <tr key={r.id} onClick={() => setDong(r.id)} className={clsx('cursor-pointer border-t border-ink/8', r.ketLuan === 'lech' ? 'bg-danger/[0.05]' : r.ketLuan.startsWith('thieu') ? 'bg-amber2/[0.10]' : '', hang?.id === r.id && 'outline outline-2 -outline-offset-2 outline-brand/40')}>
                    <td className="px-4 py-3 align-top font-semibold">{r.thongSo}</td>
                    <Cot gia={r.hopDong} trich={r.trichDan.hd} /><Cot gia={r.banVe} trich={r.trichDan.bv} /><Cot gia={r.chiDan} trich={r.trichDan.cd} />
                    <td className="px-3 py-3 align-top"><span className={clsx('rounded-md px-2 py-0.5 text-xs font-bold', KL[r.ketLuan])}>{r.ketLuanTen}</span>
                      <div className="mt-1 text-xs text-ink/55">{r.tinCay != null ? `Tin cậy ${r.tinCay.toLocaleString('vi-VN', { minimumFractionDigits: 2 })}` : r.aiDeXuat.split(':')[0]}</div></td>
                    <td className="py-3 pr-4 text-right align-top">
                      {r.quyetDinh
                        ? <span className="text-xs font-semibold text-brand">{r.quyetDinh === 'da_tao_phieu' ? <>Đã mở phiếu <Link to="/duyet" className="underline">{r.phieu?.ma}</Link></> : 'Đã xác nhận'}</span>
                        : <button className={r.hanhDong === 'tao_phieu' ? 'btn-primary' : 'btn-ghost'} disabled={!quyen || busy === r.id} title={!quyen ? 'Vai trò của bạn không có quyền thực hiện' : undefined}
                          onClick={(e) => { e.stopPropagation(); lam(r) }}>{busy === r.id ? 'Đang xử lý…' : nut}</button>}
                    </td>
                  </tr>)
              })}
            </tbody>
          </table>
        </div>
        {hang && <p className="border-t border-ink/8 bg-brand-soft/50 p-3 text-sm"><b className="text-brand">AI đề xuất · {hang.thongSo}:</b> {hang.aiDeXuat}</p>}
      </section>
      {hang && <BangChung r={hang} />}
    </>
  )
}
