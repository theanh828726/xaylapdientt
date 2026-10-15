import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'
import { AlertTriangle } from 'lucide-react'
import { duyetBuoc, getHopThu } from '../api'
import { dm, lamLoi } from '../lib/fmt'
import { Alert, Empty, Loading, Modal } from '../components/ui'
import type { HopThu, HopThuItem } from '../types'

type Tab = 'cho_toi' | 'cap_khac' | 'da_xu_ly'
const TABS: { k: Tab; nhan: string; dem: keyof HopThu['dem'] }[] = [
  { k: 'cho_toi', nhan: 'Chờ tôi', dem: 'choToi' }, { k: 'cap_khac', nhan: 'Cấp khác', dem: 'capKhac' }, { k: 'da_xu_ly', nhan: 'Đã xử lý', dem: 'daXuLy' },
]
const DOT = { xong: 'bg-brand', dang: 'bg-amber2 ring-4 ring-amber2/30', cho: 'bg-ink/20', tu_choi: 'bg-danger' } as const

function Chuoi({ c }: { c: HopThuItem['chuoi'] }) {
  return (
    <ol className="flex items-start gap-1 overflow-x-auto py-1" aria-label="Chuỗi duyệt">
      {c.map((b, i) => (
        <li key={i} className="flex min-w-[52px] flex-1 flex-col items-center gap-1 text-center">
          <span className="flex w-full items-center"><i className={clsx('h-0.5 flex-1', i === 0 ? 'opacity-0' : 'bg-ink/15')} />
            <i className={clsx('size-3 shrink-0 rounded-full', DOT[b.trangThai as keyof typeof DOT] ?? DOT.cho)} />
            <i className={clsx('h-0.5 flex-1', i === c.length - 1 ? 'opacity-0' : 'bg-ink/15')} /></span>
          <span className={clsx('text-[11px] leading-tight', b.trangThai === 'dang' ? 'font-bold text-ink' : 'text-ink/60')}>{b.ngan}</span>
        </li>))}
    </ol>
  )
}

