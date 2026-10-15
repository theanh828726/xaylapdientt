// Điểm duy nhất giao tiếp với backend FastAPI (/api). Component chỉ gọi hàm trong src/api/.
// Access token giữ trong bộ nhớ; refresh token là cookie HttpOnly do server đặt (dev: Vite proxy /api → :8000).
import type { Session } from '../types'

export const BASE_URL = import.meta.env.VITE_API_URL ?? ''
const DU_AN_KEY = 'tuyenso.duAn'

let accessToken: string | null = null
let onUnauthorized: (() => void) | null = null

export const setAccessToken = (t: string | null) => { accessToken = t }
export const setOnUnauthorized = (fn: (() => void) | null) => { onUnauthorized = fn }
export const getDuAnId = (): string | null => { try { return localStorage.getItem(DU_AN_KEY) } catch { return null } }
export const setDuAnId = (id: string | null) => {
  try { if (id) localStorage.setItem(DU_AN_KEY, id); else localStorage.removeItem(DU_AN_KEY) } catch { /* private mode */ }
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) { super(message); this.status = status }
}

async function detail(r: Response): Promise<string> {
  try {
    const d = (await r.json()).detail
    if (typeof d === 'string') return d
    if (Array.isArray(d)) return d.map((e) => e.msg).join('; ')
  } catch { /* không phải JSON */ }
  return `Lỗi ${r.status}`
}

let refreshing: Promise<Session | null> | null = null
/** Đổi cookie refresh lấy access token mới. Gọi song song dùng chung một request (token xoay vòng). */
export function refreshSession(): Promise<Session | null> {
  refreshing ??= fetch(`${BASE_URL}/api/auth/refresh`, { method: 'POST', credentials: 'include' })
    .then(async (r) => {
      if (!r.ok) { setAccessToken(null); return null }
      const s: Session = await r.json()
      setAccessToken(s.accessToken)
      return s
    })
    .catch(() => null)
    .finally(() => { refreshing = null })
  return refreshing
}

type Init = Omit<RequestInit, 'body'> & { json?: unknown; form?: FormData }

/** Gửi request kèm token/dự án; gặp 401 thì refresh một lần rồi gửi lại. Trả về Response chưa đọc body. */
async function request(path: string, init: Init = {}): Promise<Response> {
  const { json, form, headers, ...rest } = init
  const send = () => {
    const duAn = getDuAnId()
    return fetch(`${BASE_URL}/api${path}`, {
      ...rest,
      credentials: 'include',
      headers: {
        ...(json !== undefined && { 'Content-Type': 'application/json' }),
        ...(accessToken && { Authorization: `Bearer ${accessToken}` }),
        ...(duAn && { 'X-Du-An': duAn }),
        ...headers,
      },
      body: form ?? (json !== undefined ? JSON.stringify(json) : undefined),  // FormData: trình duyệt tự đặt boundary
    })
  }
  let r = await send()
  if (r.status === 401 && !path.startsWith('/auth/')) {
    if (await refreshSession()) r = await send()
    else onUnauthorized?.()
  }
  if (!r.ok) throw new ApiError(r.status, await detail(r))
  return r
}

export async function http<T>(path: string, init: Init = {}): Promise<T> {
  const r = await request(path, init)
  return r.status === 204 ? (undefined as T) : r.json()
}

/** Tải tệp nhị phân (ảnh, .docx) qua API có xác thực; <img src> không gửi được header nên phải đi qua blob. */
export async function httpBlob(path: string, init: Init = {}): Promise<{ blob: Blob; tenFile: string }> {
  const r = await request(path, init)
  const cd = r.headers.get('Content-Disposition') ?? ''
  const utf8 = /filename\*=UTF-8''([^;]+)/i.exec(cd)?.[1]
  const tenFile = utf8 ? decodeURIComponent(utf8) : /filename="?([^";]+)"?/i.exec(cd)?.[1] ?? 'tai-lieu'
  return { blob: await r.blob(), tenFile }
}

/** Tải về máy bằng liên kết tạm. */
export async function taiVeMay(path: string, init: Init = {}): Promise<string> {
  const { blob, tenFile } = await httpBlob(path, init)
  const url = URL.createObjectURL(blob)
  const a = Object.assign(document.createElement('a'), { href: url, download: tenFile })
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 10_000)
  return tenFile
}
