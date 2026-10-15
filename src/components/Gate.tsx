import type { ReactNode } from 'react'
import { useRole } from '../lib/role'
import { Loading } from './ui'
import Login from '../pages/Login'

// Chưa đăng nhập thì chỉ thấy màn hình đăng nhập; mọi dữ liệu còn lại do backend kiểm soát quyền.
export default function Gate({ children }: { children: ReactNode }) {
  const { ready, user } = useRole()
  if (!ready) return <Loading />
  return user ? children : <Login />
}
