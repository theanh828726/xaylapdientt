import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Bell, BookOpen, Check, ChevronDown, ClipboardCheck, GitCompare, Home, LogOut, Map, Package, RotateCcw, Search, Settings, User, Warehouse } from 'lucide-react'
import clsx from 'clsx'
import { useRole } from '../lib/role'
import { docTatCaThongBao, getDem, getThongBao, listTuyen, timKiem, type Dem } from '../api'
import { ten2chu } from '../lib/fmt'
import type { KetQuaTim, ThongBao, Tuyen } from '../types'
import ErrorBoundary from './ErrorBoundary'
import { Logo } from './ui'

// Trang có thể thay cột menu trái bằng nội dung riêng (vd. Đối soát: danh sách hạng mục) qua <SidebarPortal>.
const SidebarCtx = createContext<{ el: HTMLElement | null; setCustom: (b: boolean) => void }>({ el: null, setCustom: () => {} })
// eslint-disable-next-line react-refresh/only-export-components
export function SidebarPortal({ children }: { children: ReactNode }) {
  const { el, setCustom } = useContext(SidebarCtx)
  useEffect(() => { setCustom(true); return () => setCustom(false) }, [setCustom])
  return el ? createPortal(children, el) : null
}

const NAV = [
  { to: '/ban-do', label: 'Bản đồ tuyến', icon: Map },
  { to: '/qaqc', label: 'Hồ sơ QA/QC', icon: ClipboardCheck, badge: 'loiChan' as const, tone: 'bad' as const },
  { to: '/de-xuat', label: 'Đề xuất vật tư', icon: Package },
  { to: '/kho', label: 'Kho & giao nhận', icon: Warehouse },
  { to: '/nhat-ky', label: 'Nhật ký thi công', icon: BookOpen },
  { to: '/duyet', label: 'Phê duyệt', icon: Check, badge: 'choToi' as const, tone: 'warn' as const },
  { to: '/doi-soat', label: 'Đối soát 3 nguồn', icon: GitCompare },
  { to: '/thu-hoi', label: 'Thu hồi tuyến cũ', icon: RotateCcw },
]
const MOBILE = [
  { to: '/tong-quan', label: 'Tổng quan', icon: Home },
  { to: '/duyet', label: 'Duyệt', icon: Check, badge: 'choToi' as const },
  { to: '/ban-do', label: 'Bản đồ', icon: Map },
  { to: '/toi', label: 'Tôi', icon: User },
]

function useClickOutside(ref: React.RefObject<HTMLElement | null>, onOut: () => void) {
  useEffect(() => {
    const f = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && onOut()
    document.addEventListener('mousedown', f)
    return () => document.removeEventListener('mousedown', f)
  }, [ref, onOut])
}

function ChonDuAn() {
  const { duAn, duAnId, chonDuAn } = useRole()
  const [mo, setMo] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const dong = useCallback(() => setMo(false), [])
  useClickOutside(ref, dong)
  const cur = duAn.find((d) => d.id === duAnId)
  return (
    <div ref={ref} className="relative min-w-0">
      <button onClick={() => duAn.length > 1 && setMo(!mo)} aria-haspopup="listbox" aria-expanded={mo}
        className="flex items-center gap-2 rounded-lg border border-white/15 bg-white/5 px-3 min-h-[38px] text-left text-sm max-w-[460px] hover:bg-white/10">
        <span className="text-white/55 text-xs shrink-0">Dự án</span>
        <span className="truncate font-semibold">{cur?.ten ?? '—'}</span>
        {duAn.length > 1 && <ChevronDown size={15} className="shrink-0 text-white/60" />}
      </button>
      {mo && (
        <ul role="listbox" className="absolute left-0 top-full z-40 mt-1 w-[420px] max-w-[90vw] rounded-lg bg-white p-1 text-ink shadow-xl">
          {duAn.map((d) => (
            <li key={d.id}><button role="option" aria-selected={d.id === duAnId} onClick={() => { setMo(false); if (d.id !== duAnId) chonDuAn(d.id) }}
              className={clsx('w-full rounded-md px-3 py-2 text-left text-sm hover:bg-brand-soft', d.id === duAnId && 'bg-brand-soft font-semibold')}>
              <span className="num text-xs text-ink/50">{d.ma}</span><br />{d.ten}</button></li>))}
        </ul>
      )}
    </div>
  )
}

