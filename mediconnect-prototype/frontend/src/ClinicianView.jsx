import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from './App.jsx';

const BOOKING_API = '/api/bookings';

function ClinicianView() {
  const { token, user } = useAuth();
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [selectedAppointment, setSelectedAppointment] = useState(null);
  const [updateStatus, setUpdateStatus] = useState('');

  useEffect(() => {
    loadAppointments();
  }, []);

  async function loadAppointments() {
    try {
      const response = await axios.get(`${BOOKING_API}/appointments`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setAppointments(response.data);
    } catch (err) {
      setError('Failed to load appointments');
    } finally {
      setLoading(false);
    }
  }

  async function handleStatusUpdate(appointmentId, newStatus) {
    setError('');
    setSuccess('');

    try {
      await axios.put(
        `${BOOKING_API}/appointments/${appointmentId}`,
        { status: newStatus },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      setSuccess(`Appointment ${newStatus} successfully!`);
      loadAppointments();
      setSelectedAppointment(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update appointment');
    }
  }

  async function handleDelete(appointmentId) {
    if (!window.confirm('Are you sure you want to cancel this appointment?')) {
      return;
    }

    try {
      await axios.delete(`${BOOKING_API}/appointments/${appointmentId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setSuccess('Appointment cancelled successfully!');
      loadAppointments();
      setSelectedAppointment(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to cancel appointment');
    }
  }

  function getStatusBadge(status) {
    const statusClasses = {
      pending: 'badge-pending',
      confirmed: 'badge-confirmed',
      cancelled: 'badge-cancelled',
      completed: 'badge-completed',
    };
    return <span className={`badge ${statusClasses[status] || ''}`}>{status}</span>;
  }

  if (loading) {
    return <div className="loading">Loading appointments...</div>;
  }

  return (
    <div className="container">
      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="card">
        <h2>Clinician Dashboard - Cross-Site Appointment Viewer</h2>
        <p style={{ marginBottom: '20px', color: '#666' }}>
          Logged in as: {user?.username} | Role: {user?.role}
        </p>

        {appointments.length === 0 ? (
          <p>No appointments found for your assigned clinics.</p>
        ) : (
          <>
            <table className="table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Patient</th>
                  <th>Title</th>
                  <th>Clinic</th>
                  <th>Location</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {appointments.map((apt) => (
                  <tr key={apt.id}>
                    <td>{new Date(apt.appointment_date).toLocaleString()}</td>
                    <td>Patient #{apt.patient_id}</td>
                    <td>{apt.title}</td>
                    <td>{apt.clinic_id}</td>
                    <td>{apt.location || '-'}</td>
                    <td>{getStatusBadge(apt.status)}</td>
                    <td>
                      <button
                        className="btn"
                        style={{ padding: '4px 8px', fontSize: '12px', marginRight: '5px' }}
                        onClick={() => setSelectedAppointment(apt)}
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Detail Modal */}
            {selectedAppointment && (
              <div
                style={{
                  position: 'fixed',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  background: 'rgba(0,0,0,0.5)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  zIndex: 1000,
                }}
                onClick={() => setSelectedAppointment(null)}
              >
                <div
                  className="card"
                  style={{ maxWidth: '500px', width: '90%', margin: 0 }}
                  onClick={(e) => e.stopPropagation()}
                >
                  <h3>Appointment Details</h3>
                  <div style={{ marginBottom: '20px' }}>
                    <p><strong>ID:</strong> {selectedAppointment.id}</p>
                    <p><strong>Title:</strong> {selectedAppointment.title}</p>
                    <p><strong>Description:</strong> {selectedAppointment.description || 'N/A'}</p>
                    <p><strong>Date:</strong> {new Date(selectedAppointment.appointment_date).toLocaleString()}</p>
                    <p><strong>Duration:</strong> {selectedAppointment.duration_minutes} minutes</p>
                    <p><strong>Clinic:</strong> {selectedAppointment.clinic_id}</p>
                    <p><strong>Location:</strong> {selectedAppointment.location || 'N/A'}</p>
                    <p><strong>Status:</strong> {getStatusBadge(selectedAppointment.status)}</p>
                    <p><strong>Patient ID:</strong> {selectedAppointment.patient_id}</p>
                    <p><strong>Created:</strong> {new Date(selectedAppointment.created_at).toLocaleString()}</p>
                  </div>

                  <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                    {selectedAppointment.status === 'pending' && (
                      <>
                        <button
                          className="btn"
                          onClick={() => handleStatusUpdate(selectedAppointment.id, 'confirmed')}
                        >
                          Confirm
                        </button>
                        <button
                          className="btn btn-danger"
                          onClick={() => handleDelete(selectedAppointment.id)}
                        >
                          Cancel
                        </button>
                      </>
                    )}
                    {selectedAppointment.status === 'confirmed' && (
                      <button
                        className="btn"
                        onClick={() => handleStatusUpdate(selectedAppointment.id, 'completed')}
                      >
                        Mark Complete
                      </button>
                    )}
                    <button
                      className="btn btn-secondary"
                      onClick={() => setSelectedAppointment(null)}
                    >
                      Close
                    </button>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default ClinicianView;
