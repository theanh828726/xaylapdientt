import { useRef, useState } from 'react'
import { Download, Plus, Save, Upload } from 'lucide-react'
import clsx from 'clsx'
import { dungMauMacDinh, getPhanQuyen, listMauBieu, listNguoiDung, listTatCaDuAn, suaNguoiDung, suaPhanQuyen, taiMauLen, taiMauVe, taoNguoiDung } from '../api'
import { useAsync } from '../lib/useAsync'
import { useRole } from '../lib/role'
import { Badge, Loading, PageHeader } from '../components/ui'
import type { DuAnTom, MauBieuInfo, NguoiDungQT, PhanQuyen } from '../types'

// Phải khớp backend/app/rbac.py (Role, ROLE_LABEL).
const VAI_TRO = [
  ['giam_doc', 'Giám đốc'], ['chi_huy_truong', 'Chỉ huy trưởng'], ['ky_thuat', 'Kỹ thuật'], ['ke_toan', 'Kế toán'],
  ['phong_ke_hoach', 'P. Kế hoạch'], ['pho_giam_doc', 'Phó Giám đốc'], ['chu_tich', 'Chủ tịch'],
] as const
const loi = (e: unknown) => (e instanceof Error ? e.message : 'Thao tác thất bại')
const input = 'mt-1 w-full rounded-lg border border-ink/15 px-3 min-h-[44px] font-normal disabled:bg-ink/5'

export default function QuanTri() {
  const { can } = useRole()
  const coNguoiDung = can('nguoi_dung.quan_ly'), coPhanQuyen = can('phan_quyen.quan_ly'), coBieuMau = can('du_an.quan_ly')
  const [tab, setTab] = useState<'nguoi-dung' | 'phan-quyen' | 'bieu-mau'>(coNguoiDung ? 'nguoi-dung' : coPhanQuyen ? 'phan-quyen' : 'bieu-mau')
  if (!coNguoiDung && !coPhanQuyen && !coBieuMau) return <><PageHeader title="Quản trị" /><p className="card p-4 text-sm">Vai trò của bạn không có quyền quản trị.</p></>
  const tabs = [...(coNguoiDung ? [['nguoi-dung', 'Người dùng'] as const] : []), ...(coPhanQuyen ? [['phan-quyen', 'Phân quyền'] as const] : []),
    ...(coBieuMau ? [['bieu-mau', 'Biểu mẫu'] as const] : [])]
  return (
    <>
      <PageHeader title="Quản trị" sub="Người dùng, ma trận phân quyền và mẫu biểu (.docx) của dự án"
        actions={<div role="tablist" className="flex rounded-lg border border-ink/15 overflow-hidden">
          {tabs.map(([k, t]) => (
            <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
              className={clsx('px-4 min-h-[44px] text-sm font-semibold', tab === k ? 'bg-brand text-white' : 'bg-white')}>{t}</button>))}
        </div>} />
      {tab === 'nguoi-dung' && coNguoiDung ? <NguoiDungTab /> : tab === 'bieu-mau' && coBieuMau ? <BieuMauTab /> : <PhanQuyenTab />}
    </>
  )
}

// ---------------- Người dùng ----------------
function NguoiDungTab() {
  const { user } = useRole()
  const loaded = useAsync(listNguoiDung), duAn = useAsync(listTatCaDuAn)
  const [local, setLocal] = useState<NguoiDungQT[]>()
  const [edit, setEdit] = useState<string | null>(null)   // id đang sửa, 'moi' = thêm mới
  const ds = local ?? loaded
  if (!ds || !duAn) return <Loading />
  const ma = (id: string) => duAn.find((d) => d.id === id)?.ma ?? '?'
  const luu = (u: NguoiDungQT) => { setLocal(ds.some((x) => x.id === u.id) ? ds.map((x) => (x.id === u.id ? u : x)) : [...ds, u]); setEdit(null) }

  return (
    <div className="space-y-3">
      {edit === 'moi'
        ? <NguoiDungForm duAn={duAn} onCancel={() => setEdit(null)} onSaved={luu} />
        : <button className="btn-primary" onClick={() => setEdit('moi')}><Plus size={16} />Thêm người dùng</button>}
      <div className="card divide-y divide-ink/8">
        {ds.map((u) => edit === u.id
          ? <div key={u.id} className="p-4"><NguoiDungForm u={u} self={u.id === user?.id} duAn={duAn} onCancel={() => setEdit(null)} onSaved={luu} /></div>
          : <div key={u.id} className="p-4 flex flex-wrap items-center gap-3 text-sm">
              <div className="flex-1 min-w-[200px]"><div className="font-semibold">{u.hoTen}{u.donVi ? ` · ${u.donVi}` : ''}</div><div className="text-ink/60 num">{u.email}</div></div>
              <Badge tone="info">{u.vaiTroTen}</Badge>
              <div className="text-xs text-ink/60 min-w-[120px]">{u.duAnIds.length ? u.duAnIds.map(ma).join(', ') : 'Chưa gán dự án'}</div>
              <Badge tone={u.active ? 'ok' : 'bad'}>{u.active ? 'Hoạt động' : 'Đã khoá'}</Badge>
              <button className="btn-ghost" onClick={() => setEdit(u.id)}>Sửa</button>
            </div>)}
      </div>
    </div>
  )
}

