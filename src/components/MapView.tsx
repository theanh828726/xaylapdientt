import { useEffect, useRef, useState } from 'react'
import { LngLatBounds, Map as MlMap, Marker, setWorkerUrl, type ExpressionSpecification, type GeoJSONSourceSpecification } from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
import { Layers, Minus, Plus } from 'lucide-react'
import clsx from 'clsx'
import type { GeoFeatureCollection, ViTriCot } from '../types'

// Vite đóng gói worker (kèm module phụ thuộc) thành một file riêng; mặc định của maplibre bị lệch đường dẫn sau khi pre-bundle.
setWorkerUrl(workerUrl)

// Nền bản đồ raster OSM cho demo. Production nên dùng nguồn tile riêng/được cấp phép: đặt VITE_MAP_TILES_URL.
const TILES = import.meta.env.VITE_MAP_TILES_URL ?? 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'

import { BUOC_STYLE } from '../lib/buoc'

const coWebGL = () => {
  try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')) } catch { return false }
}

const bounds = (geo: GeoFeatureCollection) => {
  const b = new LngLatBounds()
  for (const f of geo.features) {
    const c = f.geometry.coordinates as number[] | number[][]
    if (typeof c[0] === 'number') b.extend(c as [number, number])
    else (c as [number, number][]).forEach((p) => b.extend(p))
  }
  return b
}

/** Chỉ hiện các tuyến đang bật (theo mã tuyến), giữ nguyên phân loại kiểu vẽ của từng lớp. */
function apLoc(m: MlMap, bat: string[]) {
  const ma = ['literal', bat] as unknown as ExpressionSpecification
  const dieuKien: Record<string, unknown> = {
    'tuyen-cu': ['==', ['get', 'tuyenLoai'], 'cu'],
    'tuyen-ha': ['all', ['==', ['get', 'tuyenLoai'], 'moi'], ['==', ['get', 'capDienAp'], '0,4 kV']],
    'tuyen-moi': ['all', ['==', ['get', 'tuyenLoai'], 'moi'], ['!=', ['get', 'capDienAp'], '0,4 kV']],
  }
  for (const [id, dk] of Object.entries(dieuKien)) {
    if (m.getLayer(id)) m.setFilter(id, ['all', ['==', ['get', 'loai'], 'tuyen'], dk, ['in', ['get', 'ma'], ma]] as unknown as ExpressionSpecification)
  }
}

function dungMarker(p: ViTriCot, chon: boolean, onClick: () => void): HTMLElement {
  const st = BUOC_STYLE[p.buoc]
  const so = p.ten.replace(/^VT/, '')
  const el = document.createElement('div')
  el.className = 'tuyenso-marker'
  el.setAttribute('role', 'button')
  el.tabIndex = 0
  el.setAttribute('aria-label', `${p.ten.replace('VT', 'Vị trí ')}, ${st.nhan}${p.canhBaoMuc ? p.canhBaoMuc === 'chan' ? ', có lỗi chặn' : ', có cảnh báo' : ''}`)
  el.style.cssText = 'position:relative;display:flex;flex-direction:column;align-items:center;cursor:pointer;'
  const kich = chon ? 22 : 16
  const dot = document.createElement('div')
  dot.style.cssText = `width:${kich}px;height:${kich}px;border-radius:50%;background:${st.bg};border:2.5px solid ${st.vien};box-shadow:0 0 0 1px rgba(18,32,28,.35)${chon ? ',0 0 0 5px #E8A317' : ''};`
  el.appendChild(dot)
  if (p.canhBaoMuc) {
    const w = document.createElement('div')
    w.style.cssText = 'position:absolute;top:-12px;right:-10px;line-height:0;'
    const mau = p.canhBaoMuc === 'chan' ? '#A1281A' : '#E8A317'
    w.innerHTML = `<svg width="18" height="16" viewBox="0 0 18 16" aria-hidden="true"><path d="M9 1.2 17 15H1z" fill="${mau}" stroke="#fff" stroke-width="1.4" stroke-linejoin="round"/><path d="M9 6v4.2" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/><circle cx="9" cy="12.4" r=".9" fill="#fff"/></svg>`
    el.appendChild(w)
  }
  const nhan = document.createElement('div')
  nhan.className = 'tuyenso-nhan'
  nhan.textContent = chon ? p.ten.replace('VT', 'VT ') : so
  nhan.style.cssText = chon
    ? 'margin-top:5px;background:#12201C;color:#fff;border-radius:6px;padding:2px 8px;font:600 12px "JetBrains Mono",monospace;white-space:nowrap;'
    : 'margin-top:3px;color:#12201C;font:500 11px "JetBrains Mono",monospace;text-shadow:0 0 3px #fff,0 0 3px #fff;'
  el.appendChild(nhan)
  el.addEventListener('click', (e) => { e.stopPropagation(); onClick() })
  el.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick() } })
  return el
}