function TimKiem() {
  const nav = useNavigate()
  const [q, setQ] = useState(''), [kq, setKq] = useState<KetQuaTim[]>([]), [mo, setMo] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const dong = useCallback(() => setMo(false), [])
  useClickOutside(ref, dong)
  useEffect(() => {
    if (q.trim().length < 2) return
    const t = setTimeout(() => timKiem(q.trim()).then((r) => { setKq(r); setMo(true) }, () => setKq([])), 250)
    return () => clearTimeout(t)
  }, [q])
  const di = (k: KetQuaTim) => { setMo(false); setQ(''); nav(k.lienKet) }
  return (
    <div ref={ref} className="relative w-full max-w-[340px]">
      <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-white/55" />
      <input value={q} onChange={(e) => { setQ(e.target.value); if (e.target.value.trim().length < 2) setKq([]) }} onFocus={() => kq.length && setMo(true)} aria-label="Tìm kiếm"
        onKeyDown={(e) => { if (e.key === 'Enter' && kq[0]) di(kq[0]); if (e.key === 'Escape') setMo(false) }}
        placeholder="Tìm vị trí, mã móng, phiếu…" className="w-full rounded-lg border border-white/15 bg-white/5 pl-9 pr-3 min-h-[38px] text-sm placeholder:text-white/50 focus:bg-white/10 outline-none" />
      {mo && (
        <ul className="absolute right-0 top-full z-40 mt-1 max-h-[60vh] w-[min(420px,90vw)] overflow-y-auto rounded-lg bg-white p-1 text-ink shadow-xl">
          {kq.length === 0 ? <li className="px-3 py-2 text-sm text-ink/55">Không có kết quả</li> : kq.map((k, i) => (
            <li key={i}><button onClick={() => di(k)} className="flex w-full items-baseline gap-2 rounded-md px-3 py-2 text-left text-sm hover:bg-brand-soft">
              <span className="w-20 shrink-0 text-[11px] font-semibold uppercase text-ink/45">{k.loai}</span>
              <span className="min-w-0"><b className="num">{k.tieuDe}</b><span className="block truncate text-xs text-ink/60">{k.phu}</span></span></button></li>))}
        </ul>
      )}
    </div>
  )
}