function NguoiDungForm({ u, self, duAn, onCancel, onSaved }: {
  u?: NguoiDungQT; self?: boolean; duAn: DuAnTom[]; onCancel: () => void; onSaved: (u: NguoiDungQT) => void
}) {
  const [f, setF] = useState({ email: u?.email ?? '', hoTen: u?.hoTen ?? '', vaiTro: u?.vaiTro ?? 'ky_thuat', donVi: u?.donVi ?? '', matKhau: '', active: u?.active ?? true })
  const [da, setDa] = useState(new Set(u?.duAnIds ?? []))
  const [err, setErr] = useState(''), [busy, setBusy] = useState(false)
  const set = (k: keyof typeof f, v: string | boolean) => setF((p) => ({ ...p, [k]: v }))
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true); setErr('')
    try {
      onSaved(u
        ? await suaNguoiDung(u.id, { hoTen: f.hoTen, vaiTro: f.vaiTro, donVi: f.donVi, active: f.active, duAnIds: [...da], ...(f.matKhau && { matKhau: f.matKhau }) })
        : await taoNguoiDung({ email: f.email, hoTen: f.hoTen, vaiTro: f.vaiTro, donVi: f.donVi || undefined, matKhau: f.matKhau, duAnIds: [...da] }))
    } catch (x) { setErr(loi(x)) } finally { setBusy(false) }
  }
  return (
    <form onSubmit={submit} className="card p-4 space-y-3 border-brand/30">
      <h2 className="font-semibold">{u ? `Sửa ${u.hoTen}` : 'Thêm người dùng'}</h2>
      <div className="grid sm:grid-cols-2 gap-3">
        <label className="block text-sm font-semibold">Email
          <input type="email" required disabled={!!u} value={f.email} onChange={(e) => set('email', e.target.value)} className={input} /></label>
        <label className="block text-sm font-semibold">Họ tên
          <input required minLength={2} value={f.hoTen} onChange={(e) => set('hoTen', e.target.value)} className={input} /></label>
        <label className="block text-sm font-semibold">Vai trò
          <select value={f.vaiTro} disabled={self} onChange={(e) => set('vaiTro', e.target.value)} className={input}>
            {VAI_TRO.map(([k, t]) => <option key={k} value={k}>{t}</option>)}</select></label>
        <label className="block text-sm font-semibold">Đơn vị (tuỳ chọn)
          <input value={f.donVi} onChange={(e) => set('donVi', e.target.value)} placeholder="Ví dụ: Tổ đội 2" className={input} /></label>
        <label className="block text-sm font-semibold sm:col-span-2">{u ? 'Đặt lại mật khẩu (bỏ trống nếu giữ nguyên)' : 'Mật khẩu (≥ 10 ký tự)'}
          <input type="password" autoComplete="new-password" required={!u} minLength={10} value={f.matKhau} onChange={(e) => set('matKhau', e.target.value)} className={input} /></label>
      </div>
      <fieldset><legend className="text-sm font-semibold mb-1">Dự án được truy cập</legend>
        <div className="flex flex-wrap gap-x-5 gap-y-1">
          {duAn.map((d) => (
            <label key={d.id} className="flex items-center gap-2 text-sm min-h-[36px]">
              <input type="checkbox" checked={da.has(d.id)} onChange={(e) => setDa((p) => { const n = new Set(p); if (e.target.checked) n.add(d.id); else n.delete(d.id); return n })} />{d.ma}</label>))}
        </div></fieldset>
      {u && <label className="flex items-center gap-2 text-sm min-h-[36px]"><input type="checkbox" checked={f.active} disabled={self} onChange={(e) => set('active', e.target.checked)} />Tài khoản hoạt động{self && ' (không thể tự khoá)'}</label>}
      {u && <p className="text-xs text-ink/55">Đổi vai trò, đổi mật khẩu hoặc khoá tài khoản sẽ buộc người đó đăng nhập lại.</p>}
      {err && <p role="alert" className="rounded-lg bg-danger/10 p-3 text-sm text-danger">{err}</p>}
      <div className="flex gap-2"><button className="btn-primary" disabled={busy}><Save size={16} />{busy ? 'Đang lưu…' : 'Lưu'}</button><button type="button" className="btn-ghost" onClick={onCancel}>Hủy</button></div>
    </form>
  )
}

