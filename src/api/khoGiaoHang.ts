import { http } from './client'
import type { DotGiaoHang, MaCauKien, NodeKho } from '../types'

export const getKho = () => http<NodeKho>('/kho')
export const listDotGiaoHang = () => http<DotGiaoHang[]>('/dot-giao-hang')
export const listMaCauKien = () => http<MaCauKien[]>('/ma-cau-kien')
