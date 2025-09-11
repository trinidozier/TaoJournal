import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import taoLogo from './assets/tao-logo.jpg'; // Keep your logo; update to forgelogo.png if needed

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setMessage('');

    // Create form-data for OAuth2PasswordRequestForm
    const formData = new FormData();
    formData.append('username', email); // Backend expects 'username' for email
    formData.append('password', password);

    console.log('Attempting login with:', { email });

    try {
      const res = await fetch('https://taojournal-production.up.railway.app/login', {
        method: 'POST',
        body: formData, // Send as form-data
      });
      console.log('Login response status:', res.status);
      const text = await res.text();
      console.log('Login response body:', text);
      let data;
      try {
        data = JSON.parse(text);
      } catch (err) {
        console.error('JSON parse error:', err);
        setMessage('Invalid server response.');
        return;
      }
      if (res.ok) {
        localStorage.setItem('token', data.access_token);
        setMessage('Login successful!');
        console.log('Navigating to dashboard');
        setTimeout(() => navigate('/dashboard'), 1000);
      } else {
        // Handle error messages safely
        const errorMsg = data.detail
          ? Array.isArray(data.detail)
            ? data.detail.map(err => err.msg || 'Unknown error').join(', ')
            : data.detail
          : 'Login failed. Please check your credentials.';
        setMessage(errorMsg);
      }
    } catch (err) {
      console.error('Login error:', err);
      setMessage('Error connecting to server. Please try again.');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-100 to-blue-100 flex items-center justify-center">
      <div className="bg-white p-8 rounded-lg shadow-xl border border-gray-200 w-full max-w-md">
        <div className="flex justify-center mb-4">
          <img src={taoLogo} alt="StrategyForge Journal Logo" className="h-16 w-auto rounded" />
        </div>
        <h1 className="text-2xl font-bold mb-2 text-center">Login to StrategyForge Journal</h1>
        <p className="text-sm text-gray-600 mb-6 text-center">
          Welcome back. Enter your credentials to access your trading journal.
          If you've forgotten your password, you can reset it below.
        </p>
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring focus:border-blue-300"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring focus:border-blue-300"
              required
            />
          </div>
          <button
            type="submit"
            className="w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 transition"
          >
            Login
          </button>
        </form>
        {message && <p className="mt-4 text-center text-sm text-gray-700">{message}</p>}
        <div className="mt-6 text-center space-y-2">
          <a href="forgot-password" className="text-sm text-blue-600 hover:underline">
            Forgot password?
          </a>
          <p className="text-sm text-gray-600">
            Need an account?{' '}
            <a href="/register" className="text-blue-600 hover:underline">
              Register here
            </a>
          </p>
        </div>
        <p className="text-xs text-gray-500 mt-6 text-center">
          Your login is encrypted and secure.
          StrategyForge Journal never shares your data.
        </p>
      </div>
    </div>
  );
}

export default Login;