// ---------------- Phân quyền ----------------
const KHOA = new Set(['giam_doc:phan_quyen.quan_ly', 'giam_doc:nguoi_dung.quan_ly'])  // backend cấm gỡ: tránh tự khoá hệ thống

function PhanQuyenTab() {
  const data = useAsync(getPhanQuyen)
  if (!data) return <Loading />
  return <MaTran data={data} />
}

function MaTran({ data }: { data: PhanQuyen }) {
  const [m, setM] = useState<Record<string, Set<string>>>(() => Object.fromEntries(Object.entries(data.maTran).map(([k, v]) => [k, new Set(v)])))
  const [dirty, setDirty] = useState<Set<string>>(new Set())
  const [msg, setMsg] = useState(''), [err, setErr] = useState(''), [busy, setBusy] = useState(false)
  const toggle = (vt: string, q: string) => {
    setM((p) => { const n = new Set(p[vt]); if (n.has(q)) n.delete(q); else n.add(q); return { ...p, [vt]: n } })
    setDirty((p) => new Set(p).add(vt)); setMsg('')
  }
  const luu = async () => {
    setBusy(true); setErr(''); setMsg('')
    const con = new Set(dirty)
    try {
      for (const vt of dirty) { await suaPhanQuyen(vt, [...m[vt]]); con.delete(vt) }
      setMsg('Đã lưu. Quyền áp dụng ngay cho mọi yêu cầu; menu của người đang đăng nhập cập nhật khi họ tải lại trang.')
    } catch (e) { setErr(loi(e)) } finally { setDirty(con); setBusy(false) }
  }
  return (
    <div className="card p-4">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[820px] text-sm">
          <thead><tr><th className="pb-2 pr-3">Quyền</th>{data.vaiTro.map((v) => <th key={v.ma} className="pb-2 text-center">{v.ten}</th>)}</tr></thead>
          <tbody>{data.quyen.map((q) => (
            <tr key={q.ma} className="border-t border-ink/8">
              <td className="py-2 pr-3"><div className="font-medium">{q.moTa}</div><div className="num text-xs text-ink/50">{q.ma}</div></td>
              {data.vaiTro.map((v) => (
                <td key={v.ma} className="text-center">
                  <input type="checkbox" className="size-5" aria-label={`${q.moTa} – ${v.ten}`} checked={m[v.ma].has(q.ma)}
                    disabled={KHOA.has(`${v.ma}:${q.ma}`)} onChange={() => toggle(v.ma, q.ma)} />
                </td>))}
            </tr>))}</tbody>
        </table>
      </div>
      {err && <p role="alert" className="mt-3 rounded-lg bg-danger/10 p-3 text-sm text-danger">{err}</p>}
      {msg && <p role="status" className="mt-3 rounded-lg bg-brand-soft p-3 text-sm text-brand">{msg}</p>}
      <div className="mt-4 flex items-center gap-3">
        <button className="btn-primary" disabled={busy || dirty.size === 0} onClick={luu}><Save size={16} />{busy ? 'Đang lưu…' : `Lưu thay đổi${dirty.size ? ` (${dirty.size} vai trò)` : ''}`}</button>
        <span className="text-xs text-ink/55">Mỗi thay đổi được ghi vào audit_log.</span>
      </div>
    </div>
  )
}

