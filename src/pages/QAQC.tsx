import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import {
  ganKetQua, getLichNen, getQaqc, listMauBieu, listTuyen, moPhieuDieuChinh, nhacKyThuat, sinhBienBanHangLoat, sinhChietTinh, soanDeTrinh,
  xemTruocBienBan,
} from '../api'
import { useRole } from '../lib/role'
import { dm, homNay, lamLoi, vtHien } from '../lib/fmt'
import { Alert, Bar, Loading, Modal, PageHeader, RuleChip } from '../components/ui'
import type { LichNen, MauBieuInfo, Nhom, OMaTran, QaqcTongQuan, Tuyen, ViPham, XemTruoc } from '../types'

const NHOM: [Nhom, string][] = [['PL1', 'Phần móng · PL1'], ['PL2', 'Cột + dây · PL2'], ['PL3', 'Cắt – đóng điện · PL3'], ['PL4', 'Thanh toán · PL4']]
const lui = (iso: string, n: number) => { const d = new Date(iso); d.setDate(d.getDate() - n); return d.toLocaleDateString('sv-SE') }

function Stat({ nhan, children, sub, loi }: { nhan: string; children: React.ReactNode; sub?: React.ReactNode; loi?: boolean }) {
  return (
    <div className={clsx('card p-4', loi && 'border-danger/50')}>
      <div className={clsx('text-xs', loi ? 'font-semibold text-danger' : 'text-ink/55')}>{nhan}</div>
      <div className={clsx('num mt-1 text-[28px] font-semibold leading-none', loi && 'text-danger')}>{children}</div>
      {sub && <div className="mt-2 text-xs text-ink/55">{sub}</div>}
    </div>
  )
}

const O = ({ o, onClick }: { o: OMaTran | null; onClick: () => void }) => {
  if (!o) return <div className="h-8 rounded bg-ink/5" />
  const cls = o.state === 'nt' ? 'bg-brand text-white'
    : o.state === 'cho' || o.state === 'dang' ? 'border border-brand/40 bg-brand-soft text-brand'
      : o.state === 'thieu' ? 'bg-amber2 text-white' : 'border-2 border-danger bg-white text-danger'
  return (
    <button onClick={onClick} className={clsx('num grid h-8 w-full place-items-center rounded text-[11px] font-bold', cls)}
      aria-label={`${o.state === 'nt' ? 'Đã nghiệm thu' : o.state === 'chan' ? 'Bị chặn' : o.state === 'thieu' ? 'Thiếu hồ sơ' : 'Đã làm, chờ nghiệm thu'}${o.ma ? ' ' + o.ma.join(' ') : ''}`}>
      {o.ma?.join(' ') ?? o.nhan ?? ''}</button>
  )
}

