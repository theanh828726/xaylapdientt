import { http } from './client'
import type { DoiSoatDong, DoiSoatHangMuc, DoiSoatHangMucTom } from '../types'

export const listHangMucDoiSoat = () => http<DoiSoatHangMucTom[]>('/doi-soat/hang-muc')
export const getHangMucDoiSoat = (id: string) => http<DoiSoatHangMuc>(`/doi-soat/hang-muc/${id}`)
export const xacNhanDoiSoat = (id: string, quyetDinh: 'chap_nhan' | 'hoi_tvgs') =>
  http<DoiSoatDong>(`/doi-soat/${id}/quyet-dinh`, { method: 'POST', json: { quyetDinh } })
/** Tạo phiếu xử lý (thông số lệch) hoặc lập phát sinh (thiếu trong một nguồn): mở phiếu điều chỉnh đi qua chuỗi duyệt. */
export const taoPhieuDoiSoat = (id: string) => http<DoiSoatDong>(`/doi-soat/${id}/tao-phieu`, { method: 'POST' })
