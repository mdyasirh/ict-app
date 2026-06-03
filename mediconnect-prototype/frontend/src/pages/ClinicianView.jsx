import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../App'
import { api } from '../api/client'

function ClinicianView() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [appointments, setAppointments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedApt, setSelectedApt] = useState(null)
  const [updateStatus, setUpdateStatus] = useState('')

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

  const handleUpdateStatus = async (appointmentId, newStatus) => {
    try {
      await api.appointments.update(appointmentId, { status: newStatus })
      fetchAppointments()
      setSelectedApt(null)
      setUpdateStatus('')
    } catch (err) {
      setError('Failed to update appointment')
    }
  }

  const handleDeleteAppointment = async (appointmentId) => {
    if (window.confirm('Are you sure you want to cancel this appointment?')) {
      try {
        await api.appointments.delete(appointmentId)
        fetchAppointments()
      } catch (err) {
        setError('Failed to delete appointment')
      }
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="clinician-view">
      <div className="page-header">
        <div>
          <h2>Welcome, {user?.username}</h2>
          <p>{user?.role === 'admin' ? 'Admin' : 'Clinician'} Appointment Management</p>
        </div>
        <button onClick={handleLogout} className="logout-btn">Logout</button>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="clinician-content">
        <div className="appointments-list">
          <h3>Appointments Overview</h3>
          {loading ? (
            <p>Loading...</p>
          ) : appointments.length === 0 ? (
            <p className="empty-state">No appointments available</p>
          ) : (
            <table className="appointments-table large">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Patient ID</th>
                  <th>Date & Time</th>
                  <th>Status</th>
                  <th>Clinic</th>
                  <th>Notes</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {appointments.map(apt => (
                  <tr key={apt.id}>
                    <td>{apt.id}</td>
                    <td>{apt.patient_id}</td>
                    <td>{apt.appointment_datetime}</td>
                    <td>
                      <select 
                        value={selectedApt?.id === apt.id ? updateStatus : apt.status}
                        onChange={(e) => {
                          setSelectedApt(apt)
                          setUpdateStatus(e.target.value)
                        }}
                        className="status-select"
                      >
                        <option value="scheduled">Scheduled</option>
                        <option value="completed">Completed</option>
                        <option value="cancelled">Cancelled</option>
                        <option value="no-show">No-show</option>
                      </select>
                    </td>
                    <td>{apt.clinic_id}</td>
                    <td>{apt.notes || '—'}</td>
                    <td className="actions">
                      {selectedApt?.id === apt.id && (
                        <>
                          <button 
                            onClick={() => handleUpdateStatus(apt.id, updateStatus)}
                            className="btn-small primary"
                          >
                            Save
                          </button>
                          <button 
                            onClick={() => setSelectedApt(null)}
                            className="btn-small secondary"
                          >
                            Cancel
                          </button>
                        </>
                      )}
                      <button 
                        onClick={() => handleDeleteAppointment(apt.id)}
                        className="btn-small danger"
                      >
                        Delete
                      </button>
                    </td>
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

export default ClinicianView