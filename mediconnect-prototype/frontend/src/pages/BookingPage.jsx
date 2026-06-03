import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../App'
import { api } from '../api/client'

function BookingPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [appointments, setAppointments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    patient_id: user?.id || 1,
    clinician_id: 1,
    clinic_id: 1,
    appointment_datetime: '',
    status: 'scheduled',
    notes: ''
  })

  useEffect(() => {
    fetchAppointments()
  }, [])

  const fetchAppointments = async () => {
    try {
      setLoading(true)
      const response = await api.appointments.list()
      setAppointments(response.data)
      setError('')
    } catch (err) {
      setError('Failed to load appointments')
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      await api.appointments.create(formData)
      setFormData({
        patient_id: user?.id || 1,
        clinician_id: 1,
        clinic_id: 1,
        appointment_datetime: '',
        status: 'scheduled',
        notes: ''
      })
      setShowForm(false)
      fetchAppointments()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create appointment')
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="booking-page">
      <div className="page-header">
        <div>
          <h2>Welcome, {user?.username}</h2>
          <p>Patient Appointment Booking</p>
        </div>
        <button onClick={handleLogout} className="logout-btn">Logout</button>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="booking-content">
        <button 
          className="primary-btn"
          onClick={() => setShowForm(!showForm)}
        >
          {showForm ? 'Cancel' : 'Book New Appointment'}
        </button>

        {showForm && (
          <form onSubmit={handleSubmit} className="booking-form">
            <h3>New Appointment</h3>
            
            <div className="form-group">
              <label>Appointment Date & Time</label>
              <input
                type="datetime-local"
                name="appointment_datetime"
                value={formData.appointment_datetime}
                onChange={handleInputChange}
                required
              />
            </div>

            <div className="form-group">
              <label>Clinician ID</label>
              <input
                type="number"
                name="clinician_id"
                value={formData.clinician_id}
                onChange={handleInputChange}
                min="1"
                required
              />
            </div>

            <div className="form-group">
              <label>Clinic ID</label>
              <input
                type="number"
                name="clinic_id"
                value={formData.clinic_id}
                onChange={handleInputChange}
                min="1"
                required
              />
            </div>

            <div className="form-group">
              <label>Notes</label>
              <textarea
                name="notes"
                value={formData.notes}
                onChange={handleInputChange}
                placeholder="Any special notes..."
              />
            </div>

            <button type="submit" className="primary-btn">Book Appointment</button>
          </form>
        )}

        <div className="appointments-list">
          <h3>Your Appointments</h3>
          {loading ? (
            <p>Loading...</p>
          ) : appointments.length === 0 ? (
            <p className="empty-state">No appointments booked yet</p>
          ) : (
            <table className="appointments-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Date & Time</th>
                  <th>Clinician</th>
                  <th>Clinic</th>
                  <th>Status</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {appointments.map(apt => (
                  <tr key={apt.id}>
                    <td>{apt.id}</td>
                    <td>{apt.appointment_datetime}</td>
                    <td>{apt.clinician_id}</td>
                    <td>{apt.clinic_id}</td>
                    <td><span className={`status-${apt.status}`}>{apt.status}</span></td>
                    <td>{apt.notes || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}

export default BookingPage