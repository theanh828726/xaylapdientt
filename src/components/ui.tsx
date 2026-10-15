import clsx from 'clsx'
import { useEffect, useRef, type ReactNode } from 'react'
import { X } from 'lucide-react'
import type { MucRule } from '../types'

const tones = {
  ok: 'bg-brand-soft text-brand', warn: 'bg-amber2/20 text-[#8a5a00]', bad: 'bg-danger/10 text-danger',
  idle: 'bg-ink/8 text-ink/70', info: 'bg-sky-100 text-sky-800',
}
export type Tone = keyof typeof tones
export const Badge = ({ tone = 'idle', children, className }: { tone?: Tone; children: ReactNode; className?: string }) => (
  <span className={clsx('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap', tones[tone], className)}>{children}</span>
)

/** Nhãn mức rule: CHẶN (đỏ đặc) / CẢNH BÁO (vàng) / NHẮC (xanh dương) kèm mã rule. */
export const RuleChip = ({ muc, ma }: { muc: MucRule; ma: string }) => (
  <span className={clsx('inline-flex w-[58px] shrink-0 flex-col items-center rounded-md py-1 text-[10px] font-bold leading-[1.15] uppercase tracking-wide',
    muc === 'Chặn' ? 'bg-danger text-white' : muc === 'Cảnh báo' ? 'bg-amber2/25 text-[#8a5a00] border border-amber2/50' : 'bg-sky-100 text-sky-800')}>
    <span>{muc === 'Nhắc việc' ? 'Nhắc' : muc === 'Cảnh báo' ? 'Cảnh báo' : 'Chặn'}</span><span className="num">{ma}</span>
  </span>
)

export const PageHeader = ({ title, sub, actions, eyebrow }: { title: string; sub?: string; actions?: ReactNode; eyebrow?: ReactNode }) => (
  <div className="flex flex-wrap items-end justify-between gap-3 mb-5">
    <div className="min-w-0">
      {eyebrow && <div className="text-xs text-ink/55 mb-1">{eyebrow}</div>}
      <h1 className="text-xl lg:text-2xl font-bold">{title}</h1>
      {sub && <p className="text-sm text-ink/60 mt-0.5">{sub}</p>}
    </div>
    {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
  </div>
)

export const Loading = () => <div className="p-8 text-sm text-ink/50">Đang tải…</div>
export const Empty = ({ children }: { children: ReactNode }) => <p className="card p-4 text-sm text-ink/60">{children}</p>
export const Alert = ({ children, tone = 'bad' }: { children: ReactNode; tone?: 'bad' | 'ok' | 'warn' }) => (
  <p role={tone === 'ok' ? 'status' : 'alert'} className={clsx('rounded-lg p-3 text-sm',
    tone === 'bad' ? 'bg-danger/10 text-danger' : tone === 'warn' ? 'bg-amber2/15 text-[#6b4a00]' : 'bg-brand-soft text-brand')}>{children}</p>
)

export const Bar = ({ value, max = 100, tone = 'brand' }: { value: number; max?: number; tone?: 'brand' | 'warn' | 'bad' }) => (
  <div className="h-1.5 rounded-full bg-ink/10 overflow-hidden" role="progressbar" aria-valuenow={value} aria-valuemax={max}>
    <div className={clsx('h-full rounded-full', tone === 'bad' ? 'bg-danger' : tone === 'warn' ? 'bg-amber2' : 'bg-brand')}
      style={{ width: `${Math.max(0, Math.min(100, max ? (value / max) * 100 : 0))}%` }} />
  </div>
)

export const Modal = ({ title, onClose, children, wide }: { title: string; onClose: () => void; children: ReactNode; wide?: boolean }) => {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', k)
    ref.current?.focus()
    return () => document.removeEventListener('keydown', k)
  }, [onClose])
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-ink/45 p-4" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div ref={ref} tabIndex={-1} role="dialog" aria-modal="true" aria-label={title}
        className={clsx('card max-h-[88vh] w-full overflow-y-auto p-5 outline-none', wide ? 'max-w-2xl' : 'max-w-md')}>
        <div className="mb-3 flex items-start justify-between gap-3">
          <h2 className="text-lg font-bold">{title}</h2>
          <button onClick={onClose} aria-label="Đóng" className="grid size-9 place-items-center rounded-lg hover:bg-ink/8"><X size={18} /></button>
        </div>
        {children}
      </div>
    </div>
  )
}

/** Logo TuyếnSố: ô vàng với cột điện hai xà. */
export const Logo = ({ size = 32 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 32 32" role="img" aria-label="TuyếnSố">
    <rect width="32" height="32" rx="7" fill="#E8A317" />
    <g stroke="#12201C" strokeWidth="2.4" strokeLinecap="round" fill="none">
      <path d="M11 6v20M21 6v20M7 11h18M7 17h18" />
    </g>
  </svg>
)
