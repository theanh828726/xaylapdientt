import { http, setAccessToken } from './client'
import type { Session } from '../types'

export async function login(email: string, matKhau: string): Promise<Session> {
  const s = await http<Session>('/auth/login', { method: 'POST', json: { email, matKhau } })
  setAccessToken(s.accessToken)
  return s
}
export async function logout(): Promise<void> {
  try { await http<void>('/auth/logout', { method: 'POST' }) } finally { setAccessToken(null) }
}
