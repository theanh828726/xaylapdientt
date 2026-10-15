// Kiểu dữ liệu trả về từ backend FastAPI (camelCase). 7 entity trung tâm: ViTriCot, MaCauKien, DeXuatVatTu, DotGiaoHang,
// BaoCaoHienTruong, NghiemThu (= công tác + nghiệm thu theo vị trí), PhieuDieuChinh.
export type MucRule = 'Chặn' | 'Cảnh báo' | 'Nhắc việc'
export type Nhom = 'PL1' | 'PL2' | 'PL3' | 'PL4'

// ---------- Vị trí cột / bản đồ ----------
export type Buoc = 'da_keo_day' | 'da_dung_cot' | 'mong_da_nghiem_thu' | 'dang_thi_cong_mong' | 'chua_thi_cong'
export interface ViTriCot {
  id: string; ten: string; km: number; kmText: string; loaiMong: string; kieuCot: string | null
  buoc: Buoc; buocTen: string; tienDo: number; vuongGpmb: boolean
  canhBaoMuc: 'chan' | 'canh_bao' | null; canhBao: string[]
  lon: number | null; lat: number | null; tuyenMa: string | null
}
export interface LichSuCongTac { ma: string; ten: string; ghiChu: string; ngay: string | null; nhan: string; trangThai: 'xong' | 'dang' | 'chua' | 'chan' }
export interface ViTriCotChiTiet {
  id: string; ten: string; kmText: string; kieuCot: string | null; doan: string
  tuyen: { id: string; ma: string; ten: string } | null
  chips: { text: string; tone: 'ok' | 'warn' | 'info' | 'bad' | 'idle' }[]
  canhBao: { ma: string; muc: MucRule; thongBao: string; chiTiet: string | null }[]
  thietKe: { cot: string | null; cotNpc: string | null; mong: string; xa: string | null; tiepDia: string | null; capDat: string | null; khoangCach: string | null }
  chietTinh: { daoDat: number; dienTichMieng: number; dienTichDay: number; ghiChu: string }
  lichSu: LichSuCongTac[]
  vatTu: { ten: string; dvt: string; dinhMuc: number; daCap: number }[]
  nhacVatTu: string | null
  hoSo: { dat: number; tong: number; muc: { ten: string; ok: boolean }[] }
  anh: { tong: number; tep: number }
}
export interface Tuyen { id: string; ma: string; ten: string; capDienAp: string | null; loai: 'moi' | 'cu'; nguon: string; soViTri: number; chieuDaiKm: number; capNhat: string | null }
export interface GeoFeatureCollection {
  type: 'FeatureCollection'
  features: { type: 'Feature'; geometry: { type: string; coordinates: unknown }; properties: Record<string, unknown> }[]
}
export interface KmzKetQua { tuyen: number; cotCapNhat: number; khongKhop: string[] }
export interface AnhMeta { id: string; tenFile: string; mime: string; kichThuoc?: number; baoCaoId?: string; chupLuc?: string | null; lat?: number | null; lon?: number | null }
export interface AnhViTri { khaiBao: number; tep: AnhMeta[] }

