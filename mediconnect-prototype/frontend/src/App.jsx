import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';
import BookingForm from './BookingForm.jsx';
import ClinicianView from './ClinicianView.jsx';

// API base URLs
const AUTH_API = '/api/auth';
const BOOKING_API = '/api/bookings';

// Auth context
const AuthContext = createContext(null);

export function useAuth() {
  return useContext(AuthContext);
}

function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      loadUser();
    } else {
      setLoading(false);
    }
  }, []);

  async function loadUser() {
    try {
      const response = await axios.get(`${AUTH_API}/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setUser(response.data);
    } catch (error) {
      localStorage.removeItem('token');
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  async function login(username, password) {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    const response = await axios.post(`${AUTH_API}/token`, formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });

    const { access_token } = response.data;
    localStorage.setItem('token', access_token);
    setToken(access_token);
    
    // Load user details
    const userResponse = await axios.get(`${AUTH_API}/me`, {
      headers: { Authorization: `Bearer ${access_token}` },
    });
    setUser(userResponse.data);
    
    return userResponse.data;
  }

  function logout() {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  }

  async function register(userData) {
    const response = await axios.post(`${AUTH_API}/register`, userData);
    return response.data;
  }

  const value = {
    user,
    token,
    loading,
    login,
    logout,
    register,
    isAuthenticated: !!token,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Login component
function LoginForm() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const { login, register } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      if (isRegistering) {
        await register({
          username,
          password,
          email: `${username}@example.com`,
          role: 'patient',
        });
        alert('Registration successful! Please log in.');
        setIsRegistering(false);
      } else {
        await login(username, password);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Authentication failed');
    }
  };

  return (
    <div className="container">
      <div className="card auth-form">
        <h2>{isRegistering ? 'Register' : 'Login'} to MediConnect</h2>
        {error && <div className="error-message">{error}</div>}
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
          
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          
          <button type="submit" className="btn" style={{ width: '100%' }}>
            {isRegistering ? 'Register' : 'Login'}
          </button>
        </form>
        
        <p style={{ marginTop: '16px', textAlign: 'center' }}>
          <button
            className="btn btn-secondary"
            onClick={() => setIsRegistering(!isRegistering)}
            style={{ background: 'none', color: '#667eea', padding: 0 }}
          >
            {isRegistering ? 'Already have an account? Login' : "Don't have an account? Register"}
          </button>
        </p>
      </div>
    </div>
  );
}

// Header component
function Header() {
  const { user, logout, isAuthenticated } = useAuth();

  return (
    <header className="header">
      <div className="header-content">
        <div className="logo">MediConnect Health Services</div>
        {isAuthenticated && (
          <div className="nav-links">
            <span style={{ marginRight: '15px' }}>
              Welcome, {user?.username} ({user?.role})
            </span>
            <button onClick={logout}>Logout</button>
          </div>
        )}
      </div>
    </header>
  );
}

// Protected route wrapper
function ProtectedRoute({ children, allowedRoles }) {
  const { user, isAuthenticated, loading } = useAuth();

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  if (allowedRoles && !allowedRoles.includes(user?.role)) {
    return (
      <div className="container">
        <div className="alert alert-error">
          Access denied. Required roles: {allowedRoles.join(', ')}
        </div>
      </div>
    );
  }

  return children;
}

// Main App component
function App() {
  return (
    <Router>
      <AuthProvider>
        <div className="app">
          <Header />
          <Routes>
            <Route path="/login" element={<LoginForm />} />
            <Route
              path="/"
              element={
                <ProtectedRoute allowedRoles={['patient', 'clinician', 'admin']}>
                  <BookingForm />
                </ProtectedRoute>
              }
            />
            <Route
              path="/clinician"
              element={
                <ProtectedRoute allowedRoles={['clinician', 'admin']}>
                  <ClinicianView />
                </ProtectedRoute>
              }
            />
          </Routes>
        </div>
      </AuthProvider>
    </Router>
  );
}

export default App;
