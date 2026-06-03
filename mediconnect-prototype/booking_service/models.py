"""
SQLAlchemy models for booking service.
Defines Appointment, Patient, and Clinician entities.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


class AppointmentStatus(enum.Enum):
    """Appointment status enumeration."""
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    CANCELLED = 'cancelled'
    COMPLETED = 'completed'


class Patient(Base):
    """Patient entity for appointment booking."""
    __tablename__ = 'patients'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, nullable=False, index=True)  # Links to auth service user
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(DateTime)
    phone = Column(String(20))
    email = Column(String(255))
    address = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    appointments = relationship('Appointment', back_populates='patient')


class Clinician(Base):
    """Clinician entity - healthcare providers."""
    __tablename__ = 'clinicians'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, nullable=False, index=True)  # Links to auth service user
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    specialty = Column(String(100))
    clinic_ids = Column(String(500))  # Comma-separated list of clinic IDs
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    appointments = relationship('Appointment', back_populates='clinician')


class Appointment(Base):
    """Appointment entity - core booking record."""
    __tablename__ = 'appointments'

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False, index=True)
    clinician_id = Column(Integer, ForeignKey('clinicians.id'), nullable=True, index=True)
    
    # Appointment details
    title = Column(String(200), nullable=False)
    description = Column(Text)
    appointment_date = Column(DateTime, nullable=False, index=True)
    duration_minutes = Column(Integer, default=30)
    clinic_id = Column(String(50), nullable=False, index=True)
    location = Column(String(255))
    
    # Status tracking
    status = Column(SQLEnum(AppointmentStatus), default=AppointmentStatus.PENDING)
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    cancelled_at = Column(DateTime, nullable=True)

    patient = relationship('Patient', back_populates='appointments')
    clinician = relationship('Clinician', back_populates='appointments')