// ---------- Rule engine / QA-QC ----------
export interface Rule { ma: string; ten: string; muc: MucRule; nhom: Nhom; moTa: string; trienKhai: boolean; lyDoChuaCo?: string; soViPham: number }
export interface ViPham {
  ma: string; muc: MucRule; nhom: Nhom; loai: string; doiTuongId: string; ten: string; thongBao: string
  chiTiet?: string; hanhDong?: string; viTri?: string; congTac?: string; moc?: string
}
export type TrangThaiO = 'nt' | 'cho' | 'thieu' | 'chan' | 'dang'
export interface OMaTran { state: TrangThaiO; ma?: string[]; nhan?: string | null }
export interface MaTran { cot: { ma: string; ten: string; nhom: string }[]; rows: { viTri: string; viTriHien: string; id: string; cells: Record<string, OMaTran | null> }[] }
export interface QaqcTongQuan {
  nhom: Nhom; nhomTen: string; soQuyTac: number; chayLuc: string; tu: string; den: string
  thongKe: {
    duHoSoMong: { du: number; tong: number }
    bienBanSanSang: { n: number; tu: string; den: string }
    loiChan: { n: number }
    mauChoNen: { n: number; ganNhat: { tuoi: number; ngay: string } | null }
  }
  kiemTra: ViPham[]
  maTran: MaTran
}
export interface XemTruoc {
  tu: string; den: string; gop: 'vi_tri' | 'doan_ngay'; bienBan: number; congTac: number; kemGiayMoi: number; kemChietTinh: number
  soNgayNhatKy: number; sanSang: number; biChan: { n: number; ds: { viTri: string; ma: string[] }[] }
  danhSach: { nhan: string; soCongTac: number }[]
}
export interface LichNen { id: string; maMau: string; viTri: string; congTac: string; ngayDuc: string; tuoiNgay: number; hanNen: string }
export interface BienBan { id: string; doiTuongId?: string; loai?: string; so: string; tenFile: string; mauNguon: string; congTacIds?: string[]; message: string; taoLuc?: string | null }

// ---------- Duyệt / đề xuất / phiếu ----------
export interface BuocDuyet {
  vaiTro: string; vaiTroNgan: string; vaiTroMa: string; nguoi: string; trangThai: 'xong' | 'dang' | 'cho' | 'tu_choi'
  thoiGian: string | null; thoiGianIso: string | null; lyDo: string | null; goiY: string | null
}
export type TrangThaiDuyet = 'cho_duyet' | 'da_duyet' | 'tu_choi'
export interface DongDeXuat {
  maCK: string; ten: string; dvt: string; moTa: string | null; theoDinhMuc: number; daDeXuat: number; conLai: number
  tonKho: number | null; deXuat: number; quyDoi: string | null; canhBao: string | null; hdSoLuong: number | null
}
export interface DeXuatVatTu {
  id: string; ma: string; doan: string | null; congTrinh: string; nguoiLap: string; nguoiLapTen: string; ngayLap: string; canHang: string | null
  giaoTai: string | null; lanDeXuat: number; lyDoVuot: string | null; dong: DongDeXuat[]; chuoiDuyet: BuocDuyet[]
  doiChieu: { khop: number; tong: number; ghiChu: string | null }
  giaHopDong?: number; giaKhoan?: number   // vắng mặt nếu vai trò không đủ quyền (backend không trả)
  trangThai: TrangThaiDuyet; buocHienTai: string | null; vaiTroTiep: string | null; coTheDuyet: boolean
}
export type LoaiPhieu = 'dieu_chinh' | 'nghiem_thu_dk'
export interface PhieuDieuChinh {
  id: string; ma: string; loai: LoaiPhieu; loaiTen: string; tieuDe: string; lyDo: string; ngay: string; trangThai: TrangThaiDuyet
  viTri: string | null; tacDong: string[]; sauDieuChinh: string | null; chuoiDuyet: BuocDuyet[]; buocHienTai: string | null; coTheDuyet: boolean
}
export interface HopThuItem {
  loai: 'de_xuat' | LoaiPhieu; doiTuong: 'de_xuat' | 'phieu_dc'; id: string; ma: string; nhan: string; gio: string; moc: string
  tieuDe: string; lienKet: string; chuoi: { vaiTro: string; ngan: string; trangThai: string }[]
  canhBao: { ma: string; noiDung: string } | null
  chiTiet: { lyDo: string; tacDong: string[]; sauDieuChinh: string | null } | null
  trangThai: TrangThaiDuyet; coTheDuyet: boolean
}
export interface HopThu { tab: string; dem: { choToi: number; capKhac: number; daXuLy: number }; items: HopThuItem[] }

