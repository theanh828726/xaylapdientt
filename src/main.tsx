import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter, Navigate, Route, Routes } from 'react-router-dom'
import './index.css'
import Layout from './components/Layout'
import Gate from './components/Gate'
import { AuthProvider } from './lib/role'
import BanDo from './pages/BanDo'
import QAQC from './pages/QAQC'
import DeXuat from './pages/DeXuat'
import DoiSoat from './pages/DoiSoat'
import Kho from './pages/Kho'
import NhatKy from './pages/NhatKy'
import Duyet from './pages/Duyet'
import ThuHoi from './pages/ThuHoi'
import BaoCao from './pages/BaoCao'
import TongQuan from './pages/TongQuan'
import Toi from './pages/Toi'
import QuanTri from './pages/QuanTri'

// Máy tính mở bản đồ tuyến; điện thoại mở Tổng quan (theo thiết kế).
const Trang = () => <Navigate to={window.matchMedia('(min-width: 1024px)').matches ? '/ban-do' : '/tong-quan'} replace />

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <Gate>
        <HashRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<Trang />} />
              <Route path="ban-do" element={<BanDo />} />
              <Route path="qaqc" element={<QAQC />} />
              <Route path="de-xuat" element={<DeXuat />} />
              <Route path="de-xuat/:ma" element={<DeXuat />} />
              <Route path="kho" element={<Kho />} />
              <Route path="nhat-ky" element={<NhatKy />} />
              <Route path="duyet" element={<Duyet />} />
              <Route path="doi-soat" element={<DoiSoat />} />
              <Route path="thu-hoi" element={<ThuHoi />} />
              <Route path="bao-cao" element={<BaoCao />} />
              <Route path="bao-cao/:viTriId" element={<BaoCao />} />
              <Route path="tong-quan" element={<TongQuan />} />
              <Route path="toi" element={<Toi />} />
              <Route path="quan-tri" element={<QuanTri />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </HashRouter>
      </Gate>
    </AuthProvider>
  </StrictMode>,
)
