import React, { useState, useContext, createContext } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import './index.css'
import LoginPage from './pages/LoginPage'
import BookingPage from './pages/BookingPage'
import ClinicianView from './pages/ClinicianView'

const AuthContext = createContext()

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('access_token') || null)
  const [user, setUser] = useState(localStorage.getItem('user') ? JSON.parse(localStorage.getItem('user')) : null)

  const login = (accessToken, userData) => {
    localStorage.setItem('access_token', accessToken)
    localStorage.setItem('user', JSON.stringify(userData))
    setToken(accessToken)
    setUser(userData)
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ token, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)

function App() {
  const { token, user } = useAuth()

  return (
    <Router>
      <div className="app">
        <header className="app-header">
          <h1>MediConnect</h1>
          <p>Appointment Booking System</p>
        </header>
        
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          
          {token && user ? (
            <>
              {user.role === 'patient' && (
                <Route path="/" element={<BookingPage />} />
              )}
              {user.role === 'clinician' && (
                <Route path="/" element={<ClinicianView />} />
              )}
              {user.role === 'admin' && (
                <Route path="/" element={<ClinicianView />} />
              )}
              <Route path="*" element={<Navigate to="/" replace />} />
            </>
          ) : (
            <Route path="*" element={<Navigate to="/login" replace />} />
          )}
        </Routes>
      </div>
    </Router>
  )
}

export default App