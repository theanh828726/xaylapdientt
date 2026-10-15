"""khoi tao schema

Revision ID: be7bc6ecab27
Revises: 
Create Date: 2026-10-14 12:50:30.898954
"""
from alembic import op
import sqlalchemy as sa
import geoalchemy2
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision = 'be7bc6ecab27'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis')
    op.create_table('du_an',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('ma', sa.String(length=40), nullable=False),
    sa.Column('ten', sa.String(length=200), nullable=False),
    sa.Column('chu_dau_tu', sa.String(length=200), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_du_an')),
    sa.UniqueConstraint('ma', name=op.f('uq_du_an_ma'))
    )
    op.create_table('nguoi_dung',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('mat_khau_hash', sa.String(length=255), nullable=False),
    sa.Column('ho_ten', sa.String(length=120), nullable=False),
    sa.Column('vai_tro', sa.Enum('giam_doc', 'chi_huy_truong', 'ky_thuat', 'ke_toan', 'phong_ke_hoach', 'pho_giam_doc', 'chu_tich', name='vai_tro', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('don_vi', sa.String(length=120), nullable=True),
    sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_nguoi_dung')),
    sa.UniqueConstraint('email', name=op.f('uq_nguoi_dung_email'))
    )
    op.create_table('role_permission',
    sa.Column('vai_tro', sa.Enum('giam_doc', 'chi_huy_truong', 'ky_thuat', 'ke_toan', 'phong_ke_hoach', 'pho_giam_doc', 'chu_tich', name='vai_tro', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('quyen', sa.String(length=60), nullable=False),
    sa.PrimaryKeyConstraint('vai_tro', 'quyen', name=op.f('pk_role_permission'))
    )
    op.create_table('rule_def',
    sa.Column('ma', sa.String(length=8), nullable=False),
    sa.Column('ten', sa.String(length=300), nullable=False),
    sa.Column('muc', sa.Enum('Chặn', 'Cảnh báo', 'Nhắc việc', name='muc_rule', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('module', sa.String(length=8), nullable=False),
    sa.Column('mo_ta', sa.String(length=500), server_default='', nullable=False),
    sa.PrimaryKeyConstraint('ma', name=op.f('pk_rule_def'))
    )
    op.create_table('audit_log',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('du_an_id', sa.Uuid(), nullable=True),
    sa.Column('nguoi_dung_id', sa.Uuid(), nullable=True),
    sa.Column('hanh_dong', sa.String(length=60), nullable=False),
    sa.Column('bang', sa.String(length=60), nullable=False),
    sa.Column('doi_tuong_id', sa.String(length=64), nullable=True),
    sa.Column('truoc', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('sau', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['du_an_id'], ['du_an.id'], name=op.f('fk_audit_log_du_an_id_du_an'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['nguoi_dung_id'], ['nguoi_dung.id'], name=op.f('fk_audit_log_nguoi_dung_id_nguoi_dung'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_log'))
    )
    op.create_index(op.f('ix_audit_log_du_an_id'), 'audit_log', ['du_an_id'], unique=False)
    op.create_table('buoc_duyet',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('doi_tuong', sa.Enum('de_xuat', 'phieu_dc', name='doi_tuong_duyet', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('doi_tuong_id', sa.Uuid(), nullable=False),
    sa.Column('thu_tu', sa.SmallInteger(), nullable=False),
    sa.Column('vai_tro', sa.Enum('giam_doc', 'chi_huy_truong', 'ky_thuat', 'ke_toan', 'phong_ke_hoach', 'pho_giam_doc', 'chu_tich', name='vai_tro', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('nguoi_phu_trach_id', sa.Uuid(), nullable=True),
    sa.Column('nguoi_duyet_id', sa.Uuid(), nullable=True),
    sa.Column('trang_thai', sa.Enum('xong', 'dang', 'cho', 'tu_choi', name='buoc_trang_thai', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('thoi_gian', sa.DateTime(timezone=True), nullable=True),
    sa.Column('ly_do', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['nguoi_duyet_id'], ['nguoi_dung.id'], name=op.f('fk_buoc_duyet_nguoi_duyet_id_nguoi_dung'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['nguoi_phu_trach_id'], ['nguoi_dung.id'], name=op.f('fk_buoc_duyet_nguoi_phu_trach_id_nguoi_dung'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_buoc_duyet')),
    sa.UniqueConstraint('doi_tuong', 'doi_tuong_id', 'thu_tu', name=op.f('uq_buoc_duyet_doi_tuong'))
    )
    op.create_index('ix_buoc_duyet_doi_tuong', 'buoc_duyet', ['doi_tuong', 'doi_tuong_id'], unique=False)
    op.create_table('de_xuat_vat_tu',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('du_an_id', sa.Uuid(), nullable=False),
    sa.Column('ma', sa.String(length=40), nullable=False),
    sa.Column('cong_trinh', sa.String(length=300), nullable=False),
    sa.Column('nguoi_lap_id', sa.Uuid(), nullable=False),
    sa.Column('ngay_lap', sa.Date(), nullable=False),
    sa.Column('gia_hop_dong', sa.BigInteger(), nullable=True),
    sa.Column('gia_khoan', sa.BigInteger(), nullable=True),
    sa.Column('trang_thai', sa.Enum('cho_duyet', 'da_duyet', 'tu_choi', name='trang_thai_duyet', native_enum=False, create_constraint=True, length=32), server_default='cho_duyet', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['du_an_id'], ['du_an.id'], name=op.f('fk_de_xuat_vat_tu_du_an_id_du_an'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['nguoi_lap_id'], ['nguoi_dung.id'], name=op.f('fk_de_xuat_vat_tu_nguoi_lap_id_nguoi_dung')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_de_xuat_vat_tu')),
    sa.UniqueConstraint('du_an_id', 'ma', name=op.f('uq_de_xuat_vat_tu_du_an_id'))
    )
    op.create_index(op.f('ix_de_xuat_vat_tu_du_an_id'), 'de_xuat_vat_tu', ['du_an_id'], unique=False)
    op.create_table('doi_soat',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('du_an_id', sa.Uuid(), nullable=False),
    sa.Column('thong_so', sa.String(length=200), nullable=False),
    sa.Column('hop_dong', sa.String(length=120), nullable=False),
    sa.Column('ban_ve', sa.String(length=120), nullable=False),
    sa.Column('chi_dan', sa.String(length=120), nullable=False),
    sa.Column('ai_de_xuat', sa.Text(), nullable=False),
    sa.Column('quyet_dinh', sa.Enum('chap_nhan', 'hoi_tvgs', name='quyet_dinh_doi_soat', native_enum=False, create_constraint=True, length=32), nullable=True),
    sa.Column('nguoi_xac_nhan_id', sa.Uuid(), nullable=True),
    sa.Column('xac_nhan_luc', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['du_an_id'], ['du_an.id'], name=op.f('fk_doi_soat_du_an_id_du_an'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['nguoi_xac_nhan_id'], ['nguoi_dung.id'], name=op.f('fk_doi_soat_nguoi_xac_nhan_id_nguoi_dung'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_doi_soat'))
    )
    op.create_index(op.f('ix_doi_soat_du_an_id'), 'doi_soat', ['du_an_id'], unique=False)
    op.create_table('dot_giao_hang',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('du_an_id', sa.Uuid(), nullable=False),
    sa.Column('po', sa.String(length=40), nullable=False),
    sa.Column('dot', sa.SmallInteger(), nullable=False),
    sa.Column('ngay_du_kien', sa.Date(), nullable=False),
    sa.Column('dia_diem', sa.String(length=200), nullable=False),
    sa.Column('trang_thai', sa.Enum('da_giao', 'tren_duong', 'cho_giao', name='giao_hang_tt', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('hang', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['du_an_id'], ['du_an.id'], name=op.f('fk_dot_giao_hang_du_an_id_du_an'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_dot_giao_hang'))
    )
    op.create_index(op.f('ix_dot_giao_hang_du_an_id'), 'dot_giao_hang', ['du_an_id'], unique=False)
    op.create_table('kho',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('du_an_id', sa.Uuid(), nullable=False),
    sa.Column('parent_id', sa.Uuid(), nullable=True),
    sa.Column('ten', sa.String(length=200), nullable=False),
    sa.Column('cap', sa.Enum('Công ty', 'Công trường', 'Tổ đội', name='cap_kho', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('ton', sa.Numeric(precision=16, scale=3), server_default='0', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['du_an_id'], ['du_an.id'], name=op.f('fk_kho_du_an_id_du_an'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['parent_id'], ['kho.id'], name=op.f('fk_kho_parent_id_kho'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_kho'))
    )
    op.create_index(op.f('ix_kho_du_an_id'), 'kho', ['du_an_id'], unique=False)
    op.create_index(op.f('ix_kho_parent_id'), 'kho', ['parent_id'], unique=False)
    op.create_table('ma_cau_kien',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('du_an_id', sa.Uuid(), nullable=False),
    sa.Column('ma', sa.String(length=40), nullable=False),
    sa.Column('ten', sa.String(length=200), nullable=False),
    sa.Column('dvt', sa.String(length=20), nullable=False),
    sa.Column('dinh_muc', sa.Numeric(precision=14, scale=3), nullable=False),
    sa.Column('ton_kho', sa.Numeric(precision=14, scale=3), server_default='0', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['du_an_id'], ['du_an.id'], name=op.f('fk_ma_cau_kien_du_an_id_du_an'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ma_cau_kien')),
    sa.UniqueConstraint('du_an_id', 'ma', name=op.f('uq_ma_cau_kien_du_an_id'))
    )
    op.create_index(op.f('ix_ma_cau_kien_du_an_id'), 'ma_cau_kien', ['du_an_id'], unique=False)
    op.create_table('phieu_dieu_chinh',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('du_an_id', sa.Uuid(), nullable=False),
    sa.Column('ma', sa.String(length=40), nullable=False),
    sa.Column('ly_do', sa.Text(), nullable=False),
    sa.Column('ngay', sa.Date(), nullable=False),
    sa.Column('nguoi_lap_id', sa.Uuid(), nullable=True),
    sa.Column('trang_thai', sa.Enum('cho_duyet', 'da_duyet', 'tu_choi', name='trang_thai_duyet', native_enum=False, create_constraint=True, length=32), server_default='cho_duyet', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['du_an_id'], ['du_an.id'], name=op.f('fk_phieu_dieu_chinh_du_an_id_du_an'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['nguoi_lap_id'], ['nguoi_dung.id'], name=op.f('fk_phieu_dieu_chinh_nguoi_lap_id_nguoi_dung')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_phieu_dieu_chinh')),
    sa.UniqueConstraint('du_an_id', 'ma', name=op.f('uq_phieu_dieu_chinh_du_an_id'))
    )
    op.create_index(op.f('ix_phieu_dieu_chinh_du_an_id'), 'phieu_dieu_chinh', ['du_an_id'], unique=False)
    op.create_table('refresh_token',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('nguoi_dung_id', sa.Uuid(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['nguoi_dung_id'], ['nguoi_dung.id'], name=op.f('fk_refresh_token_nguoi_dung_id_nguoi_dung'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_refresh_token')),
    sa.UniqueConstraint('token_hash', name=op.f('uq_refresh_token_token_hash'))
    )
    op.create_index(op.f('ix_refresh_token_nguoi_dung_id'), 'refresh_token', ['nguoi_dung_id'], unique=False)
    op.create_table('thanh_vien_du_an',
    sa.Column('du_an_id', sa.Uuid(), nullable=False),
    sa.Column('nguoi_dung_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['du_an_id'], ['du_an.id'], name=op.f('fk_thanh_vien_du_an_du_an_id_du_an'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['nguoi_dung_id'], ['nguoi_dung.id'], name=op.f('fk_thanh_vien_du_an_nguoi_dung_id_nguoi_dung'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('du_an_id', 'nguoi_dung_id', name=op.f('pk_thanh_vien_du_an'))
    )
    op.create_geospatial_table('tuyen',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('du_an_id', sa.Uuid(), nullable=False),
    sa.Column('ten', sa.String(length=200), nullable=False),
    sa.Column('nguon', sa.String(length=20), server_default='demo', nullable=False),
    sa.Column('geom', Geometry(geometry_type='LINESTRING', srid=4326, dimension=2, spatial_index=False, from_text='ST_GeomFromEWKT', name='geometry', nullable=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['du_an_id'], ['du_an.id'], name=op.f('fk_tuyen_du_an_id_du_an'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_tuyen'))
    )
    op.create_geospatial_index('idx_tuyen_geom', 'tuyen', ['geom'], unique=False, postgresql_using='gist', postgresql_ops={})
    op.create_index(op.f('ix_tuyen_du_an_id'), 'tuyen', ['du_an_id'], unique=False)
    op.create_table('de_xuat_dong',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('de_xuat_id', sa.Uuid(), nullable=False),
    sa.Column('thu_tu', sa.SmallInteger(), nullable=False),
    sa.Column('ma_cau_kien_id', sa.Uuid(), nullable=True),
    sa.Column('ma_ck', sa.String(length=40), nullable=False),
    sa.Column('ten', sa.String(length=200), nullable=False),
    sa.Column('dvt', sa.String(length=20), nullable=False),
    sa.Column('theo_dinh_muc', sa.Numeric(precision=14, scale=3), nullable=False),
    sa.Column('de_xuat', sa.Numeric(precision=14, scale=3), nullable=False),
    sa.Column('ton_kho', sa.Numeric(precision=14, scale=3), nullable=False),
    sa.ForeignKeyConstraint(['de_xuat_id'], ['de_xuat_vat_tu.id'], name=op.f('fk_de_xuat_dong_de_xuat_id_de_xuat_vat_tu'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['ma_cau_kien_id'], ['ma_cau_kien.id'], name=op.f('fk_de_xuat_dong_ma_cau_kien_id_ma_cau_kien'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_de_xuat_dong'))
    )
    op.create_index(op.f('ix_de_xuat_dong_de_xuat_id'), 'de_xuat_dong', ['de_xuat_id'], unique=False)
    op.create_geospatial_table('vi_tri_cot',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('du_an_id', sa.Uuid(), nullable=False),
    sa.Column('tuyen_id', sa.Uuid(), nullable=True),
    sa.Column('ten', sa.String(length=40), nullable=False),
    sa.Column('km', sa.Numeric(precision=8, scale=3), nullable=False),
    sa.Column('loai_mong', sa.String(length=60), nullable=False),
    sa.Column('a', sa.Numeric(precision=8, scale=3), nullable=False),
    sa.Column('b', sa.Numeric(precision=8, scale=3), nullable=False),
    sa.Column('h', sa.Numeric(precision=8, scale=3), nullable=False),
    sa.Column('k', sa.Numeric(precision=8, scale=3), nullable=False),
    sa.Column('trang_thai', sa.Enum('chua_lam', 'dang_lam', 'nghiem_thu', 'vuong_gpmb', name='trang_thai_cot', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('tien_do', sa.SmallInteger(), server_default='0', nullable=False),
    sa.Column('canh_bao', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('geom', Geometry(geometry_type='POINT', srid=4326, dimension=2, spatial_index=False, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('tien_do BETWEEN 0 AND 100', name=op.f('ck_vi_tri_cot_tien_do_0_100')),
    sa.ForeignKeyConstraint(['du_an_id'], ['du_an.id'], name=op.f('fk_vi_tri_cot_du_an_id_du_an'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tuyen_id'], ['tuyen.id'], name=op.f('fk_vi_tri_cot_tuyen_id_tuyen'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_vi_tri_cot')),
    sa.UniqueConstraint('du_an_id', 'ten', name=op.f('uq_vi_tri_cot_du_an_id'))
    )
    op.create_geospatial_index('idx_vi_tri_cot_geom', 'vi_tri_cot', ['geom'], unique=False, postgresql_using='gist', postgresql_ops={})
    op.create_index(op.f('ix_vi_tri_cot_du_an_id'), 'vi_tri_cot', ['du_an_id'], unique=False)
    op.create_table('bao_cao_hien_truong',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('du_an_id', sa.Uuid(), nullable=False),
    sa.Column('vi_tri_id', sa.Uuid(), nullable=False),
    sa.Column('nguoi_id', sa.Uuid(), nullable=False),
    sa.Column('ngay', sa.DateTime(timezone=True), nullable=False),
    sa.Column('noi_dung', sa.Text(), nullable=False),
    sa.Column('so_anh', sa.SmallInteger(), server_default='0', nullable=False),
    sa.Column('dong_bo', sa.Enum('da_dong_bo', 'cho_dong_bo', name='dong_bo', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('client_id', sa.Uuid(), nullable=True),
    sa.Column('lat', sa.Numeric(precision=9, scale=6), nullable=True),
    sa.Column('lon', sa.Numeric(precision=9, scale=6), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['du_an_id'], ['du_an.id'], name=op.f('fk_bao_cao_hien_truong_du_an_id_du_an'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['nguoi_id'], ['nguoi_dung.id'], name=op.f('fk_bao_cao_hien_truong_nguoi_id_nguoi_dung')),
    sa.ForeignKeyConstraint(['vi_tri_id'], ['vi_tri_cot.id'], name=op.f('fk_bao_cao_hien_truong_vi_tri_id_vi_tri_cot'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_bao_cao_hien_truong')),
    sa.UniqueConstraint('client_id', name=op.f('uq_bao_cao_hien_truong_client_id'))
    )
    op.create_index(op.f('ix_bao_cao_hien_truong_du_an_id'), 'bao_cao_hien_truong', ['du_an_id'], unique=False)
    op.create_index(op.f('ix_bao_cao_hien_truong_vi_tri_id'), 'bao_cao_hien_truong', ['vi_tri_id'], unique=False)
    op.create_table('nghiem_thu',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('du_an_id', sa.Uuid(), nullable=False),
    sa.Column('vi_tri_id', sa.Uuid(), nullable=False),
    sa.Column('hang_muc', sa.String(length=100), nullable=False),
    sa.Column('phu_luc', sa.String(length=60), nullable=False),
    sa.Column('trang_thai', sa.Enum('dat', 'thieu_ho_so', 'chua_du_dieu_kien', name='nghiem_thu_tt', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['du_an_id'], ['du_an.id'], name=op.f('fk_nghiem_thu_du_an_id_du_an'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['vi_tri_id'], ['vi_tri_cot.id'], name=op.f('fk_nghiem_thu_vi_tri_id_vi_tri_cot'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_nghiem_thu'))
    )
    op.create_index(op.f('ix_nghiem_thu_du_an_id'), 'nghiem_thu', ['du_an_id'], unique=False)
    op.create_index(op.f('ix_nghiem_thu_vi_tri_id'), 'nghiem_thu', ['vi_tri_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_nghiem_thu_vi_tri_id'), table_name='nghiem_thu')
    op.drop_index(op.f('ix_nghiem_thu_du_an_id'), table_name='nghiem_thu')
    op.drop_table('nghiem_thu')
    op.drop_index(op.f('ix_bao_cao_hien_truong_vi_tri_id'), table_name='bao_cao_hien_truong')
    op.drop_index(op.f('ix_bao_cao_hien_truong_du_an_id'), table_name='bao_cao_hien_truong')
    op.drop_table('bao_cao_hien_truong')
    op.drop_index(op.f('ix_vi_tri_cot_du_an_id'), table_name='vi_tri_cot')
    op.drop_geospatial_index('idx_vi_tri_cot_geom', table_name='vi_tri_cot', postgresql_using='gist', column_name='geom')
    op.drop_geospatial_table('vi_tri_cot')
    op.drop_index(op.f('ix_de_xuat_dong_de_xuat_id'), table_name='de_xuat_dong')
    op.drop_table('de_xuat_dong')
    op.drop_index(op.f('ix_tuyen_du_an_id'), table_name='tuyen')
    op.drop_geospatial_index('idx_tuyen_geom', table_name='tuyen', postgresql_using='gist', column_name='geom')
    op.drop_geospatial_table('tuyen')
    op.drop_table('thanh_vien_du_an')
    op.drop_index(op.f('ix_refresh_token_nguoi_dung_id'), table_name='refresh_token')
    op.drop_table('refresh_token')
    op.drop_index(op.f('ix_phieu_dieu_chinh_du_an_id'), table_name='phieu_dieu_chinh')
    op.drop_table('phieu_dieu_chinh')
    op.drop_index(op.f('ix_ma_cau_kien_du_an_id'), table_name='ma_cau_kien')
    op.drop_table('ma_cau_kien')
    op.drop_index(op.f('ix_kho_parent_id'), table_name='kho')
    op.drop_index(op.f('ix_kho_du_an_id'), table_name='kho')
    op.drop_table('kho')
    op.drop_index(op.f('ix_dot_giao_hang_du_an_id'), table_name='dot_giao_hang')
    op.drop_table('dot_giao_hang')
    op.drop_index(op.f('ix_doi_soat_du_an_id'), table_name='doi_soat')
    op.drop_table('doi_soat')
    op.drop_index(op.f('ix_de_xuat_vat_tu_du_an_id'), table_name='de_xuat_vat_tu')
    op.drop_table('de_xuat_vat_tu')
    op.drop_index('ix_buoc_duyet_doi_tuong', table_name='buoc_duyet')
    op.drop_table('buoc_duyet')
    op.drop_index(op.f('ix_audit_log_du_an_id'), table_name='audit_log')
    op.drop_table('audit_log')
    op.drop_table('rule_def')
    op.drop_table('role_permission')
    op.drop_table('nguoi_dung')
    op.drop_table('du_an')