function The({ it, onXong, onLoi }: { it: HopThuItem; onXong: (m: string) => void; onLoi: (m: string) => void }) {
  const [lyDo, setLyDo] = useState<string | null>(null), [busy, setBusy] = useState(false), [xacNhan, setXacNhan] = useState(false)
  const gui = async (q: 'duyet' | 'tu_choi', ly?: string) => {
    setBusy(true)
    try { await duyetBuoc(it.doiTuong, it.id, q, ly); setLyDo(null); setXacNhan(false); onXong(q === 'duyet' ? `Đã duyệt ${it.ma}.` : `Đã trả lại ${it.ma}.`) }
    catch (e) { onLoi(lamLoi(e)) } finally { setBusy(false) }
  }
  return (
    <article className="card p-4">
      <div className="flex items-baseline justify-between gap-2 text-xs"><span><b className="num text-sm">{it.ma}</b> · <span className="text-ink/60">{it.nhan}</span></span><span className="text-ink/50">{it.gio} · {dm(it.moc.slice(0, 10), true)}</span></div>
      <h3 className="mt-1.5 font-semibold leading-snug">{it.tieuDe}</h3>
      <div className="mt-2"><Chuoi c={it.chuoi} /></div>
      {it.canhBao && (
        <div role="alert" className="mt-2 flex gap-2 rounded-lg bg-amber2/15 p-2.5 text-sm"><AlertTriangle size={16} className="mt-0.5 shrink-0 text-amber2" />
          <p><b className="num">{it.canhBao.ma} · </b>{it.canhBao.noiDung}</p></div>)}
      {it.chiTiet && (
        <div className="mt-2 space-y-1.5 rounded-lg bg-paper p-3 text-sm">
          <p>{it.chiTiet.lyDo}</p>
          {it.chiTiet.tacDong.length > 0 && <ul className="list-disc pl-5 text-ink/75">{it.chiTiet.tacDong.map((t) => <li key={t}>{t}</li>)}</ul>}
          {it.chiTiet.sauDieuChinh && <p className="font-semibold text-brand">Sau điều chỉnh: {it.chiTiet.sauDieuChinh}</p>}
        </div>)}
      <div className="mt-3 grid grid-cols-3 gap-2">
        {it.coTheDuyet
          ? <button className="btn-ghost" disabled={busy} onClick={() => setLyDo('')}>Trả lại</button>
          : <span />}
        <Link to={it.lienKet} className="btn-ghost justify-center">Chi tiết</Link>
        {it.coTheDuyet
          ? <button className="btn-primary" disabled={busy} onClick={() => setXacNhan(true)}>Duyệt</button>
          : <span className="grid place-items-center text-xs text-ink/50">{it.trangThai === 'da_duyet' ? 'Đã duyệt' : it.trangThai === 'tu_choi' ? 'Đã trả lại' : 'Đang chờ cấp khác'}</span>}
      </div>
      {xacNhan && (
        <Modal title={`Duyệt ${it.ma}?`} onClose={() => setXacNhan(false)}>
          <p className="text-sm">{it.tieuDe}</p>
          <p className="mt-2 text-sm text-ink/65">Sau khi duyệt, hồ sơ chuyển cho bước kế tiếp trong chuỗi duyệt và bạn không thể tự hoàn tác.</p>
          <div className="mt-3 flex justify-end gap-2"><button className="btn-ghost" onClick={() => setXacNhan(false)}>Huỷ</button>
            <button className="btn-primary" disabled={busy} onClick={() => gui('duyet')}>{busy ? 'Đang gửi…' : 'Xác nhận duyệt'}</button></div>
        </Modal>)}
      {lyDo !== null && (
        <Modal title={`Trả lại ${it.ma}`} onClose={() => setLyDo(null)}>
          <label className="block text-sm font-medium" htmlFor={`ly-${it.id}`}>Lý do trả lại (bắt buộc)</label>
          <textarea id={`ly-${it.id}`} className="mt-1 w-full rounded-lg border border-ink/20 p-2 text-sm" rows={3} value={lyDo} onChange={(e) => setLyDo(e.target.value)} />
          <div className="mt-3 flex justify-end gap-2"><button className="btn-ghost" onClick={() => setLyDo(null)}>Huỷ</button>
            <button className="btn-primary" disabled={!lyDo.trim() || busy} onClick={() => gui('tu_choi', lyDo.trim())}>Trả lại</button></div>
        </Modal>)}
    </article>
  )
}

export default function Duyet() {
  const [tab, setTab] = useState<Tab>('cho_toi'), [d, setD] = useState<HopThu | null>(null)
  const [loi, setLoi] = useState(''), [msg, setMsg] = useState('')
  const tai = useCallback((t: Tab) => { getHopThu(t).then((r) => { setD(r); setLoi('') }, (e) => setLoi(lamLoi(e))) }, [])
  useEffect(() => { tai(tab) }, [tab, tai])
  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-3 text-xl font-bold lg:text-2xl">Phê duyệt</h1>
      <div role="tablist" className="mb-4 flex rounded-xl bg-ink/8 p-1">
        {TABS.map((t) => (
          <button key={t.k} role="tab" aria-selected={tab === t.k} onClick={() => { setTab(t.k); setD(null); setMsg('') }}
            className={clsx('min-h-[40px] flex-1 rounded-lg text-sm font-semibold', tab === t.k ? 'bg-white text-ink shadow-sm' : 'text-ink/60')}>
            {t.nhan}{d && <span className={clsx('num ml-1.5 rounded-full px-1.5 text-xs', t.k === 'cho_toi' && d.dem.choToi > 0 ? 'bg-danger text-white' : 'text-ink/50')}>{d.dem[t.dem]}</span>}</button>))}
      </div>
      {loi && <div className="mb-3"><Alert>{loi}</Alert></div>}
      {msg && <div className="mb-3"><Alert tone="ok">{msg}</Alert></div>}
      {!d ? <Loading /> : d.items.length === 0 ? <Empty>{tab === 'cho_toi' ? 'Không có mục nào đang chờ bạn duyệt.' : 'Chưa có mục nào.'}</Empty>
        : <div className="space-y-3">{d.items.map((it) => <The key={it.doiTuong + it.id} it={it} onLoi={setLoi} onXong={(m) => { setMsg(m); tai(tab) }} />)}</div>}
    </div>
  )
}
