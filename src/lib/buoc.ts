import type { Buoc } from '../types'

export const BUOC_STYLE: Record<Buoc, { nhan: string; bg: string; vien: string }> = {
  da_keo_day: { nhan: 'Đã kéo dây', bg: '#0F5C55', vien: '#fff' },
  da_dung_cot: { nhan: 'Đã dựng cột, lắp xà', bg: '#2E8C7E', vien: '#fff' },
  mong_da_nghiem_thu: { nhan: 'Móng đã nghiệm thu', bg: '#7FBFB3', vien: '#fff' },
  dang_thi_cong_mong: { nhan: 'Đang thi công móng', bg: '#D8EEE9', vien: '#0F5C55' },
  chua_thi_cong: { nhan: 'Chưa thi công', bg: '#FFFFFF', vien: '#8A958F' },
}
export const BUOC_THU_TU: Buoc[] = ['da_keo_day', 'da_dung_cot', 'mong_da_nghiem_thu', 'dang_thi_cong_mong', 'chua_thi_cong']
