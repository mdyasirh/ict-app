import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from './App.jsx';

const BOOKING_API = '/api/bookings';

function BookingForm() {
  const { token, user } = useAuth();
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // Form state
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    appointment_date: '',
    duration_minutes: 30,
    clinic_id: '',
    location: '',
  });

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

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setSuccess('');

    try {
      const payload = {
        ...formData,
        appointment_date: new Date(formData.appointment_date).toISOString(),
      };

      await axios.post(`${BOOKING_API}/appointments`, payload, {
        headers: { Authorization: `Bearer ${token}` },
      });

      setSuccess('Appointment booked successfully!');
      setFormData({
        title: '',
        description: '',
        appointment_date: '',
        duration_minutes: 30,
        clinic_id: '',
        location: '',
      });
      loadAppointments();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to book appointment');
    }
  }

  function handleChange(e) {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'duration_minutes' ? parseInt(value) : value,
    }));
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

      {/* Booking Form */}
      <div className="card">
        <h2>Book an Appointment</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Title</label>
            <input
              type="text"
              name="title"
              value={formData.title}
              onChange={handleChange}
              placeholder="e.g., General Checkup"
              required
            />
          </div>

          <div className="form-group">
            <label>Description</label>
            <textarea
              name="description"
              value={formData.description}
              onChange={handleChange}
              placeholder="Describe your reason for visit"
              rows="3"
            />
          </div>

          <div className="form-group">
            <label>Date and Time</label>
            <input
              type="datetime-local"
              name="appointment_date"
              value={formData.appointment_date}
              onChange={handleChange}
              required
            />
          </div>

          <div className="form-group">
            <label>Duration (minutes)</label>
            <select
              name="duration_minutes"
              value={formData.duration_minutes}
              onChange={handleChange}
            >
              <option value="15">15 minutes</option>
              <option value="30">30 minutes</option>
              <option value="45">45 minutes</option>
              <option value="60">60 minutes</option>
              <option value="90">90 minutes</option>
              <option value="120">120 minutes</option>
            </select>
          </div>

          <div className="form-group">
            <label>Clinic ID</label>
            <input
              type="text"
              name="clinic_id"
              value={formData.clinic_id}
              onChange={handleChange}
              placeholder="e.g., CLINIC001"
              required
            />
          </div>

          <div className="form-group">
            <label>Location</label>
            <input
              type="text"
              name="location"
              value={formData.location}
              onChange={handleChange}
              placeholder="e.g., Room 101, Building A"
            />
          </div>

          <button type="submit" className="btn">Book Appointment</button>
        </form>
      </div>

      {/* Appointments List */}
      <div className="card">
        <h2>Your Appointments</h2>
        {appointments.length === 0 ? (
          <p>No appointments scheduled.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Title</th>
                <th>Clinic</th>
                <th>Location</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {appointments.map((apt) => (
                <tr key={apt.id}>
                  <td>{new Date(apt.appointment_date).toLocaleString()}</td>
                  <td>{apt.title}</td>
                  <td>{apt.clinic_id}</td>
                  <td>{apt.location || '-'}</td>
                  <td>{getStatusBadge(apt.status)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default BookingForm;
