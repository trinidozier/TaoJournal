import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import taoLogo from '../assets/tao-logo.jpg';

export default function Register() {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState('');
  const navigate = useNavigate();

  const handleRegister = async (e) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setMessage('Passwords do not match.');
      return;
    }

    try {
      const res = await fetch('https://taojournal-production.up.railway.app/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ first_name: firstName, last_name: lastName, email, password })
      });

      const data = await res.json();
      if (res.ok) {
        setMessage('Registration successful! Redirecting...');
        setTimeout(() => navigate('/login'), 1000);
      } else {
        setMessage(data.detail || 'Registration failed.');
      }
    } catch (err) {
      setMessage('Error connecting to server.');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4">
      <img src={taoLogo} alt="Tao Trader Logo" className="w-28 h-auto mb-4 shadow-md rounded" />
      <h1 className="text-3xl font-bold text-gray-800 mb-2">Welcome to Tao Trader</h1>
      <p className="text-gray-600 mb-6 text-center max-w-md">
        Register to start journaling your trades with clarity and confidence.
      </p>
      <form onSubmit={handleRegister} className="bg-white shadow-md rounded-lg p-6 w-full max-w-md space-y-4">
        <input type="text" placeholder="John" value={firstName} onChange={(e) => setFirstName(e.target.value)} className="mt-1 w-full px-3 py-2 border rounded-md" required />
        <input type="text" placeholder="Doe" value={lastName} onChange={(e) => setLastName(e.target.value)} className="mt-1 w-full px-3 py-2 border rounded-md" required />
        <input type="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} className="mt-1 w-full px-3 py-2 border rounded-md" required />
        <input type="password" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} className="mt-1 w-full px-3 py-2 border rounded-md" required />
        <input type="password" placeholder="••••••••" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} className="mt-1 w-full px-3 py-2 border rounded-md" required />
        <button type="submit" className="w-full bg-blue-600 text-white py-2 rounded-md hover:bg-blue-700 transition">
          Register
        </button>
      </form>
      {message && <p className="mt-4 text-sm text-gray-700 text-center">{message}</p>}
      <p className="mt-4 text-sm text-gray-600">
        Already registered? <Link to="/login" className="text-blue-600 hover:underline">Log in here</Link>
      </p>
    </div>
  );
}
