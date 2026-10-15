import { Component, type ReactNode } from 'react'
import { AlertTriangle } from 'lucide-react'

interface State { error: Error | null }

/** Hiển thị lỗi tải dữ liệu (API) thay vì màn hình trắng. Đổi `key` (theo route) để reset. */
export default class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null }
  static getDerivedStateFromError(error: Error): State { return { error } }
  render() {
    const { error } = this.state
    if (!error) return this.props.children
    const forbidden = (error as { status?: number }).status === 403
    return (
      <div role="alert" className="card p-6 max-w-xl">
        <div className="flex items-center gap-2 font-semibold text-danger"><AlertTriangle size={18} />{forbidden ? 'Không có quyền truy cập' : 'Không tải được dữ liệu'}</div>
        <p className="mt-2 text-sm">{error.message}</p>
        <button className="btn-ghost mt-4" onClick={() => this.setState({ error: null })}>Thử lại</button>
      </div>
    )
  }
}