interface Props {
  poles: ViTriCot[]
  geo: GeoFeatureCollection
  tuyenHienThi: string[]          // mã tuyến đang bật
  selectedId?: string
  onSelect: (id: string) => void
  onViewport?: (ids: string[]) => void
}

export default function MapView({ poles, geo, tuyenHienThi, selectedId, onSelect, onViewport }: Props) {
  const box = useRef<HTMLDivElement>(null)
  const map = useRef<MlMap | null>(null)
  const markers = useRef<Marker[]>([])
  const [webgl] = useState(coWebGL)
  const [nen, setNen] = useState<'osm' | 'trang'>('osm')
  const [moMenu, setMoMenu] = useState(false)
  const moi = useRef({ poles, tuyenHienThi, onSelect, onViewport, nen })
  useEffect(() => { moi.current = { poles, tuyenHienThi, onSelect, onViewport, nen } })

  const baoViewport = () => {
    const m = map.current
    if (!m || !moi.current.onViewport) return
    const b = m.getBounds()
    moi.current.onViewport(moi.current.poles.filter((p) => p.lon != null && p.lat != null && b.contains([p.lon, p.lat])).map((p) => p.id))
  }

  // Khởi tạo bản đồ một lần cho mỗi bộ dữ liệu hình học.
  useEffect(() => {
    if (!box.current || !webgl) return
    const m = new MlMap({
      container: box.current,
      style: {
        version: 8,
        sources: { nen: { type: 'raster', tiles: [TILES], tileSize: 256, maxzoom: 19, attribution: '© OpenStreetMap' } },
        layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#EEF0EA' } }, { id: 'nen', type: 'raster', source: 'nen' }],
      },
      bounds: geo.features.length ? bounds(geo) : undefined, fitBoundsOptions: { padding: 70, maxZoom: 17 },
      attributionControl: { compact: true },
    })
    map.current = m
    m.on('style.load', () => {
      m.addSource('tuyen', { type: 'geojson', data: geo as unknown as GeoJSONSourceSpecification['data'] })
      m.addLayer({ id: 'tuyen-cu', type: 'line', source: 'tuyen', layout: { 'line-cap': 'butt' },
        paint: { 'line-color': '#6B7771', 'line-width': 2.2, 'line-dasharray': [3, 3], 'line-opacity': 0.85 } })
      m.addLayer({ id: 'tuyen-ha', type: 'line', source: 'tuyen', paint: { 'line-color': '#2E8C7E', 'line-width': 2.6, 'line-opacity': 0.9 } })
      m.addLayer({ id: 'tuyen-moi', type: 'line', source: 'tuyen', layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': '#0F5C55', 'line-width': 4.5 } })
      apLoc(m, moi.current.tuyenHienThi)
      m.setLayoutProperty('nen', 'visibility', moi.current.nen === 'osm' ? 'visible' : 'none')
    })
    m.on('moveend', baoViewport)
    m.on('load', baoViewport)
    return () => { markers.current.forEach((x) => x.remove()); markers.current = []; m.remove(); map.current = null }
  }, [geo, webgl]) // eslint-disable-line react-hooks/exhaustive-deps

  // Bật/tắt từng tuyến theo chip.
  useEffect(() => {
    const m = map.current
    if (!m) return
    if (m.getLayer('tuyen-moi')) apLoc(m, tuyenHienThi); else m.once('style.load', () => apLoc(m, tuyenHienThi))
  }, [tuyenHienThi, geo])

  useEffect(() => {
    const m = map.current
    if (!m) return
    const ap = () => m.setLayoutProperty('nen', 'visibility', nen === 'osm' ? 'visible' : 'none')
    if (m.getLayer('nen')) ap(); else m.once('style.load', ap)
  }, [nen, geo])

  // Vẽ marker các vị trí cột (HTML) — không cần glyph/font cho nhãn.
  useEffect(() => {
    const m = map.current
    if (!m) return
    markers.current.forEach((x) => x.remove())
    markers.current = []
    for (const p of poles) {
      if (p.lon == null || p.lat == null) continue
      const chon = p.id === selectedId
      const mk = new Marker({ element: dungMarker(p, chon, () => moi.current.onSelect(p.id)), anchor: 'top', offset: [0, chon ? -11 : -8] })
        .setLngLat([p.lon, p.lat]).addTo(m)
      if (chon) mk.getElement().style.zIndex = '5'
      markers.current.push(mk)
    }
    baoViewport()
  }, [poles, selectedId, geo]) // eslint-disable-line react-hooks/exhaustive-deps

  // Khi chọn vị trí từ ngoài bản đồ (tìm kiếm, danh sách) → đưa vào giữa khung nhìn nếu đang nằm ngoài.
  useEffect(() => {
    const m = map.current
    const p = poles.find((x) => x.id === selectedId)
    if (!m || !p || p.lon == null || p.lat == null) return
    if (!m.getBounds().contains([p.lon, p.lat])) m.easeTo({ center: [p.lon, p.lat], duration: 600 })
  }, [selectedId]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!webgl) return <div role="alert" className="grid h-full min-h-[320px] place-items-center rounded-xl bg-amber2/15 p-4 text-sm">Trình duyệt không bật WebGL nên không vẽ được bản đồ.</div>
  return (
    <div className="relative h-full min-h-[360px] w-full overflow-hidden rounded-xl border border-ink/10">
      <div ref={box} role="application" aria-label="Bản đồ tuyến dây" className="absolute inset-0" />
      <div className="absolute right-3 top-3 z-10 flex flex-col gap-1.5">
        <button onClick={() => map.current?.zoomIn()} aria-label="Phóng to" className="grid size-9 place-items-center rounded-lg bg-white shadow hover:bg-brand-soft"><Plus size={17} /></button>
        <button onClick={() => map.current?.zoomOut()} aria-label="Thu nhỏ" className="grid size-9 place-items-center rounded-lg bg-white shadow hover:bg-brand-soft"><Minus size={17} /></button>
        <div className="relative">
          <button onClick={() => setMoMenu(!moMenu)} aria-label="Lớp bản đồ" aria-expanded={moMenu} className="grid size-9 place-items-center rounded-lg bg-white shadow hover:bg-brand-soft"><Layers size={17} /></button>
          {moMenu && (
            <div className="absolute right-11 top-0 w-44 rounded-lg bg-white p-1.5 text-sm shadow-lg">
              {([['osm', 'Bản đồ nền (OSM)'], ['trang', 'Chỉ tuyến, không nền']] as const).map(([k, t]) => (
                <button key={k} onClick={() => { setNen(k); setMoMenu(false) }} className={clsx('block w-full rounded-md px-2.5 py-2 text-left hover:bg-brand-soft', nen === k && 'bg-brand-soft font-semibold')}>{t}</button>))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