// ---------------- Biểu mẫu ----------------
function BieuMauTab() {
  const loaded = useAsync(listMauBieu)
  const [local, setLocal] = useState<MauBieuInfo[]>()
  const [msg, setMsg] = useState(''), [err, setErr] = useState('')
  const ds = local ?? loaded
  if (!ds) return <Loading />
  const lam = async (viec: () => Promise<string | void>) => {
    setErr(''); setMsg('')
    try { const m = await viec(); if (m) setMsg(m) } catch (e) { setErr(loi(e)) }
  }
  const lamMoi = async () => setLocal(await listMauBieu())
  return (
    <div className="space-y-3">
      <p className="card p-4 text-sm text-ink/70">
        Mẫu mặc định do hệ thống tạo sẵn. Để chỉnh: <b>tải mẫu về</b>, sửa bằng Word (giữ nguyên các thẻ <span className="num">{'{{ … }}'}</span> và <span className="num">{'{% … %}'}</span>),
        rồi <b>tải lên</b>. Mẫu được thử render bằng dữ liệu mẫu trước khi nhận; phiên bản cũ vẫn được lưu và có thể quay về mẫu mặc định bất cứ lúc nào.
        Cần đối chiếu biểu mẫu hiện hành (TT 10/2021/TT-BXD) trước khi phát hành chính thức.
      </p>
      {err && <p role="alert" className="rounded-lg bg-danger/10 p-3 text-sm text-danger">{err}</p>}
      {msg && <p role="status" className="rounded-lg bg-brand-soft p-3 text-sm text-brand">{msg}</p>}
      {ds.map((m) => <MauCard key={m.loai} m={m} lam={lam} lamMoi={lamMoi} />)}
    </div>
  )
}

function MauCard({ m, lam, lamMoi }: { m: MauBieuInfo; lam: (v: () => Promise<string | void>) => Promise<void>; lamMoi: () => Promise<void> }) {
  const file = useRef<HTMLInputElement>(null)
  const [mo, setMo] = useState(false)
  return (
    <div className="card p-4 space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="font-semibold flex-1 min-w-[220px]">{m.ten}</h2>
        <Badge tone={m.nguon === 'du-an' ? 'ok' : 'idle'}>{m.nguon === 'du-an' ? `Mẫu dự án · v${m.phienBan}` : 'Mẫu mặc định'}</Badge>
      </div>
      {m.ghiChu && <p className="text-xs text-ink/60">Ghi chú: {m.ghiChu}</p>}
      <div className="flex flex-wrap gap-2">
        <button className="btn-ghost" onClick={() => lam(async () => { await taiMauVe(m.loai, 'hien-tai') })}><Download size={16} />Tải mẫu đang dùng</button>
        {m.nguon === 'du-an' && <button className="btn-ghost" onClick={() => lam(async () => { await taiMauVe(m.loai, 'mac-dinh') })}><Download size={16} />Tải mẫu mặc định</button>}
        <input ref={file} type="file" hidden accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ''; if (f) lam(async () => { const r = await taiMauLen(m.loai, f); await lamMoi(); return `Đã áp dụng mẫu mới (phiên bản ${r.phienBan}) cho "${m.ten}".` }) }} />
        <button className="btn-primary" onClick={() => file.current?.click()}><Upload size={16} />Tải lên bản đã sửa (.docx)</button>
        {m.nguon === 'du-an' && <button className="btn-ghost" onClick={() => lam(async () => { await dungMauMacDinh(m.loai); await lamMoi(); return `Đã quay về mẫu mặc định cho "${m.ten}".` })}>Dùng lại mẫu mặc định</button>}
      </div>
      <button className="text-sm underline text-brand" onClick={() => setMo(!mo)}>{mo ? 'Ẩn' : 'Xem'} các biến dùng được trong mẫu</button>
      {mo && <table className="w-full table-fixed text-sm"><tbody>{m.bien.map((b) => (
        <tr key={b.ten} className="border-t border-ink/8 align-top"><td className="py-1.5 pr-3 num text-xs break-all w-[45%]">{`{{ ${b.ten.split('  ')[0]} }}`}</td><td className="py-1.5">{b.moTa}</td></tr>))}</tbody></table>}
    </div>
  )
}
