import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import MapPage from './pages/MapPage';
import AuthPage from './pages/AuthPage';
import DashboardPage from './pages/DashboardPage';
import DocumentsPage from './pages/DocumentsPage';
import MyUploadsPage from './pages/MyUploadsPage';
import HowItWorksPage from './pages/HowItWorksPage';
import ArchitecturePage from './pages/ArchitecturePage';
import CapabilitiesPage from './pages/CapabilitiesPage';
import { BackgroundProvider } from './context/BackgroundContext';

// Protected route — checks for the real access token
const ProtectedRoute = ({ children }) => {
  const isAuthenticated =
    localStorage.getItem('satquery_access_token') !== null ||
    localStorage.getItem('satquery_jwt_token') !== null;

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace />;
  }
  return children;
};

function App() {
  return (
    <BackgroundProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/auth" element={<AuthPage />} />
          <Route path="/how-it-works" element={<HowItWorksPage />} />
          <Route path="/architecture" element={<ArchitecturePage />} />
          <Route path="/capabilities" element={<CapabilitiesPage />} />
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
    </BackgroundProvider>
  );
}

export default App;
