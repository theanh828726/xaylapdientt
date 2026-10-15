import { http, httpBlob, taiVeMay } from './client'
import type { AnhViTri, FormBaoCao, GeoFeatureCollection, KmzKetQua, Tuyen, ViTriCot, ViTriCotChiTiet } from '../types'

export const listViTriCot = () => http<ViTriCot[]>('/vi-tri-cot')
export const getViTriCot = (id: string) => http<ViTriCotChiTiet>(`/vi-tri-cot/${id}`)
export const getAnhViTri = (id: string) => http<AnhViTri>(`/vi-tri-cot/${id}/anh`)
export const getFormBaoCao = (id: string) => http<FormBaoCao>(`/vi-tri-cot/${id}/bao-cao-form`)
/** Xuất bảng chiết tính hố móng của một vị trí (.docx theo mẫu của dự án). */
export const xuatChietTinhViTri = (id: string) => taiVeMay(`/vi-tri-cot/${id}/chiet-tinh`)
export const listTuyen = () => http<Tuyen[]>('/tuyen')
/** FeatureCollection (tuyến LineString + cột Point, EPSG:4326) cho bản đồ MapLibre. */
export const getBanDoGeoJSON = () => http<GeoFeatureCollection>('/ban-do/geojson')
/** Nhập KMZ/KML: thay tuyến KMZ cũ, cập nhật toạ độ cho cột đã có (khớp theo tên). */
export const importKmz = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return http<KmzKetQua>('/ban-do/import-kmz', { method: 'POST', form })
}
export const layAnhBlobUrl = async (anhId: string) => URL.createObjectURL((await httpBlob(`/anh/${anhId}`)).blob)
