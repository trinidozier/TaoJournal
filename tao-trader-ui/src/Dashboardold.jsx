// src/pages/Dashboard.jsx
import { useEffect } from "react";
import { useNavigate, Navigate } from "react-router-dom";

// ProtectedRoute wrapper
function ProtectedRoute({ children }) {
  const token = localStorage.getItem("token");
  return token ? children : <Navigate to="/login" />;
}

// Dashboard component
function Dashboard() {
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) navigate("/login");
  }, [navigate]);

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <h1 className="text-2xl font-bold mb-4">Welcome back, Trader 🧠</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card title="Journal Entries" onClick={() => navigate("/journal")} />
        <Card title="Performance Analytics" onClick={() => navigate("/analytics")} />
      </div>
    </div>
  );
}

// Simple card component
function Card({ title, onClick }) {
  return (
    <div
      onClick={onClick}
      className="cursor-pointer bg-white shadow-md rounded-lg p-4 hover:bg-blue-50 transition"
    >
      <h2 className="text-lg font-semibold">{title}</h2>
    </div>
  );
}

// Export wrapped dashboard
export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <Dashboard />
    </ProtectedRoute>
  );
}
