import { http, taiVeMay } from './client'
import type { BienBan, LichNen, Nhom, QaqcTongQuan, Rule, ViPham, XemTruoc } from '../types'

export const listRules = () => http<Rule[]>('/quy-tac')
export const listViPham = (nhom?: Nhom) => http<ViPham[]>(`/quy-tac/vi-pham${nhom ? `?nhom=${nhom}` : ''}`)
const q = (tu?: string, den?: string, extra = '') => `?${[tu && `tu=${tu}`, den && `den=${den}`, extra].filter(Boolean).join('&')}`
export const getQaqc = (nhom: Nhom, tu?: string, den?: string) => http<QaqcTongQuan>(`/qaqc/tong-quan${q(tu, den, `nhom=${nhom}`)}`)
export const xemTruocBienBan = (gop: 'vi_tri' | 'doan_ngay', tu?: string, den?: string) =>
  http<XemTruoc>(`/qaqc/sinh-bien-ban/xem-truoc${q(tu, den, `gop=${gop}`)}`)
/** Sinh biên bản hàng loạt (kèm giấy mời + bảng chiết tính), tải về file ZIP các .docx. */
export const sinhBienBanHangLoat = (gop: 'vi_tri' | 'doan_ngay', tu: string, den: string) =>
  taiVeMay('/qaqc/sinh-bien-ban', { method: 'POST', json: { gop, tu, den } })
export const getLichNen = () => http<LichNen[]>('/qaqc/lich-nen')

// Hành động trên từng cảnh báo
export const ganKetQua = (loId: string, ketQua: 'dat' | 'khong_dat', ghiChu?: string) =>
  http<{ id: string; ma: string; ketQua: string }>(`/lo-vat-lieu/${loId}/ket-qua`, { method: 'POST', json: { ketQua, ghiChu } })
export const soanDeTrinh = (loId: string) => taiVeMay(`/lo-vat-lieu/${loId}/de-trinh`, { method: 'POST' })
export const moPhieuDieuChinh = (congTacId: string) => http<{ id: string; ma: string }>(`/cong-tac/${congTacId}/mo-phieu-dieu-chinh`, { method: 'POST' })
export const sinhChietTinh = () => taiVeMay('/qaqc/sinh-chiet-tinh', { method: 'POST' })
export const nhacKyThuat = (dotGiaoId: string) => http<{ message: string }>(`/dot-giao-hang/${dotGiaoId}/nhac`, { method: 'POST' })

export const sinhBienBanCongTac = (id: string, taoLai = false) => http<BienBan>(`/cong-tac/${id}/bien-ban${taoLai ? '?tao_lai=true' : ''}`, { method: 'POST' })
export const listBienBan = () => http<BienBan[]>('/bien-ban')
export const taiBienBan = (id: string) => taiVeMay(`/bien-ban/${id}/tai-ve`)
