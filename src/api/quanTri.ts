import { http } from './client'
import type { DuAnTom, NguoiDungQT, PhanQuyen } from '../types'

export const listNguoiDung = () => http<NguoiDungQT[]>('/nguoi-dung')
export const listTatCaDuAn = () => http<DuAnTom[]>('/du-an/tat-ca')

export interface NguoiDungMoi { email: string; hoTen: string; vaiTro: string; matKhau: string; donVi?: string; duAnIds: string[] }
export const taoNguoiDung = (b: NguoiDungMoi) => http<NguoiDungQT>('/nguoi-dung', { method: 'POST', json: b })

export interface NguoiDungSua { hoTen?: string; vaiTro?: string; donVi?: string; active?: boolean; matKhau?: string; duAnIds?: string[] }
export const suaNguoiDung = (id: string, b: NguoiDungSua) => http<NguoiDungQT>(`/nguoi-dung/${id}`, { method: 'PATCH', json: b })

export const getPhanQuyen = () => http<PhanQuyen>('/phan-quyen')
export const suaPhanQuyen = (vaiTro: string, quyen: string[]) =>
  http<{ vaiTro: string; quyen: string[] }>(`/phan-quyen/${vaiTro}`, { method: 'PUT', json: { quyen } })
