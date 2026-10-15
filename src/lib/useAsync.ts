import { useEffect, useState } from 'react'

/** Gọi hàm async một lần khi mount. Lỗi được ném lại lúc render để ErrorBoundary hiển thị (thay vì treo "Đang tải…"). */
export function useAsync<T>(fn: () => Promise<T>): T | undefined {
  const [d, setD] = useState<T>()
  const [err, setErr] = useState<unknown>()
  useEffect(() => {
    let ok = true
    fn().then((v) => ok && setD(v), (e) => ok && setErr(e))
    return () => { ok = false }
  }, []) // eslint-disable-line
  if (err) throw err
  return d
}
