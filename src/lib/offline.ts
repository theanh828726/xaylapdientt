// Hàng đợi báo cáo hiện trường khi mất mạng: báo cáo + ảnh lưu IndexedDB, gửi lại khi có mạng.
// clientId cố định cho báo cáo và từng ảnh nên gửi lại nhiều lần không tạo bản sao (backend idempotent).
import { taiAnhLen, taoBaoCao } from '../api'
import type { BaoCaoInput } from '../types'

export interface MucCho { clientId: string; baoCao: BaoCaoInput; anh: { clientId: string; blob: Blob; lat?: number; lon?: number }[]; duAnId: string }

const DB = 'tuyenso-offline', KHO = 'hang_doi'
const mo = () => new Promise<IDBDatabase>((ok, loi) => {
  const r = indexedDB.open(DB, 1)
  r.onupgradeneeded = () => r.result.createObjectStore(KHO, { keyPath: 'clientId' })
  r.onsuccess = () => ok(r.result)
  r.onerror = () => loi(r.error)
})
const tx = async <T>(mode: IDBTransactionMode, f: (s: IDBObjectStore) => IDBRequest<T>) => {
  const db = await mo()
  return new Promise<T>((ok, loi) => {
    const q = f(db.transaction(KHO, mode).objectStore(KHO))
    q.onsuccess = () => ok(q.result)
    q.onerror = () => loi(q.error)
  })
}

export const dangCho = () => tx<MucCho[]>('readonly', (s) => s.getAll()).catch(() => [] as MucCho[])
export const luuCho = (m: MucCho) => tx('readwrite', (s) => s.put(m))
const xoaCho = (id: string) => tx('readwrite', (s) => s.delete(id))

/** Gửi một mục: báo cáo trước, ảnh sau; chỉ xoá khỏi hàng đợi khi mọi thứ đã lên server. */
export async function guiMuc(m: MucCho) {
  const bc = await taoBaoCao({ ...m.baoCao, clientId: m.clientId })
  for (const a of m.anh) await taiAnhLen(bc.id, a.blob, a.clientId, a.lat != null && a.lon != null ? { lat: a.lat, lon: a.lon } : undefined)
  await xoaCho(m.clientId)
  return bc
}

/** Đẩy toàn bộ hàng đợi; trả về số mục đã gửi được (mục lỗi giữ lại cho lần sau). */
export async function dongBo(duAnId?: string) {
  let n = 0
  for (const m of await dangCho()) {
    if (duAnId && m.duAnId !== duAnId) continue
    try { await guiMuc(m); n++ } catch { /* giữ lại */ }
  }
  return n
}

/** Xoá bản nháp và hàng đợi trên máy (gọi khi đăng xuất để người dùng sau không thấy dữ liệu của người trước). */
export async function xoaDuLieuMay() {
  try {
    for (const k of Object.keys(localStorage)) if (k.startsWith('tuyenso.nhap.')) localStorage.removeItem(k)
  } catch { /* bỏ qua */ }
  await tx('readwrite', (s) => s.clear()).catch(() => undefined)
}