function Chuong({ dem, lamMoi }: { dem: Dem | null; lamMoi: () => void }) {
  const nav = useNavigate()
  const [mo, setMo] = useState(false), [tb, setTb] = useState<ThongBao[]>([])
  const ref = useRef<HTMLDivElement>(null)
  const dong = useCallback(() => setMo(false), [])
  useClickOutside(ref, dong)
  const tong = (dem?.choToi ?? 0) + (dem?.chuaDoc ?? 0)
  const bam = async () => {
    const m = !mo
    setMo(m)
    if (m) setTb((await getThongBao()).items)
  }
  const docHet = async () => { await docTatCaThongBao(); setTb((x) => x.map((n) => ({ ...n, daDoc: true }))); lamMoi() }
  return (
    <div ref={ref} className="relative">
      <button onClick={bam} aria-label={`Thông báo${tong ? `, ${tong} mục mới` : ''}`} aria-expanded={mo}
        className="relative grid size-10 place-items-center rounded-lg border border-white/15 bg-white/5 hover:bg-white/10">
        <Bell size={17} />
        {tong > 0 && <span className="num absolute -right-1 -top-1 grid min-w-[18px] place-items-center rounded-full bg-danger px-1 text-[10px] font-bold">{tong}</span>}
      </button>
      {mo && (
        <div className="absolute right-0 top-full z-40 mt-1 w-[min(380px,92vw)] rounded-lg bg-white p-2 text-ink shadow-xl">
          {dem && dem.choToi > 0 && <>
            <div className="px-2 pt-1 text-[11px] font-semibold uppercase text-ink/45">Chờ bạn duyệt ({dem.choToi})</div>
            {dem.choToiItems.map((i) => (
              <button key={i.ma} onClick={() => { setMo(false); nav('/duyet') }} className="block w-full rounded-md px-2 py-2 text-left text-sm hover:bg-brand-soft">
                <b className="num">{i.ma}</b> · <span className="text-ink/60">{i.nhan.toLowerCase()}</span><span className="block truncate text-xs text-ink/70">{i.tieuDe}</span></button>))}
          </>}
          <div className="mt-1 flex items-center justify-between px-2 pt-1 text-[11px] font-semibold uppercase text-ink/45">
            <span>Thông báo</span>{tb.some((n) => !n.daDoc) && <button onClick={docHet} className="normal-case text-brand underline">Đánh dấu đã đọc</button>}
          </div>
          {tb.length === 0 && <p className="px-2 py-3 text-sm text-ink/55">Không có thông báo.</p>}
          {tb.map((n) => (
            <button key={n.id} onClick={() => { setMo(false); if (n.lienKet) nav(n.lienKet) }}
              className={clsx('block w-full rounded-md px-2 py-2 text-left text-sm hover:bg-brand-soft', !n.daDoc && 'font-semibold')}>
              {n.tieuDe}<span className="block text-xs font-normal text-ink/60">{n.noiDung} · {n.thoiGian}</span></button>))}
        </div>
      )}
    </div>
  )
}

function NguoiDung() {
  const { user, role, logout } = useRole()
  const nav = useNavigate()
  const [mo, setMo] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const dong = useCallback(() => setMo(false), [])
  useClickOutside(ref, dong)
  return (
    <div ref={ref} className="relative">
      <button onClick={() => setMo(!mo)} aria-expanded={mo} className="flex items-center gap-2.5 rounded-lg px-1 py-1 hover:bg-white/10">
        <span className="grid size-9 place-items-center rounded-full bg-brand-light text-xs font-bold">{ten2chu(user?.hoTen ?? '')}</span>
        <span className="hidden text-left leading-tight md:block"><span className="block text-sm font-semibold">{user?.hoTen}</span><span className="block text-xs text-white/60">{role}</span></span>
      </button>
      {mo && (
        <div className="absolute right-0 top-full z-40 mt-1 w-48 rounded-lg bg-white p-1 text-sm text-ink shadow-xl">
          <button onClick={() => { setMo(false); nav('/toi') }} className="flex w-full items-center gap-2 rounded-md px-3 py-2 hover:bg-brand-soft"><User size={15} />Tài khoản của tôi</button>
          <button onClick={logout} className="flex w-full items-center gap-2 rounded-md px-3 py-2 hover:bg-brand-soft"><LogOut size={15} />Đăng xuất</button>
        </div>
      )}
    </div>
  )
}

function TheTuyen({ tuyen }: { tuyen: Tuyen[] }) {
  const t = tuyen.find((x) => x.loai === 'moi') ?? tuyen[0]
  if (!t) return null
  return (
    <div className="m-3 rounded-lg bg-paper p-3 text-xs leading-relaxed">
      <div className="font-semibold text-ink">{t.ten.replace(/(\d+(?:,\d+)?) kV/, 'trung thế $1 kV')}</div>
      <div className="text-ink/65"><span className="num">{t.soViTri}</span> vị trí · <span className="num">{t.chieuDaiKm.toLocaleString('vi-VN')}</span> km</div>
      {t.capNhat && <div className="text-ink/50">Cập nhật {t.capNhat.slice(8, 10)}/{t.capNhat.slice(5, 7)} · {t.capNhat.slice(11, 16)}</div>}
    </div>
  )
}

