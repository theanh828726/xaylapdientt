import { Link } from 'react-router-dom'
import { listBaoCao } from '../api'
import { useAsync } from '../lib/useAsync'
import { nf, vtHien } from '../lib/fmt'
import { Badge, Empty, Loading, PageHeader } from '../components/ui'

export default function NhatKy() {
  const ds = useAsync(listBaoCao)
  if (!ds) return <Loading />
  return (
    <>
      <PageHeader eyebrow="Hiện trường" title="Nhật ký thi công" sub="Báo cáo hằng ngày từ hiện trường — nguồn của biên bản nghiệm thu." actions={<Link to="/bao-cao" className="btn-primary">Báo cáo mới</Link>} />
      {ds.length === 0 ? <Empty>Chưa có báo cáo hiện trường nào.</Empty> : (
        <section className="card overflow-x-auto"><table className="w-full min-w-[760px] text-sm">
          <thead><tr className="bg-paper text-left text-xs font-semibold text-ink/65"><th className="px-4 py-3">Ngày</th><th>Vị trí</th><th>Công tác</th><th>Khối lượng</th><th>Tổ đội · nhân lực</th><th>Ảnh</th><th>Người báo cáo</th><th>Đồng bộ</th></tr></thead>
          <tbody>{ds.map((b) => (
            <tr key={b.id} className="border-t border-ink/8 align-top">
              <td className="num px-4 py-3">{b.ngay}</td>
              <td><Link className="font-semibold text-brand underline" to={`/ban-do?vt=${b.viTriId}`}>{vtHien(b.viTri)}</Link></td>
              <td>{b.congTac ?? '—'}{b.noiDung && <div className="text-xs text-ink/55">{b.noiDung}</div>}</td>
              <td className="num">{b.khoiLuong != null ? nf(b.khoiLuong) : '—'}</td>
              <td>{b.toDoi ?? '—'}{b.nhanLuc != null && <span className="text-ink/55"> · {b.nhanLuc} người</span>}</td>
              <td className="num">{b.anh}</td><td>{b.nguoi}</td>
              <td><Badge tone={b.dongBo === 'da_dong_bo' ? 'ok' : 'warn'}>{b.dongBo === 'da_dong_bo' ? 'Đã đồng bộ' : 'Chờ đồng bộ'}</Badge></td>
            </tr>))}</tbody></table></section>)}
    </>
  )
}
