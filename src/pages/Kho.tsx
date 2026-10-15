import { useState } from 'react'
import clsx from 'clsx'
import { ChevronRight } from 'lucide-react'
import { getKho, listDotGiaoHang } from '../api'
import { useAsync } from '../lib/useAsync'
import { dm, nf } from '../lib/fmt'
import { Badge, Empty, Loading, PageHeader } from '../components/ui'
import type { DotGiaoHang, NodeKho } from '../types'

const TT = { da_giao: ['ok', 'Đã giao'], tren_duong: ['warn', 'Trên đường'], cho_giao: ['idle', 'Chờ giao'] } as const

function Nut({ n, sau = 0 }: { n: NodeKho; sau?: number }) {
  const [mo, setMo] = useState(sau < 1)
  return (
    <li>
      <div className="flex min-h-[40px] items-center gap-2 border-t border-ink/8 py-2 pr-3 text-sm" style={{ paddingLeft: 12 + sau * 22 }}>
        {n.con?.length ? <button aria-label={mo ? 'Thu gọn' : 'Mở rộng'} aria-expanded={mo} onClick={() => setMo(!mo)}><ChevronRight size={16} className={clsx('transition-transform', mo && 'rotate-90')} /></button> : <span className="w-4" />}
        <span className="flex-1 font-medium">{n.ten}</span><span className="text-xs text-ink/50">{n.cap}</span>
        <span className="num w-20 text-right font-semibold">{nf(n.ton)}</span>
      </div>
      {mo && n.con && <ul>{n.con.map((c) => <Nut key={c.id} n={c} sau={sau + 1} />)}</ul>}
    </li>
  )
}

function Dot({ d }: { d: DotGiaoHang }) {
  const [tone, nhan] = TT[d.trangThai]
  return (
    <tr className="border-t border-ink/8">
      <td className="px-4 py-3"><b className="num">{d.po}</b> <span className="text-ink/55">· đợt {d.dot}</span></td>
      <td className="px-3">{d.hang}<div className="text-xs text-ink/55">{d.nhaCungCap ?? '—'}</div></td>
      <td className="px-3">{d.diaDiem}</td><td className="num px-3">{dm(d.ngayNhan ?? d.ngayDuKien)}</td>
      <td className="num px-3 text-right">{d.slNhan != null ? `${nf(d.slNhan)}/${nf(d.slDat ?? 0)}` : nf(d.slDat ?? 0)} {d.dvt}</td>
      <td className="px-3">{d.trangThai === 'da_giao' && !d.coAnhPhuongTien ? <Badge tone="bad">R11 · thiếu ảnh phương tiện</Badge> : <Badge tone={tone}>{nhan}</Badge>}</td>
    </tr>
  )
}

export default function Kho() {
  const kho = useAsync(getKho), dot = useAsync(listDotGiaoHang)
  if (!kho || !dot) return <Loading />
  return (
    <>
      <PageHeader eyebrow="Vật tư" title="Kho & giao nhận" sub="Tồn kho theo cấp Công ty → Công trường → Tổ đội và các đợt giao hàng." />
      <div className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <section className="card overflow-hidden" aria-label="Tồn kho"><h2 className="p-4 font-semibold">Tồn kho</h2><ul><Nut n={kho} /></ul></section>
        <section className="card overflow-hidden" aria-label="Đợt giao hàng"><h2 className="p-4 font-semibold">Đợt giao hàng · {dot.length}</h2>
          {dot.length === 0 ? <div className="p-4"><Empty>Chưa có đợt giao hàng.</Empty></div> : (
            <div className="overflow-x-auto"><table className="w-full min-w-[640px] text-sm"><thead><tr className="bg-paper text-left text-xs font-semibold text-ink/65">
              <th className="px-4 py-2.5">PO</th><th className="px-3">Hàng</th><th className="px-3">Địa điểm</th><th className="px-3">Ngày</th><th className="px-3 text-right">SL</th><th className="px-3">Trạng thái</th></tr></thead>
              <tbody>{dot.map((d) => <Dot key={d.id} d={d} />)}</tbody></table></div>)}
        </section>
      </div>
    </>
  )
}
