/** Khối lượng hố móng: V = h/3·(S1+S2+√(S1·S2)); A1=A+0.4, A2=A1+2Kh */
export function khoiLuongHoMong(A: number, B: number, h: number, K: number) {
  const A1 = A + 0.4, B1 = B + 0.4
  const A2 = A1 + 2 * K * h, B2 = B1 + 2 * K * h
  const S1 = A1 * B1, S2 = A2 * B2
  const V = (h / 3) * (S1 + S2 + Math.sqrt(S1 * S2))
  return { A1, B1, A2, B2, S1, S2, V }
}
export const fmt = (n: number, d = 1) => n.toLocaleString('vi-VN', { minimumFractionDigits: d, maximumFractionDigits: d })
export const vnd = (n: number) => n.toLocaleString('vi-VN') + ' đ'
