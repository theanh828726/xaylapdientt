import { http } from './client'
import type { HopThu, TrangThaiDuyet } from '../types'

export type LoaiDuyet = 'de_xuat' | 'phieu_dc'
/** Duyệt / từ chối (trả lại) bước hiện tại của chuỗi duyệt; từ chối bắt buộc có lý do, duyệt có thể kèm ghi chú. */
export const duyetBuoc = (loai: LoaiDuyet, id: string, quyetDinh: 'duyet' | 'tu_choi', lyDo?: string) =>
  http<{ trangThai: TrangThaiDuyet; buocHienTai: string | null }>(`/duyet/${loai}/${id}`, { method: 'POST', json: { quyetDinh, lyDo } })
export const getHopThu = (tab: 'cho_toi' | 'cap_khac' | 'da_xu_ly') => http<HopThu>(`/duyet/hop-thu?tab=${tab}`)
