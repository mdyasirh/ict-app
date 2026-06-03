"""
Locust load testing script for MediConnect Booking Service.
Tests appointment booking endpoint under various load conditions.

Usage:
    locust -f locustfile.py --host http://localhost:8002 \
           --users 200 --spawn-rate 10 --run-time 120s --headless \
           --csv experiments/locust_results/200vu
"""
import random
from datetime import datetime, timedelta
from locust import HttpUser, task, between


class BookingUser(HttpUser):
    """Simulates a user booking appointments."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    # Sample data for realistic bookings
    clinics = ['CLINIC001', 'CLINIC002', 'HOSPITAL01', 'HOSPITAL02', 'CLINIC003']
    locations = [
        'Room 101, Building A',
        'Room 205, Building B',
        'Consultation Room 3',
        'Main Clinic - Floor 2',
        'Regional Health Center'
    ]
    titles = [
        'General Checkup',
        'Follow-up Consultation',
        'Vaccination Appointment',
        'Blood Test',
        'Specialist Referral',
        'Routine Screening',
        'Health Assessment'
    ]
    descriptions = [
        'Annual health checkup and vitals monitoring',
        'Follow-up on previous consultation results',
        'Seasonal flu vaccination',
        'Routine blood work for diabetes monitoring',
        'Cardiology referral consultation',
        'Preventive health screening',
        'Comprehensive health assessment'
    ]
    
    def on_start(self):
        """Called when user starts - authenticate and get token."""
        # For load testing, we use a pre-generated token or skip auth
        # In real scenario, you would login here
        self.token = self.get_test_token()
    
    def get_test_token(self):
        """
        Get a test token for authenticated requests.
        In production, replace with actual login flow.
        """
        # Try to get a token via login
        try:
            response = self.client.post(
                "/auth/token",
                data={
                    "username": "testuser",
                    "password": "testpass123"
                }
            )
            if response.status_code == 200:
                return response.json().get('access_token', '')
        except Exception:
            pass
        
        # Return empty token (requests will fail auth, but we can test unauthenticated paths)
        return ""
    
    @task(3)
    def list_appointments(self):
        """View list of appointments (most common operation)."""
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        
        with self.client.get(
            "/appointments",
            headers=headers,
            catch_response=True
        ) as response:
            if response.status_code == 401:
                response.success()  # Expected for missing token in load test
    
    @task(5)
    def book_appointment(self):
        """Book a new appointment (primary load test target)."""
        # Generate random appointment data
        future_date = datetime.now() + timedelta(
            days=random.randint(1, 30),
            hours=random.randint(9, 17),
            minutes=random.choice([0, 15, 30, 45])
        )
        
        payload = {
            "title": random.choice(self.titles),
            "description": random.choice(self.descriptions),
            "appointment_date": future_date.isoformat(),
            "duration_minutes": random.choice([15, 30, 45, 60]),
            "clinic_id": random.choice(self.clinics),
            "location": random.choice(self.locations)
        }
        
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        
        self.client.post(
            "/appointments",
            json=payload,
            headers=headers,
            name="/appointments [POST]"
        )
    
    @task(2)
    def get_health(self):
        """Check service health (lightweight operation)."""
        self.client.get("/health", name="/health")
    
    @task(1)
    def get_specific_appointment(self):
        """Get details of a specific appointment."""
        appointment_id = random.randint(1, 1000)
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        
        self.client.get(
            f"/appointments/{appointment_id}",
            headers=headers,
            name="/appointments/[id] [GET]"
        )


class AdminUser(HttpUser):
    """Simulates an admin user performing management operations."""
    
    wait_time = between(2, 5)
    
    @task(2)
    def view_all_appointments(self):
        """Admin views all appointments across clinics."""
        # Would need admin token in real scenario
        self.client.get(
            "/appointments",
            name="/appointments [admin view]"
        )
    
    @task(1)
    def update_appointment_status(self):
        """Admin updates appointment status."""
        appointment_id = random.randint(1, 100)
        status = random.choice(['confirmed', 'completed', 'cancelled'])
        
        self.client.put(
            f"/appointments/{appointment_id}",
            json={"status": status},
            name="/appointments/[id] [PUT]"
        )
