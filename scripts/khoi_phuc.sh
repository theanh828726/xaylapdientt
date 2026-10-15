#!/usr/bin/env bash
# Khôi phục TuyếnSố từ một thư mục sao lưu do sao_luu.sh tạo ra. GHI ĐÈ dữ liệu hiện tại.
#   ./scripts/khoi_phuc.sh backups/20261015-020000
# Với kiểm thử khôi phục (không đụng DB thật): DB_TARGET=tuyenso_khoi_phuc_thu ./scripts/khoi_phuc.sh <thư mục> --chi-db
set -euo pipefail

cd "$(dirname "$0")/.."
DIR="${1:?Cách dùng: khoi_phuc.sh <thư-mục-sao-lưu> [--chi-db]}"
[ -f "$DIR/db.dump" ] || { echo "Không thấy $DIR/db.dump"; exit 1; }
set -a; . ./.env; set +a
TARGET="${DB_TARGET:-$POSTGRES_DB}"

( cd "$DIR" && sha256sum -c SHA256SUMS )
if [ "$TARGET" = "$POSTGRES_DB" ]; then
  read -r -p "Sẽ GHI ĐÈ cơ sở dữ liệu '$TARGET'. Gõ 'dong-y' để tiếp tục: " ok
  [ "$ok" = "dong-y" ] || { echo "Đã huỷ."; exit 1; }
  docker compose stop api
fi
docker compose exec -T db psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$TARGET\"" -c "CREATE DATABASE \"$TARGET\""
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$TARGET" -c "CREATE EXTENSION IF NOT EXISTS postgis"
docker compose exec -T db pg_restore -U "$POSTGRES_USER" -d "$TARGET" --no-owner --exit-on-error < "$DIR/db.dump" \
  || { echo "pg_restore báo lỗi (xem phía trên)."; exit 1; }
if [ "${2:-}" != "--chi-db" ] && [ -f "$DIR/minio.tar" ]; then
  docker compose exec -T api python -m scripts.kho_tar nhap < "$DIR/minio.tar"
fi
[ "$TARGET" = "$POSTGRES_DB" ] && docker compose start api
echo "Khôi phục xong vào '$TARGET'."
