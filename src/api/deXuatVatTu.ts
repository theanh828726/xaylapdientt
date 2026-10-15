import { http } from './client'
import type { DeXuatVatTu, PhieuDieuChinh } from '../types'

export const listDeXuatVatTu = () => http<DeXuatVatTu[]>('/de-xuat-vat-tu')
export const listPhieuDieuChinh = () => http<PhieuDieuChinh[]>('/phieu-dieu-chinh')
