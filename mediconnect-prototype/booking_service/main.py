import os
import logging
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.future import select
from pydantic import BaseModel
import jwt

JWT_SECRET = os.getenv('JWT_SECRET')
DATABASE_URL = os.getenv('DATABASE_URL')
AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://auth_service:8001')
ALGORITHM = 'HS256'

if not JWT_SECRET:
    raise ValueError('JWT_SECRET environment variable required')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=5)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

from models import Appointment, Patient, Clinician, Base

class AppointmentCreate(BaseModel):
    patient_id: int
    clinician_id: int
    clinic_id: int
    appointment_datetime: str
    status: str = 'scheduled'
    notes: str = ''

class AppointmentUpdate(BaseModel):
    status: str = None
    notes: str = None

class AppointmentResponse(BaseModel):
    id: int
    patient_id: int
    clinician_id: int
    clinic_id: int
    appointment_datetime: str
    status: str
    notes: str
    created_at: str

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

async def verify_token(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Authorization header required')
    
    token = authorization.split(' ')[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        if payload.get('exp', 0) < datetime.utcnow().timestamp():
            raise HTTPException(status_code=401, detail='Token expired')
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail='Invalid token')

def require_role(*allowed_roles: str):
    async def check_role(credentials: dict = Depends(verify_token)):
        if credentials.get('role') not in allowed_roles:
            raise HTTPException(status_code=403, detail='Insufficient permissions')
        return credentials
    return Depends(check_role)

app = FastAPI(title='MediConnect Booking Service', version='1.0.0')

@app.on_event('startup')
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info('Database tables created')

@app.post('/appointments', response_model=AppointmentResponse, status_code=201)
async def create_appointment(
    request: AppointmentCreate,
    credentials: dict = require_role('patient', 'clinician', 'admin'),
    db: AsyncSession = Depends(get_db)
):
    if credentials.get('role') == 'patient' and request.patient_id != int(credentials.get('sub', 0)):
        raise HTTPException(status_code=403, detail='Cannot create appointment for other patients')
    
    appointment = Appointment(
        patient_id=request.patient_id,
        clinician_id=request.clinician_id,
        clinic_id=request.clinic_id,
        appointment_datetime=request.appointment_datetime,
        status=request.status,
        notes=request.notes
    )
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)
    
    logger.info(f'Appointment {appointment.id} created by {credentials.get("sub")}')
    
    return AppointmentResponse(
        id=appointment.id,
        patient_id=appointment.patient_id,
        clinician_id=appointment.clinician_id,
        clinic_id=appointment.clinic_id,
        appointment_datetime=appointment.appointment_datetime,
        status=appointment.status,
        notes=appointment.notes,
        created_at=appointment.created_at.isoformat()
    )

@app.get('/appointments', response_model=list)
async def list_appointments(
    credentials: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    role = credentials.get('role')
    user_id = int(credentials.get('sub', 0))
    
    if role == 'patient':
        result = await db.execute(select(Appointment).where(Appointment.patient_id == user_id))
    elif role == 'clinician':
        result = await db.execute(select(Appointment).where(Appointment.clinician_id == user_id))
    else:
        result = await db.execute(select(Appointment))
    
    appointments = result.scalars().all()
    
    return [
        AppointmentResponse(
            id=apt.id,
            patient_id=apt.patient_id,
            clinician_id=apt.clinician_id,
            clinic_id=apt.clinic_id,
            appointment_datetime=apt.appointment_datetime,
            status=apt.status,
            notes=apt.notes,
            created_at=apt.created_at.isoformat()
        )
        for apt in appointments
    ]

@app.get('/appointments/{appointment_id}', response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: int,
    credentials: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appointment = result.scalars().first()
    
    if not appointment:
        raise HTTPException(status_code=404, detail='Appointment not found')
    
    role = credentials.get('role')
    user_id = int(credentials.get('sub', 0))
    
    if role == 'patient' and appointment.patient_id != user_id:
        raise HTTPException(status_code=403, detail='Cannot access other patient appointments')
    elif role == 'clinician' and appointment.clinician_id != user_id:
        raise HTTPException(status_code=403, detail='Cannot access appointments outside your clinic')
    
    return AppointmentResponse(
        id=appointment.id,
        patient_id=appointment.patient_id,
        clinician_id=appointment.clinician_id,
        clinic_id=appointment.clinic_id,
        appointment_datetime=appointment.appointment_datetime,
        status=appointment.status,
        notes=appointment.notes,
        created_at=appointment.created_at.isoformat()
    )

@app.put('/appointments/{appointment_id}', response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: int,
    request: AppointmentUpdate,
    credentials: dict = require_role('clinician', 'admin'),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appointment = result.scalars().first()
    
    if not appointment:
        raise HTTPException(status_code=404, detail='Appointment not found')
    
    if request.status:
        appointment.status = request.status
    if request.notes:
        appointment.notes = request.notes
    
    await db.commit()
    await db.refresh(appointment)
    
    logger.info(f'Appointment {appointment_id} updated by {credentials.get("sub")}')
    
    return AppointmentResponse(
        id=appointment.id,
        patient_id=appointment.patient_id,
        clinician_id=appointment.clinician_id,
        clinic_id=appointment.clinic_id,
        appointment_datetime=appointment.appointment_datetime,
        status=appointment.status,
        notes=appointment.notes,
        created_at=appointment.created_at.isoformat()
    )

@app.delete('/appointments/{appointment_id}', status_code=204)
async def delete_appointment(
    appointment_id: int,
    credentials: dict = require_role('clinician', 'admin'),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appointment = result.scalars().first()
    
    if not appointment:
        raise HTTPException(status_code=404, detail='Appointment not found')
    
    await db.delete(appointment)
    await db.commit()
    
    logger.info(f'Appointment {appointment_id} deleted by {credentials.get("sub")}')

@app.get('/health')
async def health():
    return {'status': 'ok', 'service': 'booking_service'}

if __name__ == '__main__':
    import uvicorn
    port = int(os.getenv('BOOKING_SERVICE_PORT', 8002))
    uvicorn.run(app, host='0.0.0.0', port=port)