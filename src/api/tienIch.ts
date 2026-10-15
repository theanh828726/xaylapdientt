import { http } from './client'
import type { KetQuaTim, ThongBao } from '../types'

export interface Dem { loiChan: number; choToi: number; chuaDoc: number; choToiItems: { ma: string; nhan: string; tieuDe: string; lienKet: string }[] }
/** Số trên huy hiệu menu và chuông thông báo. */
export const getDem = () => http<Dem>('/tong-quan/dem')
export const timKiem = (q: string) => http<KetQuaTim[]>(`/tim-kiem?q=${encodeURIComponent(q)}`)
export const getThongBao = () => http<{ chuaDoc: number; items: ThongBao[] }>('/thong-bao')
export const docTatCaThongBao = () => http<void>('/thong-bao/doc-tat-ca', { method: 'POST' })