// ---------- Đối soát 3 nguồn ----------
export interface DoiSoatHangMucTom { id: string; ten: string; soCanXuLy: number; soThongSo: number }
export interface BangChung { nguon: string; nhan: string; bbox: { x: number; y: number; w: number; h: number }; tone: 'ok' | 'bad'; chu_thich: string }
export interface DoiSoatDong {
  id: string; thongSo: string; hopDong: string; banVe: string; chiDan: string; trichDan: { hd?: string; bv?: string; cd?: string }
  ketLuan: 'khop' | 'lech' | 'thieu_hd' | 'thieu_bv' | 'thieu_cd'; ketLuanTen: string; tinCay: number | null; aiDeXuat: string
  hanhDong: 'tao_phieu' | 'phat_sinh' | 'xac_nhan'; quyetDinh: 'chap_nhan' | 'hoi_tvgs' | 'da_tao_phieu' | null
  phieu: { id: string; ma: string } | null; bangChung: BangChung[]
}
export interface DoiSoatHangMuc {
  id: string; ten: string; tieuDe: string; nguon: { nhan: string; ten: string; mo_ta: string }[]
  soThongSo: number; soLech: number; soThieu: number; rows: DoiSoatDong[]
}

// ---------- Hiện trường / kho ----------
export interface BaoCaoHienTruong {
  id: string; viTri: string; viTriId: string; ngay: string; ngayIso: string; noiDung: string; anh: number; dongBo: 'da_dong_bo' | 'cho_dong_bo'
  nguoi: string; congTacMa: string | null; congTac: string | null; khoiLuong: number | null; thoiTiet: string | null; toDoi: string | null
  nhanLuc: number | null; mayThiCong: string[]
}
export interface BaoCaoInput {
  viTri: string; noiDung?: string; soAnh?: number; clientId?: string; ngay?: string; lat?: number; lon?: number
  congTacMa?: string; khoiLuong?: number; hoanThanh?: boolean; thoiTiet?: string; toDoi?: string; nhanLuc?: number; mayThiCong?: string[]
}
export interface FormBaoCao {
  viTri: { id: string; ten: string; kmText: string; loaiMong: string; lon: number | null; lat: number | null }
  congTac: { ma: string; ten: string; tenDai: string; trangThai: string; khoa: boolean; lyDoKhoa: string | null }[]
  congTacMacDinh: string | null
  khoiLuongThietKe: { daoMong: number; dvt: string; datCap: string | null }
  canhBao: string[]; toDoi: string[]; mayThiCong: string[]; anhToiThieu: number
}
export interface DotGiaoHang {
  id: string; po: string; dot: number; ngayDuKien: string; diaDiem: string; trangThai: 'da_giao' | 'tren_duong' | 'cho_giao'; hang: string
  nhaCungCap: string | null; ngayNhan: string | null; slDat: number | null; slNhan: number | null; dvt: string | null; coAnhPhuongTien: boolean
}
export interface MaCauKien { id: string; ma: string; ten: string; dvt: string; dinhMuc: number; tonKho: number }
export interface NodeKho { id: string; ten: string; cap: 'Công ty' | 'Công trường' | 'Tổ đội'; ton: number; con?: NodeKho[] }

// ---------- Tìm kiếm, thông báo ----------
export interface KetQuaTim { loai: string; tieuDe: string; phu: string; lienKet: string }
export interface ThongBao { id: string; tieuDe: string; noiDung: string | null; lienKet: string | null; daDoc: boolean; thoiGian: string }

// ---------- Phiên đăng nhập & quản trị ----------
export interface SessionUser { id: string; email: string; hoTen: string; vaiTro: string; vaiTroTen: string; donVi?: string | null }
export interface DuAnTom { id: string; ma: string; ten: string }
export interface Session { accessToken: string; user: SessionUser; quyen: string[]; duAn: DuAnTom[] }
export interface NguoiDungQT { id: string; email: string; hoTen: string; vaiTro: string; vaiTroTen: string; donVi?: string | null; active: boolean; duAnIds: string[] }
export interface PhanQuyen {
  vaiTro: { ma: string; ten: string }[]
  quyen: { ma: string; moTa: string }[]
  maTran: Record<string, string[]>   // vai trò → danh sách quyền
}
export interface MauBieuInfo {
  loai: string; ten: string; nguon: 'mac-dinh' | 'du-an'; phienBan: number; tenFile: string
  ghiChu?: string | null; capNhat?: string | null; bien: { ten: string; moTa: string }[]
}
