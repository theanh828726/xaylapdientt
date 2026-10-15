/** Định dạng hiển thị theo quy ước Việt Nam. */
export const nf = (n: number, toiDa = 3) => n.toLocaleString('vi-VN', { maximumFractionDigits: toiDa })
export const nfCoDinh = (n: number, d: number) => n.toLocaleString('vi-VN', { minimumFractionDigits: d, maximumFractionDigits: d })
export const vnd = (n: number) => n.toLocaleString('vi-VN') + ' đ'
/** "VT45" → "VT 45" (cách viết trong thiết kế). */
export const vtHien = (ten: string) => ten.replace(/^VT(\d+)/, 'VT $1')
/** "2026-10-14" → "14/10"; kèm năm nếu withYear. */
export const dm = (iso: string | null | undefined, withYear = false) => {
  if (!iso) return '—'
  const [y, m, d] = iso.slice(0, 10).split('-')
  return withYear ? `${d}/${m}/${y}` : `${d}/${m}`
}
export const gio = (iso: string) => new Date(iso).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', hour12: false })
export const homNay = () => new Date().toLocaleDateString('sv-SE')   // YYYY-MM-DD theo giờ máy
export const thuNgay = (d = new Date()) => {
  const t = ['Chủ Nhật', 'Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy'][d.getDay()]
  return `${t}, ${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`
}
export const ten2chu = (ten: string) => ten.split(/\s+/).filter(Boolean).slice(-2).map((x) => x[0]).join('').toUpperCase()
export const lamLoi = (e: unknown, mac = 'Thao tác thất bại') => (e instanceof Error ? e.message : mac)
