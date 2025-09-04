import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Register from './pages/Register';
import Login from './Login';  // Adjust path if Login.jsx is in a different folder (e.g., './pages/Login')
import DashboardPage from './pages/Dashboard';  // Use your full Dashboard.jsx, which already includes ProtectedRoute

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Navigate to="/login" />} />  // Redirect root to login; change to "/register" if preferred
        <Route path="/register" element={<Register />} />
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/journal" element={<div className="p-6">Journal Works</div>} />
        <Route path="/analytics" element={<div className="p-6">Analytics Works</div>} />
      </Routes>
    </Router>
  );
}