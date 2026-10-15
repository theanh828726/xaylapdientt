import { Link } from 'react-router-dom'
import { listTuyen, listViTriCot } from '../api'
import { useAsync } from '../lib/useAsync'
import { vtHien, nf } from '../lib/fmt'
import { Empty, Loading, PageHeader } from '../components/ui'

export default function ThuHoi() {
  const tuyen = useAsync(listTuyen), poles = useAsync(listViTriCot)
  if (!tuyen || !poles) return <Loading />
  const cu = tuyen.filter((t) => t.loai === 'cu')
  return (
    <>
      <PageHeader eyebrow="Sau khi đóng điện tuyến mới" title="Thu hồi tuyến cũ" sub="Các tuyến cũ chờ thu hồi, hiển thị nét đứt trên bản đồ." />
      {cu.length === 0 ? <Empty>Dự án này không có tuyến cũ cần thu hồi.</Empty> : (
        <div className="grid gap-4 md:grid-cols-2">
          {cu.map((t) => {
            const vt = poles.filter((p) => p.tuyenMa === t.ma)
            return (
              <section key={t.id} className="card p-5">
                <h2 className="font-semibold">{t.ten}</h2>
                <p className="mt-1 text-sm text-ink/65"><span className="num">{t.soViTri}</span> vị trí · <span className="num">{nf(t.chieuDaiKm)}</span> km · {t.capDienAp ?? '—'}</p>
                {vt.length > 0 && <p className="mt-2 text-sm">Vị trí: {vt.slice(0, 12).map((p) => <Link key={p.id} to={`/ban-do?vt=${p.id}`} className="mr-2 font-semibold text-brand underline">{vtHien(p.ten)}</Link>)}{vt.length > 12 && '…'}</p>}
                <Link to="/ban-do" className="btn-ghost mt-4">Xem trên bản đồ</Link>
              </section>)
          })}
        </div>)}
      <p className="mt-4 text-xs text-ink/55">Quản lý khối lượng thu hồi và bàn giao vật tư thu hồi sẽ bổ sung khi có thiết kế màn hình.</p>
    </>
  )
}
