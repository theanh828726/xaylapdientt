import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { login as apiLogin, logout as apiLogout } from '../api'
import { getDuAnId, refreshSession, setAccessToken, setDuAnId, setOnUnauthorized } from '../api/client'
import type { DuAnTom, Session, SessionUser } from '../types'

interface Auth {
  ready: boolean
  user: SessionUser | null
  role: string                       // tên vai trò hiển thị (vd "Chỉ huy trưởng")
  duAn: DuAnTom[]
  duAnId: string | null
  login: (email: string, matKhau: string) => Promise<void>
  logout: () => Promise<void>
  chonDuAn: (id: string) => void
  can: (quyen: string) => boolean
  // Lớp hiển thị giá: quyền lấy từ backend (ma trận phân quyền cấu hình được); backend cũng không trả giá khi thiếu quyền.
  thayGia: boolean
  thayGiaKhoan: boolean
}
const Ctx = createContext<Auth>(null!)

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [session, setSession] = useState<Session | null>(null)
  const [ready, setReady] = useState(false)

  const nhan = useCallback((s: Session | null) => {
    if (s) {
      // dự án đã chọn lần trước có thể không còn thuộc về người dùng này
      if (!s.duAn.some((d) => d.id === getDuAnId())) setDuAnId(s.duAn[0]?.id ?? null)
    } else setDuAnId(null)
    setSession(s)
  }, [])

  useEffect(() => {
    setOnUnauthorized(() => { setAccessToken(null); setSession(null) })
    refreshSession().then(nhan).finally(() => setReady(true))
    return () => setOnUnauthorized(null)
  }, [nhan])

  const value = useMemo<Auth>(() => {
    const quyen = new Set(session?.quyen ?? [])
    const can = (q: string) => quyen.has(q)
    return {
      ready, user: session?.user ?? null, role: session?.user.vaiTroTen ?? '', duAn: session?.duAn ?? [],
      duAnId: session ? getDuAnId() : null,
      login: async (email, matKhau) => { nhan(await apiLogin(email, matKhau)) },
      logout: async () => { try { await apiLogout() } finally { setSession(null) } },
      chonDuAn: (id) => { setDuAnId(id); window.location.reload() },  // tải lại để mọi màn hình lấy dữ liệu dự án mới
      can, thayGia: can('gia_hop_dong.xem'), thayGiaKhoan: can('gia_khoan.xem'),
    }
  }, [session, ready, nhan])

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}
export const useRole = () => useContext(Ctx)
