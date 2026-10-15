#!/usr/bin/env bash
# Sao lưu TuyếnSố: cơ sở dữ liệu (pg_dump) + ảnh/biên bản (MinIO). Chạy ở thư mục gốc dự án (nơi có docker-compose.yml).
#   ./scripts/sao_luu.sh                 # tạo backups/<ngày-giờ>/ và xoá bản cũ hơn 14 ngày
#   KEEP_DAYS=30 BACKUP_DIR=/mnt/backup ./scripts/sao_luu.sh
# Cron (mỗi ngày 02:00):  0 2 * * * cd /opt/tuyenso && ./scripts/sao_luu.sh >> backups/sao_luu.log 2>&1
# Bản sao nằm cùng máy chủ KHÔNG đủ an toàn: hãy chép thư mục backups/ sang nơi khác (máy khác, ổ khác, kho đám mây).
set -euo pipefail

cd "$(dirname "$0")/.."
BACKUP_DIR="${BACKUP_DIR:-backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"
DIR="$BACKUP_DIR/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$DIR"

set -a; . ./.env; set +a
echo "[$(date '+%F %T')] Sao lưu cơ sở dữ liệu…"
docker compose exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$DIR/db.dump"
echo "[$(date '+%F %T')] Sao lưu ảnh và biên bản (MinIO)…"
docker compose exec -T api python -m scripts.kho_tar xuat > "$DIR/minio.tar"

# Kiểm tra tệp sao lưu đọc được trước khi coi là thành công.
docker compose exec -T db pg_restore -l < "$DIR/db.dump" > /dev/null
tar -tf "$DIR/minio.tar" > /dev/null
( cd "$DIR" && sha256sum db.dump minio.tar > SHA256SUMS )

find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +"$KEEP_DAYS" -exec rm -rf {} +
echo "[$(date '+%F %T')] Xong: $DIR ($(du -sh "$DIR" | cut -f1))"
