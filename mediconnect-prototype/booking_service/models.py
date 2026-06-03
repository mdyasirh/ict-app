from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Patient(Base):
    __tablename__ = 'patients'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True)
    phone = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)

class Clinician(Base):
    __tablename__ = 'clinicians'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    clinic_id = Column(Integer)
    specialization = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

class Appointment(Base):
    __tablename__ = 'appointments'
    
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, nullable=False)
    clinician_id = Column(Integer, nullable=False)
    clinic_id = Column(Integer, nullable=False)
    appointment_datetime = Column(String(50), nullable=False)
    status = Column(String(20), default='scheduled')
    notes = Column(Text, default='')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Appointment {self.id} - {self.appointment_datetime}>'

class AuditLog(Base):
    __tablename__ = 'audit_log'
    
    id = Column(Integer, primary_key=True)
    clinician_id = Column(Integer)
    appointment_id = Column(Integer)
    action = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow)