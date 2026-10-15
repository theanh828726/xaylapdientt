import { http, taiVeMay } from './client'
import type { MauBieuInfo } from '../types'

export const listMauBieu = () => http<MauBieuInfo[]>('/mau-bieu')
/** Tải mẫu về để chỉnh bằng Word (hien-tai = mẫu đang dùng, mac-dinh = mẫu hệ thống). */
export const taiMauVe = (loai: string, nguon: 'hien-tai' | 'mac-dinh') => taiVeMay(`/mau-bieu/${loai}/tai-ve?nguon=${nguon}`)
export const taiMauLen = (loai: string, file: File, ghiChu?: string) => {
  const form = new FormData()
  form.append('file', file)
  if (ghiChu) form.append('ghiChu', ghiChu)
  return http<{ loai: string; phienBan: number }>(`/mau-bieu/${loai}`, { method: 'PUT', form })
}
export const dungMauMacDinh = (loai: string) => http<void>(`/mau-bieu/${loai}`, { method: 'DELETE' })