export default function QAQC() {
  const nav = useNavigate()
  const { can } = useRole()
  const [nhom, setNhom] = useState<Nhom>('PL1')
  const [den, setDen] = useState(homNay), [tu, setTu] = useState(() => lui(homNay(), 7))
  const [gop, setGop] = useState<'vi_tri' | 'doan_ngay'>('doan_ngay')
  const [d, setD] = useState<QaqcTongQuan | null>(null), [xt, setXt] = useState<XemTruoc | null>(null)
  const [tuyen, setTuyen] = useState<Tuyen[]>([]), [mau, setMau] = useState<MauBieuInfo | null>(null)
  const [loi, setLoi] = useState(''), [msg, setMsg] = useState(''), [busy, setBusy] = useState('')
  const [modal, setModal] = useState<null | { kieu: 'ket-qua'; v: ViPham } | { kieu: 'lich' } | { kieu: 'xem-truoc' }>(null)

  const tai = useCallback(async () => {
    try {
      const [a, b] = await Promise.all([getQaqc(nhom, tu, den), xemTruocBienBan(gop, tu, den)])
      setD(a); setXt(b); setLoi('')
    } catch (e) { setLoi(lamLoi(e, 'Không tải được dữ liệu QA/QC')) }
  }, [nhom, tu, den, gop])
  useEffect(() => { tai() }, [tai])
  useEffect(() => {
    listTuyen().then(setTuyen, () => {})
    listMauBieu().then((m) => setMau(m.find((x) => x.loai === 'nghiem_thu_cong_viec') ?? null), () => {})
  }, [])

  const chay = async (khoa: string, viec: () => Promise<string | void>) => {
    setBusy(khoa); setMsg(''); setLoi('')
    try { const m = await viec(); if (m) setMsg(m); await tai() } catch (e) { setLoi(lamLoi(e)) } finally { setBusy('') }
  }
  const xl = can('nghiem_thu.xu_ly'), lap = can('de_xuat.lap')

  const hanhDong = (v: ViPham): { nhan: string; chay: () => void; khoa?: boolean } | null => {
    const k = `${v.ma}-${v.doiTuongId}`
    switch (v.hanhDong) {
      case 'gan_ket_qua': return { nhan: 'Gắn kết quả', khoa: !xl, chay: () => setModal({ kieu: 'ket-qua', v }) }
      case 'soan_de_trinh': return { nhan: 'Soạn đề trình', khoa: !xl, chay: () => chay(k, async () => { await soanDeTrinh(v.doiTuongId); return 'Đã soạn đề trình (.docx) và tải về máy.' }) }
      case 'mo_phieu_dieu_chinh': return { nhan: 'Mở phiếu điều chỉnh', khoa: !lap, chay: () => chay(k, async () => `Đã mở phiếu ${(await moPhieuDieuChinh(v.doiTuongId)).ma}, chuyển vào luồng phê duyệt.`) }
      case 'sinh_chiet_tinh': return { nhan: 'Sinh chiết tính', khoa: !xl, chay: () => chay(k, async () => { await sinhChietTinh(); return 'Đã sinh bảng chiết tính (.docx) và ghi nhận kèm biên bản đào móng.' }) }
      case 'nhac_ky_thuat': return { nhan: 'Nhắc kỹ thuật', khoa: !xl, chay: () => chay(k, async () => (await nhacKyThuat(v.doiTuongId)).message) }
      case 'xem_lich': return { nhan: 'Xem lịch', chay: () => setModal({ kieu: 'lich' }) }
      case 'xem_phieu': return { nhan: 'Xem phiếu', chay: () => nav('/duyet') }
      case 'xem_doi_soat': return { nhan: 'Xem đối soát', chay: () => nav('/doi-soat') }
      case 'xem_de_xuat': return { nhan: 'Xem đề xuất', chay: () => nav('/de-xuat') }
      case 'xem_vat_tu': return { nhan: 'Xem vị trí', chay: () => nav('/ban-do') }
      default: return null
    }
  }

  if (!d || !xt) return loi ? <Alert>{loi}</Alert> : <Loading />
  const t = d.thongKe
  const t0 = tuyen.find((x) => x.loai === 'moi')
  const biChan = xt.biChan.ds.map((x) => `${x.viTri} · ${x.ma.join(', ')}`).join('; ')

  return (
    <>
      <PageHeader eyebrow={t0 ? `${t0.ten.replace(/(\d+(?:,\d+)?) kV/, 'trung thế $1 kV')} · ${t0.soViTri} vị trí` : undefined} title="Trung tâm kiểm soát hồ sơ"
        actions={<div role="tablist" className="flex flex-wrap gap-1 rounded-xl bg-ink/5 p-1">
          {NHOM.map(([k, ten]) => (
            <button key={k} role="tab" aria-selected={nhom === k} onClick={() => setNhom(k)}
              className={clsx('min-h-[40px] rounded-lg px-3 text-sm font-semibold', nhom === k ? 'bg-white shadow-sm' : 'text-ink/60 hover:text-ink')}>{ten}</button>))}
        </div>} />
      {loi && <div className="mb-3"><Alert>{loi}</Alert></div>}
      {msg && <div className="mb-3"><Alert tone="ok">{msg}</Alert></div>}

      <div className="mb-4 grid grid-cols-2 gap-3 xl:grid-cols-4">
        <Stat nhan="Vị trí đủ hồ sơ phần móng" sub={<Bar value={t.duHoSoMong.du} max={t.duHoSoMong.tong} />}>{t.duHoSoMong.du} <span className="text-base text-ink/50">/ {t.duHoSoMong.tong}</span></Stat>
        <Stat nhan="Biên bản sẵn sàng sinh" sub={`từ báo cáo hiện trường ${dm(d.tu)}–${dm(d.den)}`}>{t.bienBanSanSang.n}</Stat>
        <Stat nhan="Lỗi đang chặn" loi={t.loiChan.n > 0} sub="không sinh được biên bản liên quan">{t.loiChan.n}</Stat>
        <Stat nhan="Mẫu bê tông chờ nén" sub={t.mauChoNen.ganNhat ? `gần nhất: ${t.mauChoNen.ganNhat.tuoi} ngày tuổi, ${dm(t.mauChoNen.ganNhat.ngay)}` : 'không có mẫu chờ'}>{t.mauChoNen.n}</Stat>
      </div>

      <div className="mb-4 grid gap-4 xl:grid-cols-[1fr_380px]">
        <section className="card p-4" aria-label="Kiểm tra logic hồ sơ">
          <div className="mb-3 flex flex-wrap items-baseline gap-x-3"><h2 className="font-semibold">Kiểm tra logic hồ sơ</h2>
            <span className="text-xs text-ink/55">Chạy lại lúc {d.chayLuc} · {d.soQuyTac} quy tắc</span></div>
          {d.kiemTra.length === 0 && <p className="py-6 text-center text-sm text-ink/55">Không có vi phạm hay nhắc việc nào ở nhóm {d.nhomTen}.</p>}
          <ul className="divide-y divide-ink/8">
            {d.kiemTra.map((v) => {
              const h = hanhDong(v)
              const k = `${v.ma}-${v.doiTuongId}`
              return (
                <li key={k} className="flex items-start gap-3 py-3">
                  <RuleChip muc={v.muc} ma={v.ma} />
                  <div className="min-w-0 flex-1 text-sm"><div className="font-semibold leading-snug">{v.ten}</div>
                    {v.chiTiet && <div className="mt-0.5 text-xs text-ink/60">{v.chiTiet}</div>}</div>
                  {h && <button className="btn-ghost shrink-0" disabled={h.khoa || busy === k} title={h.khoa ? 'Vai trò của bạn không có quyền thực hiện' : undefined} onClick={h.chay}>{busy === k ? 'Đang xử lý…' : h.nhan}</button>}
                </li>)
            })}
          </ul>
        </section>

        <section className="card p-4" aria-label="Sinh biên bản nghiệm thu">
          <h2 className="mb-3 font-semibold">Sinh biên bản nghiệm thu</h2>
          <fieldset className="mb-3"><legend className="mb-1.5 text-xs text-ink/55">Cách gộp biên bản</legend>
            <div className="space-y-2">
              {([['vi_tri', 'Từng vị trí', 'Mặc định cho ĐZ cao thế 110–500 kV'], ['doan_ngay', 'Gộp theo đoạn, ngày', 'Mặc định cho ĐZ trung – hạ thế']] as const).map(([k, a, b]) => (
                <label key={k} className={clsx('flex cursor-pointer gap-2.5 rounded-lg border p-3', gop === k ? 'border-brand bg-brand-soft/60' : 'border-ink/15')}>
                  <input type="radio" name="gop" className="mt-1" checked={gop === k} onChange={() => setGop(k)} />
                  <span><b className="block text-sm">{a}</b><span className="text-xs text-ink/60">{b}</span></span></label>))}
            </div></fieldset>
          <div className="mb-3 grid grid-cols-2 gap-2">
            <label className="text-xs text-ink/55">Từ ngày<input type="date" value={tu} max={den} onChange={(e) => e.target.value && setTu(e.target.value)} className="mt-1 w-full rounded-lg border border-ink/15 px-3 min-h-[42px] text-sm text-ink" /></label>
            <label className="text-xs text-ink/55">Đến ngày<input type="date" value={den} min={tu} onChange={(e) => e.target.value && setDen(e.target.value)} className="mt-1 w-full rounded-lg border border-ink/15 px-3 min-h-[42px] text-sm text-ink" /></label>
          </div>
          <label className="mb-3 block text-xs text-ink/55">Bộ mẫu biểu
            <select disabled className="mt-1 w-full rounded-lg border border-ink/15 bg-ink/5 px-3 min-h-[42px] text-sm text-ink">
              <option>{mau ? (mau.nguon === 'du-an' ? `Mẫu của dự án · phiên bản ${mau.phienBan}` : 'Mẫu mặc định của hệ thống') : '—'}</option></select>
            <span className="mt-1 block">Đổi mẫu tại Quản trị → Biểu mẫu.</span></label>
          <dl className="mb-3 space-y-1.5 rounded-lg bg-paper p-3 text-sm">
            {[['Biên bản sẽ tạo', xt.bienBan], ['Kèm giấy mời, chiết tính', `${xt.kemGiayMoi} + ${xt.kemChietTinh}`]].map(([k, v]) => (
              <div key={k} className="flex justify-between"><dt>{k}</dt><dd className="num font-semibold">{v}</dd></div>))}
            <div className="flex justify-between gap-3 text-danger"><dt className="shrink-0">Bị chặn, không tạo</dt><dd className="num text-right font-semibold">{xt.biChan.n}{biChan && ` (${biChan})`}</dd></div>
            <div className="flex justify-between"><dt>Trang nhật ký cập nhật</dt><dd className="num font-semibold">{xt.soNgayNhatKy} ngày</dd></div>
          </dl>
          <div className="grid grid-cols-[1fr_auto] gap-2">
            <button className="btn-primary" disabled={!xl || xt.bienBan === 0 || busy === 'bb'} title={!xl ? 'Vai trò của bạn không có quyền sinh biên bản' : undefined}
              onClick={() => chay('bb', async () => { await sinhBienBanHangLoat(gop, tu, den); return `Đã sinh ${xt.bienBan} biên bản (kèm giấy mời và chiết tính) và tải file ZIP về máy.` })}>
              {busy === 'bb' ? 'Đang sinh…' : `Sinh ${xt.bienBan} biên bản · DOCX`}</button>
            <button className="btn-ghost" onClick={() => setModal({ kieu: 'xem-truoc' })}>Xem trước</button>
          </div>
        </section>
      </div>

      <section className="card p-4" aria-label="Ma trận vị trí × công tác">
        <div className="mb-3 flex flex-wrap items-center gap-x-5 gap-y-2"><h2 className="font-semibold">Ma trận vị trí × công tác</h2>
          <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink/70">
            {[['bg-brand', 'Đã nghiệm thu'], ['border border-brand/40 bg-brand-soft', 'Đã làm, chờ nghiệm thu'], ['bg-amber2', 'Thiếu hồ sơ'], ['border-2 border-danger bg-white', 'Bị chặn']].map(([c, t]) => (
              <li key={t} className="flex items-center gap-1.5"><i className={clsx('size-3 rounded-sm', c)} />{t}</li>))}
          </ul></div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] border-separate border-spacing-x-1 border-spacing-y-1 text-sm">
            <thead><tr><th className="w-16 pb-1 text-left text-xs font-semibold text-ink/55">Vị trí</th>
              {d.maTran.cot.map((c) => <th key={c.ma} className="pb-1 text-center text-xs font-semibold text-ink/55">{c.ten}</th>)}</tr></thead>
            <tbody>
              {d.maTran.rows.map((r) => (
                <tr key={r.id}><td className="num font-semibold">{r.viTriHien}</td>
                  {d.maTran.cot.map((c) => <td key={c.ma}><O o={r.cells[c.ma]} onClick={() => nav(`/ban-do?vt=${r.id}`)} /></td>)}</tr>))}
            </tbody>
          </table>
          {d.maTran.rows.length === 0 && <p className="py-4 text-center text-sm text-ink/55">Chưa có vị trí nào đang thi công hoặc chờ hồ sơ.</p>}
        </div>
      </section>

      {modal?.kieu === 'ket-qua' && <KetQuaModal v={modal.v} onClose={() => setModal(null)}
        onLuu={(kq, gc) => { const id = modal.v.doiTuongId; setModal(null); chay('kq', async () => { await ganKetQua(id, kq, gc); return 'Đã gắn kết quả thí nghiệm cho lô vật liệu.' }) }} />}
      {modal?.kieu === 'lich' && <LichModal onClose={() => setModal(null)} />}
      {modal?.kieu === 'xem-truoc' && (
        <Modal title="Xem trước biên bản sẽ tạo" wide onClose={() => setModal(null)}>
          <p className="mb-3 text-sm text-ink/65">{xt.congTac} công tác gộp thành {xt.bienBan} biên bản ({gop === 'doan_ngay' ? 'theo đoạn, ngày' : 'từng vị trí'}), mỗi biên bản kèm giấy mời và bảng chiết tính.</p>
          <ul className="divide-y divide-ink/8 text-sm">{xt.danhSach.map((x, i) => <li key={i} className="flex justify-between gap-3 py-2"><span>{x.nhan}</span><span className="num text-ink/55">{x.soCongTac} công tác</span></li>)}</ul>
          {xt.danhSach.length === 0 && <p className="text-sm text-ink/55">Không có công tác nào đủ điều kiện trong khoảng ngày này.</p>}
        </Modal>)}
    </>
  )
}

