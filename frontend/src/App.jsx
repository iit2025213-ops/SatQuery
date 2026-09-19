import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import MapPage from './pages/MapPage';
import AuthPage from './pages/AuthPage';
import DashboardPage from './pages/DashboardPage';
import DocumentsPage from './pages/DocumentsPage';
import MyUploadsPage from './pages/MyUploadsPage';

// Protected route — checks for the real access token
const ProtectedRoute = ({ children }) => {
  const isAuthenticated =
    localStorage.getItem('satquery_access_token') !== null ||
    localStorage.getItem('satquery_jwt_token') !== null; // fallback for existing sessions

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace />;
  }
  return children;
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/auth" element={<AuthPage />} />
        <Route
          path="/dashboard"
          element={<ProtectedRoute><DashboardPage /></ProtectedRoute>}
        />
        <Route
          path="/analysis"
          element={<ProtectedRoute><MapPage /></ProtectedRoute>}
        />
        <Route
          path="/documents"
          element={<ProtectedRoute><DocumentsPage /></ProtectedRoute>}
        />
        <Route
          path="/uploads"
          element={<ProtectedRoute><MyUploadsPage /></ProtectedRoute>}
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
