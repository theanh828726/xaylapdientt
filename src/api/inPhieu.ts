import { taiVeMay } from './client'

/** Xuất phiếu .docx theo mẫu của dự án (giá chỉ xuất hiện nếu người in có quyền xem giá). */
export const inDeXuat = (id: string) => taiVeMay(`/de-xuat-vat-tu/${id}/in`)
export const inPhieuDieuChinh = (id: string) => taiVeMay(`/phieu-dieu-chinh/${id}/in`)
