import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import taoLogo from '../assets/tao-logo.jpg';

export default function Register() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 p-6">
      <div className="bg-white p-8 rounded-lg shadow-xl border border-gray-200 w-full max-w-md">
        <div className="flex justify-center mb-4">
          <img src={taoLogo} alt="Tao Trader Logo" className="h-16 w-auto rounded" />
        </div>
        <h1 className="text-2xl font-bold mb-2 text-center">Register for Tao Trader</h1>
        <p className="text-sm text-gray-600 mb-6 text-center">
          Create an account to start tracking your trading journey.
        </p>
        <form className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">First Name</label>
            <input
              type="text"
              placeholder="First Name"
              className="mt-1 block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring focus:border-blue-300"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Last Name</label>
            <input
              type="text"
              placeholder="Last Name"
              className="mt-1 block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring focus:border-blue-300"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Email</label>
            <input
              type="email"
              placeholder="Email"
              className="mt-1 block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring focus:border-blue-300"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Password</label>
            <input
              type="password"
              placeholder="Password"
              className="mt-1 block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring focus:border-blue-300"
              required
            />
          </div>
          <button
            type="submit"
            className="w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 transition"
          >
            Register
          </button>
        </form>
        <p className="text-sm text-gray-600 mt-6 text-center">
          Already registered?{' '}
          <Link to="/login" className="text-blue-600 hover:underline">
            Click here to login
          </Link>
        </p>
      </div>
    </div>
  );
}