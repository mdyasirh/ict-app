from locust import HttpUser, task, between
import random
import json

class BookingUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        response = self.client.post('/auth/login', json={
            'username': 'clinician_001',
            'password': 'password123'
        })
        if response.status_code == 200:
            self.token = response.json()['access_token']
        else:
            self.token = None
    
    def get_headers(self):
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
    
    @task(3)
    def list_appointments(self):
        self.client.get('/appointments', headers=self.get_headers())
    
    @task(2)
    def get_single_appointment(self):
        apt_id = random.randint(1, 10)
        self.client.get(f'/appointments/{apt_id}', headers=self.get_headers())
    
    @task(5)
    def create_appointment(self):
        payload = {
            'patient_id': random.randint(1, 5),
            'clinician_id': random.randint(1, 3),
            'clinic_id': random.randint(1, 2),
            'appointment_datetime': '2026-06-15 14:00:00',
            'status': 'scheduled',
            'notes': 'Test appointment'
        }
        self.client.post('/appointments', 
                        json=payload, 
                        headers=self.get_headers())
    
    @task(1)
    def update_appointment(self):
        apt_id = random.randint(1, 10)
        payload = {
            'status': random.choice(['scheduled', 'completed', 'cancelled'])
        }
        self.client.put(f'/appointments/{apt_id}', 
                       json=payload, 
                       headers=self.get_headers()
