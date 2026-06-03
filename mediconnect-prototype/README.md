# MediConnect Health Services - Appointment Booking Prototype

A distributed microservices-based appointment booking system for healthcare providers, built with FastAPI, React, and PostgreSQL.

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   React UI      │────▶│  Booking Service │────▶│   PostgreSQL    │
│   (Port 5173)   │     │   (Port 8002)    │     │   (Port 5432)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                              │
                              ▼
                        ┌──────────────────┐
                        │   Auth Service   │
                        │   (Port 8001)    │
                        └──────────────────┘
```

## Quick Start

### Prerequisites

- Docker 24+ and Docker Compose v2
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Installation & Running

#### Option 1: Docker Compose (Recommended)

```bash
cd mediconnect-prototype

# Copy environment configuration
cp .env.example .env

# Build and start all services
docker compose up --build

# Verify services are running
curl http://localhost:8001/health  # Auth service
curl http://localhost:8002/health  # Booking service
```

Access the application at:
- **Frontend**: http://localhost:5173
- **Auth API**: http://localhost:8001/docs
- **Booking API**: http://localhost:8002/docs

#### Option 2: Local Development

```bash
# Start PostgreSQL
docker run -d --name mediconnect-db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=mediconnect \
  -p 5432:5432 \
  postgres:16-alpine

# Install and run Auth Service
cd auth_service
pip install -r requirements.txt
uvicorn main:app --reload --port 8001

# Install and run Booking Service (new terminal)
cd booking_service
pip install -r requirements.txt
uvicorn main:app --reload --port 8002

# Install and run Frontend (new terminal)
cd frontend
npm install
npm run dev
```

## API Endpoints

### Auth Service (Port 8001)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/auth/register` | POST | Register new user |
| `/auth/token` | POST | Login and get JWT token |
| `/auth/refresh` | POST | Refresh access token |
| `/auth/me` | GET | Get current user details |

### Booking Service (Port 8002)

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/health` | GET | Health check | No |
| `/appointments` | GET | List appointments | Yes |
| `/appointments` | POST | Create appointment | Yes |
| `/appointments/{id}` | GET | Get appointment details | Yes |
| `/appointments/{id}` | PUT | Update appointment | Yes (clinician/admin) |
| `/appointments/{id}` | DELETE | Cancel/Delete appointment | Yes |
| `/patients/me` | GET | Get patient profile | Yes |
| `/clinicians/me` | GET | Get clinician profile | Yes |

## Security Features

### JWT-Based Authentication

- **HS256 signed tokens** with configurable expiration (default: 15 minutes)
- **Refresh tokens** for seamless session management (7-day expiry)
- **Role-based access control (RBAC)** with three roles:
  - `patient`: Can view and book own appointments
  - `clinician`: Cross-site access to appointments in assigned clinics
  - `admin`: Full CRUD access to all resources

### RBAC Enforcement

```python
# Example: Clinician-only endpoint
@app.get('/appointments/{id}', dependencies=[Depends(require_role('clinician', 'admin'))])
async def get_appointment(id: int):
    ...
```

## Testing

### Run RBAC Tests

```bash
cd auth_service
pytest tests/ -v
```

### Load Testing with Locust

```bash
# Install Locust
pip install locust

# Run load test with 200 concurrent users
locust -f experiments/locustfile.py \
  --host http://localhost:8002 \
  --users 200 --spawn-rate 10 \
  --run-time 120s --headless \
  --csv experiments/locust_results/200vu

# View results in Locust web UI
locust -f experiments/locustfile.py --host http://localhost:8002
# Open http://localhost:8089
```

## Project Structure

```
mediconnect-prototype/
├── auth_service/
│   ├── main.py              # FastAPI app
│   ├── models.py            # SQLAlchemy models
│   ├── security.py          # JWT handling & RBAC
│   ├── requirements.txt
│   └── Dockerfile
├── booking_service/
│   ├── main.py              # FastAPI app
│   ├── models.py            # SQLAlchemy models
│   ├── auth_middleware.py   # Token validation
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main app component
│   │   ├── BookingForm.jsx  # Patient booking UI
│   │   └── ClinicianView.jsx# Clinician dashboard
│   ├── package.json
│   └── Dockerfile
├── experiments/
│   ├── locustfile.py        # Load test scenarios
│   └── locust_results/      # Test result CSVs
├── scripts/
│   └── init_db.sql          # Database initialization
├── docker-compose.yml       # Container orchestration
├── .env.example             # Environment template
└── README.md
```

## Sample Usage

### Register a User

```bash
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "securepass123",
    "role": "patient"
  }'
```

### Login and Get Token

```bash
curl -X POST http://localhost:8001/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=john_doe&password=securepass123"
```

### Book an Appointment

```bash
TOKEN="your-access-token-here"

curl -X POST http://localhost:8002/appointments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "title": "General Checkup",
    "description": "Annual health screening",
    "appointment_date": "2026-06-15T10:00:00",
    "duration_minutes": 30,
    "clinic_id": "CLINIC001",
    "location": "Room 101"
  }'
```

## Troubleshooting

### Common Issues

1. **Database connection error**: Ensure PostgreSQL container is running and healthy
   ```bash
   docker compose ps
   docker compose logs postgres
   ```

2. **Auth service unavailable**: Check JWT_SECRET is set in .env
   ```bash
   docker compose logs auth_service
   ```

3. **Frontend not loading**: Verify Node modules are installed
   ```bash
   cd frontend && npm install
   ```

### Reset Database

```bash
docker compose down -v  # Remove volumes
docker compose up --build
```

## License

This prototype is developed for educational purposes as part of ICT513 Distributed Systems Assessment 4.

## Authors

MediConnect Health Services Prototype Team
