// src/App.jsx
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import Register from './pages/Register';

// Protected route wrapper
function ProtectedRoute({ children }) {
  const token = localStorage.getItem("token");
  return token ? children : <Navigate to="/login" />;
}

// Dashboard component
function Dashboard() {
  const navigate = useNavigate();

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

// Main App with routing
export default function App() {
  return (
    <Router>
      <Routes>
        {/* Root now points to the new Register page */}
        <Route path="/" element={<Register />} />

        <Route path="/login" element={<div className="p-6">Login Page Placeholder</div>} />

        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />

        <Route path="/journal" element={<div className="p-6">Journal Page Placeholder</div>} />
        <Route path="/analytics" element={<div className="p-6">Analytics Page Placeholder</div>} />
      </Routes>
    </Router>
  );
}