function KetQuaModal({ v, onClose, onLuu }: { v: ViPham; onClose: () => void; onLuu: (kq: 'dat' | 'khong_dat', ghiChu: string) => void }) {
  const [kq, setKq] = useState<'dat' | 'khong_dat'>('dat'), [gc, setGc] = useState('')
  return (
    <Modal title="Gắn kết quả thí nghiệm" onClose={onClose}>
      <p className="mb-3 text-sm">{v.ten}<span className="block text-xs text-ink/60">{v.chiTiet}</span></p>
      <fieldset className="mb-3 flex gap-4 text-sm"><legend className="sr-only">Kết quả</legend>
        {([['dat', 'Đạt'], ['khong_dat', 'Không đạt']] as const).map(([k, t]) => <label key={k} className="flex items-center gap-2"><input type="radio" name="kq" checked={kq === k} onChange={() => setKq(k)} />{t}</label>)}</fieldset>
      <label className="mb-4 block text-sm font-semibold">Ghi chú (số hiệu phiếu thí nghiệm, ngày trả…)
        <textarea value={gc} onChange={(e) => setGc(e.target.value)} maxLength={300} rows={2} className="mt-1 w-full rounded-lg border border-ink/15 p-3 font-normal" /></label>
      <div className="flex justify-end gap-2"><button className="btn-ghost" onClick={onClose}>Hủy</button><button className="btn-primary" onClick={() => onLuu(kq, gc)}>Lưu kết quả</button></div>
    </Modal>
  )
}

function LichModal({ onClose }: { onClose: () => void }) {
  const [ds, setDs] = useState<LichNen[] | null>(null)
  useEffect(() => { getLichNen().then(setDs, () => setDs([])) }, [])
  return (
    <Modal title="Lịch nén mẫu bê tông" wide onClose={onClose}>
      {!ds ? <Loading /> : ds.length === 0 ? <p className="text-sm">Không có mẫu nào đang chờ nén.</p> : (
        <table className="w-full text-sm"><thead><tr className="text-left text-xs text-ink/55"><th className="pb-2">Hạn nén</th><th>Mẫu</th><th>Vị trí</th><th>Công tác</th><th className="text-right">Tuổi</th></tr></thead>
          <tbody>{ds.map((m) => <tr key={m.id} className="border-t border-ink/8"><td className="num py-2 font-semibold">{dm(m.hanNen, true)}</td><td className="num">{m.maMau}</td><td>{vtHien(m.viTri)}</td><td>{m.congTac}</td><td className="num text-right">{m.tuoiNgay} ngày</td></tr>)}</tbody></table>)}
    </Modal>
  )
}
