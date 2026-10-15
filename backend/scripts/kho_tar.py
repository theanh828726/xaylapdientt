"""Xuất/nhập toàn bộ đối tượng trong bucket MinIO/S3 dưới dạng tar (qua stdout/stdin) để sao lưu và khôi phục.

  docker compose exec -T api python -m scripts.kho_tar xuat > minio.tar
  docker compose exec -T api python -m scripts.kho_tar nhap < minio.tar

Chạy trong container api (đã có biến MINIO_* và thư viện minio). Khoá đối tượng giữ nguyên làm tên tệp trong tar.
"""
import io
import sys
import tarfile
import time

from minio import Minio

from app.config import settings


def _client() -> Minio:
    return Minio(settings.minio_endpoint, access_key=settings.minio_root_user,
                 secret_key=settings.minio_root_password, secure=settings.minio_secure)


def xuat() -> int:
    c, n = _client(), 0
    with tarfile.open(fileobj=sys.stdout.buffer, mode="w|") as tar:
        for o in c.list_objects(settings.minio_bucket, recursive=True):
            r = c.get_object(settings.minio_bucket, o.object_name)
            try:
                data = r.read()
            finally:
                r.close()
                r.release_conn()
            info = tarfile.TarInfo(o.object_name)
            info.size, info.mtime = len(data), int(o.last_modified.timestamp()) if o.last_modified else int(time.time())
            tar.addfile(info, io.BytesIO(data))
            n += 1
    print(f"Đã xuất {n} đối tượng", file=sys.stderr)
    return n


def nhap() -> int:
    c, n = _client(), 0
    if not c.bucket_exists(settings.minio_bucket):
        c.make_bucket(settings.minio_bucket)
    with tarfile.open(fileobj=sys.stdin.buffer, mode="r|") as tar:
        for m in tar:
            if not m.isfile() or m.name.startswith(("/", "..")) or ".." in m.name.split("/"):
                continue   # chặn đường dẫn lạ trong tệp sao lưu
            data = tar.extractfile(m).read()
            c.put_object(settings.minio_bucket, m.name, io.BytesIO(data), len(data))
            n += 1
    print(f"Đã nhập {n} đối tượng", file=sys.stderr)
    return n


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("xuat", "nhap"):
        sys.exit("Cách dùng: kho_tar.py xuat|nhap")
    xuat() if sys.argv[1] == "xuat" else nhap()