export default function Layout() {
  const { can } = useRole()
  const { pathname } = useLocation()
  const [el, setEl] = useState<HTMLElement | null>(null)
  const [custom, setCustomState] = useState(false)
  const [dem, setDem] = useState<Dem | null>(null)
  const [tuyen, setTuyen] = useState<Tuyen[]>([])
  const lamMoi = useCallback(() => { getDem().then(setDem, () => {}) }, [])
  useEffect(() => { lamMoi() }, [lamMoi, pathname])
  useEffect(() => { listTuyen().then(setTuyen, () => {}) }, [])
  const setCustom = useCallback((b: boolean) => setCustomState(b), [])
  const menu = can('nguoi_dung.quan_ly') || can('phan_quyen.quan_ly') || can('du_an.quan_ly')
    ? [...NAV, { to: '/quan-tri', label: 'Quản trị', icon: Settings } as (typeof NAV)[number]] : NAV
  const bao = pathname.startsWith('/bao-cao')   // màn hình báo cáo hiện trường tự có thanh hành động ở đáy

  return (
    <SidebarCtx.Provider value={{ el, setCustom }}>
      <div className="flex min-h-screen flex-col lg:h-screen">
        <header className="hidden h-16 shrink-0 items-center gap-4 bg-ink px-5 text-white lg:flex">
          <NavLink to="/ban-do" className="flex items-center gap-2.5 font-bold"><Logo />TuyếnSố</NavLink>
          <ChonDuAn />
          <div className="ml-auto flex items-center gap-3"><TimKiem /><Chuong dem={dem} lamMoi={lamMoi} /><NguoiDung /></div>
        </header>
        <div className="flex min-h-0 flex-1">
          <aside className="hidden w-[232px] shrink-0 flex-col overflow-y-auto border-r border-ink/10 bg-white lg:flex">
            <div ref={setEl} className={custom ? 'block' : 'hidden'} />
            <div className={clsx('flex flex-1 flex-col', custom && 'hidden')}>
              <nav className="flex-1 space-y-1 p-3" aria-label="Điều hướng chính">
                {menu.map(({ to, label, icon: I, ...r }) => {
                  const so = 'badge' in r && r.badge && dem ? dem[r.badge] : 0
                  return (
                    <NavLink key={to} to={to} className={({ isActive }) => clsx('flex min-h-[42px] items-center gap-3 rounded-lg px-3 text-sm font-medium',
                      isActive ? 'bg-brand-soft text-brand' : 'text-ink/75 hover:bg-ink/5')}>
                      <I size={17} /><span className="flex-1">{label}</span>
                      {so > 0 && <span className={clsx('num min-w-[22px] rounded-full px-1.5 py-0.5 text-center text-[11px] font-bold', 'tone' in r && r.tone === 'bad' ? 'bg-danger/10 text-danger' : 'bg-amber2/25 text-[#8a5a00]')}>{so}</span>}
                    </NavLink>)
                })}
              </nav>
              <TheTuyen tuyen={tuyen} />
            </div>
          </aside>
          <main className={clsx('min-w-0 flex-1 overflow-y-auto bg-paper p-4 lg:p-6', !bao && 'pb-24 lg:pb-6')}>
            <ErrorBoundary key={pathname}><Outlet /></ErrorBoundary>
          </main>
        </div>
        {!bao && (
          <nav aria-label="Điều hướng nhanh" className="fixed inset-x-0 bottom-0 z-30 flex border-t border-ink/10 bg-white lg:hidden">
            {MOBILE.map(({ to, label, icon: I, ...r }) => {
              const so = 'badge' in r && r.badge && dem ? dem[r.badge] : 0
              return (
                <NavLink key={to} to={to} className={({ isActive }) => clsx('relative flex min-h-[58px] flex-1 flex-col items-center justify-center gap-0.5 text-[11px] font-medium', isActive ? 'text-brand' : 'text-ink/55')}>
                  <I size={21} />{label}
                  {so > 0 && <span className="num absolute left-1/2 top-1.5 ml-2 grid min-w-[16px] place-items-center rounded-full bg-danger px-1 text-[9px] font-bold text-white">{so}</span>}
                </NavLink>)
            })}
          </nav>
        )}
      </div>
    </SidebarCtx.Provider>
  )
}
