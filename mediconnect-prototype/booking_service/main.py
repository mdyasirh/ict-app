"""
Booking Service - FastAPI application for appointment management.
Endpoints: /appointments CRUD, /patients, /clinicians
"""
import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from models import Base, Appointment, Patient, Clinician, AppointmentStatus
from auth_middleware import (
    validate_token,
    require_role,
    get_optional_user,
    security,
)

# Database configuration
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+asyncpg://postgres:postgres@localhost:5432/mediconnect'
)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Pydantic schemas
class AppointmentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    appointment_date: datetime
    duration_minutes: int = Field(default=30, ge=15, le=180)
    clinic_id: str = Field(..., min_length=1)
    location: Optional[str] = None
    clinician_id: Optional[int] = None


class AppointmentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    appointment_date: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=15, le=180)
    clinic_id: Optional[str] = None
    location: Optional[str] = None
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = None


class AppointmentResponse(BaseModel):
    id: int
    patient_id: int
    clinician_id: Optional[int]
    title: str
    description: Optional[str]
    appointment_date: datetime
    duration_minutes: int
    clinic_id: str
    location: Optional[str]
    status: str
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PatientCreate(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    date_of_birth: Optional[datetime] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class PatientResponse(BaseModel):
    id: int
    user_id: int
    first_name: str
    last_name: str
    email: Optional[str]
    phone: Optional[str]
    
    class Config:
        from_attributes = True


class ClinicianCreate(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    specialty: Optional[str] = None
    clinic_ids: Optional[str] = None


class ClinicianResponse(BaseModel):
    id: int
    user_id: int
    first_name: str
    last_name: str
    specialty: Optional[str]
    
    class Config:
        from_attributes = True


# FastAPI app
app = FastAPI(
    title='MediConnect Booking Service',
    description='Appointment Management API',
    version='1.0.0',
)


@app.on_event('startup')
async def startup():
    """Initialize database tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get('/health')
async def health_check():
    """Health check endpoint for container orchestration."""
    return {'status': 'healthy', 'service': 'booking'}


def get_db():
    """Dependency for database session."""
    db = async_session_maker()
    try:
        yield db
    finally:
        pass


# ==================== Appointment Endpoints ====================

@app.post('/appointments', response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_data: AppointmentCreate,
    request: Request,
    credentials=Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new appointment.
    
    Patients can create appointments for themselves.
    Clinicians can create appointments for patients in their clinics.
    """
    # Validate token and get user
    user = await validate_token(request, credentials)
    
    # Get or create patient record
    result = await db.execute(select(Patient).where(Patient.user_id == user['user_id']))
    patient = result.scalar_one_or_none()
    
    if not patient:
        # Auto-create patient profile if it doesn't exist
        patient = Patient(
            user_id=user['user_id'],
            first_name=user.get('first_name', 'Patient'),
            last_name=user.get('last_name', 'User'),
            email=user.get('email'),
        )
        db.add(patient)
        await db.commit()
        await db.refresh(patient)
    
    # Create appointment
    appointment = Appointment(
        patient_id=patient.id,
        clinician_id=appointment_data.clinician_id,
        title=appointment_data.title,
        description=appointment_data.description,
        appointment_date=appointment_data.appointment_date,
        duration_minutes=appointment_data.duration_minutes,
        clinic_id=appointment_data.clinic_id,
        location=appointment_data.location,
        status=AppointmentStatus.PENDING,
    )
    
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)
    
    return appointment


@app.get('/appointments', response_model=List[AppointmentResponse])
async def list_appointments(
    request: Request,
    status_filter: Optional[AppointmentStatus] = None,
    credentials=Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """
    List appointments based on user role.
    
    - Patients: See only their own appointments
    - Clinicians: See appointments for their assigned clinics
    - Admins: See all appointments
    """
    user = await validate_token(request, credentials)
    role = user.get('role')
    
    query = select(Appointment)
    
    if role == 'patient':
        # Get patient's own appointments
        result = await db.execute(select(Patient).where(Patient.user_id == user['user_id']))
        patient = result.scalar_one_or_none()
        
        if not patient:
            return []
        
        query = query.where(Appointment.patient_id == patient.id)
        
    elif role == 'clinician':
        # Get appointments for clinics this clinician can access
        result = await db.execute(select(Clinician).where(Clinician.user_id == user['user_id']))
        clinician = result.scalar_one_or_none()
        
        if clinician and clinician.clinic_ids:
            clinic_id_list = clinician.clinic_ids.split(',')
            query = query.where(Appointment.clinic_id.in_(clinic_id_list))
        else:
            # No clinic access - return empty
            return []
    
    # Apply status filter if provided
    if status_filter:
        query = query.where(Appointment.status == status_filter)
    
    result = await db.execute(query.order_by(Appointment.appointment_date.desc()))
    appointments = result.scalars().all()
    
    return appointments


@app.get('/appointments/{appointment_id}', response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: int,
    request: Request,
    credentials=Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific appointment by ID."""
    user = await validate_token(request, credentials)
    role = user.get('role')
    
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Appointment not found',
        )
    
    # RBAC: Check access permissions
    if role == 'patient':
        # Patients can only see their own appointments
        result = await db.execute(select(Patient).where(Patient.user_id == user['user_id']))
        patient = result.scalar_one_or_none()
        
        if not patient or appointment.patient_id != patient.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Access denied to this appointment',
            )
    
    elif role == 'clinician':
        # Clinicians can only see appointments in their clinics
        result = await db.execute(select(Clinician).where(Clinician.user_id == user['user_id']))
        clinician = result.scalar_one_or_none()
        
        if clinician and clinician.clinic_ids:
            clinic_id_list = clinician.clinic_ids.split(',')
            if appointment.clinic_id not in clinic_id_list:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='Access denied to this appointment',
                )
    
    # Admins can see everything
    
    return appointment


@app.put('/appointments/{appointment_id}', response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: int,
    appointment_data: AppointmentUpdate,
    request: Request,
    credentials=Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing appointment."""
    user = await validate_token(request, credentials)
    role = user.get('role')
    
    # Get appointment
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Appointment not found',
        )
    
    # RBAC: Only clinicians and admins can update appointments
    if role not in ['clinician', 'admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only clinicians and admins can update appointments',
        )
    
    # Update fields
    update_data = appointment_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(appointment, field, value)
    
    await db.commit()
    await db.refresh(appointment)
    
    return appointment


@app.delete('/appointments/{appointment_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(
    appointment_id: int,
    request: Request,
    credentials=Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """Delete/cancel an appointment."""
    user = await validate_token(request, credentials)
    role = user.get('role')
    
    # Get appointment
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Appointment not found',
        )
    
    # RBAC: Only admins can delete, others can only cancel
    if role == 'admin':
        await db.delete(appointment)
        await db.commit()
    else:
        # Mark as cancelled
        appointment.status = AppointmentStatus.CANCELLED
        appointment.cancelled_at = datetime.utcnow()
        await db.commit()
    
    return None


# ==================== Patient Endpoints ====================

@app.get('/patients/me', response_model=PatientResponse)
async def get_my_patient_profile(
    request: Request,
    credentials=Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's patient profile."""
    user = await validate_token(request, credentials)
    
    result = await db.execute(select(Patient).where(Patient.user_id == user['user_id']))
    patient = result.scalar_one_or_none()
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Patient profile not found',
        )
    
    return patient


# ==================== Clinician Endpoints ====================

@app.get('/clinicians/me', response_model=ClinicianResponse)
async def get_my_clinician_profile(
    request: Request,
    credentials=Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's clinician profile."""
    user = await validate_token(request, credentials)
    
    result = await db.execute(select(Clinician).where(Clinician.user_id == user['user_id']))
    clinician = result.scalar_one_or_none()
    
    if not clinician:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Clinician profile not found',
        )
    
    return clinician
