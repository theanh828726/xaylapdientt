import { http, httpBlob } from './client'
import type { AnhMeta, BaoCaoHienTruong, BaoCaoInput } from '../types'

export interface LocBaoCao { limit?: number; offset?: number; tu?: string; den?: string; viTri?: string }
/** Mới nhất trước, tối đa 200 dòng/lần; dùng offset để tải thêm. */
export const listBaoCao = (loc: LocBaoCao = {}) => {
  const q = new URLSearchParams()
  if (loc.limit) q.set('limit', String(loc.limit))
  if (loc.offset) q.set('offset', String(loc.offset))
  if (loc.tu) q.set('tu', loc.tu)
  if (loc.den) q.set('den', loc.den)
  if (loc.viTri) q.set('vi_tri', loc.viTri)
  const s = q.toString()
  return http<BaoCaoHienTruong[]>(`/bao-cao-hien-truong${s ? `?${s}` : ''}`)
}
/** Idempotent theo clientId: gửi lại cùng clientId không tạo bản sao. */
export const taoBaoCao = (b: BaoCaoInput) => http<BaoCaoHienTruong>('/bao-cao-hien-truong', { method: 'POST', json: b })
export const listAnh = (baoCaoId: string) => http<AnhMeta[]>(`/bao-cao-hien-truong/${baoCaoId}/anh`)
/** Tải ảnh lên kho lưu trữ; clientId cố định cho mỗi tệp nên thử lại không tạo ảnh trùng. */
export const taiAnhLen = (baoCaoId: string, file: Blob | File, clientId: string, viTri?: { lat: number; lon: number }) => {
  const form = new FormData()
  form.append('file', file, (file as File).name ?? 'anh.jpg')
  form.append('clientId', clientId)
  if (viTri) { form.append('lat', String(viTri.lat)); form.append('lon', String(viTri.lon)) }
  return http<AnhMeta>(`/bao-cao-hien-truong/${baoCaoId}/anh`, { method: 'POST', form })
}
/** Trả về object URL để gán cho <img>; gọi URL.revokeObjectURL khi không dùng nữa. */
export const layAnhUrl = async (anhId: string) => URL.createObjectURL((await httpBlob(`/anh/${anhId}`)).blob)
