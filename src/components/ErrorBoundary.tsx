import { Component, type ReactNode } from 'react'
import { AlertTriangle } from 'lucide-react'
import { ApiError } from '../api/client'

interface State { error: Error | null }

/** Hiển thị lỗi tải dữ liệu (API) thay vì màn hình trắng. Đổi `key` (theo route) để reset. */
export default class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null }
  static getDerivedStateFromError(error: Error): State { return { error } }
  componentDidCatch(error: Error) { if (!(error instanceof ApiError)) console.error('Lỗi giao diện:', error) }
  render() {
    const { error } = this.state
    if (!error) return this.props.children
    const forbidden = (error as { status?: number }).status === 403
    // Lỗi từ máy chủ có câu tiếng Việt dành cho người dùng; lỗi mã nguồn thì chỉ ghi vào console, không đưa ra màn hình.
    const message = error instanceof ApiError ? error.message : 'Đã xảy ra lỗi ngoài dự kiến. Hãy thử lại; nếu vẫn lỗi, báo cho quản trị viên kèm tên màn hình đang mở.'
    return (
      <div role="alert" className="card p-6 max-w-xl">
        <div className="flex items-center gap-2 font-semibold text-danger"><AlertTriangle size={18} />{forbidden ? 'Không có quyền truy cập' : 'Không tải được dữ liệu'}</div>
        <p className="mt-2 text-sm">{message}</p>
        <button className="btn-ghost mt-4" onClick={() => this.setState({ error: null })}>Thử lại</button>
      </div>
    )
  }
}
