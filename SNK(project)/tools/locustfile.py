"""
Locust Performance & Load Testing Script

Simulates concurrent faculty members interacting with the institutional ERP:
- Checking server status
- Fetching employee directory
- Authenticating credentials
- Submitting biometric attendance punches
- Polling kiosk recent events

Usage:
    locust -f tools/locustfile.py --headless -u 50 -r 10 --run-time 30s --host http://127.0.0.1:5000
"""

import random
from locust import HttpUser, task, between

FACULTY_ACCOUNTS = [
    ("F001", "password123"),
    ("F002", "password123"),
    ("F003", "password123"),
    ("F004", "password123"),
    ("F005", "password123"),
]


class FacultyERPUser(HttpUser):
    """Simulated faculty member check-in and dashboard browsing user."""
    wait_time = between(0.1, 0.5)

    def on_start(self):
        """Select a simulated faculty profile on startup."""
        self.emp_code, self.password = random.choice(FACULTY_ACCOUNTS)

    @task(4)
    def check_health(self):
        """Query server status endpoint."""
        self.client.get("/api/status", name="/api/status")

    @task(3)
    def list_employees(self):
        """Fetch employee directory."""
        self.client.get("/api/employees", name="/api/employees")

    @task(2)
    def verify_identity(self):
        """Submit password verification."""
        self.client.post(
            "/api/verify-credentials",
            json={"employee_code": self.emp_code, "password": self.password},
            name="/api/verify-credentials",
        )

    @task(1)
    def punch_attendance(self):
        """Submit simulated biometric punch."""
        self.client.post(
            "/api/punch",
            json={
                "employee_code": self.emp_code,
                "punch_type": "AUTO",
                "auth_method": "LOCUST_BENCHMARK",
                "biometric_proof": "locust_proof_hash",
            },
            name="/api/punch",
        )

    @task(3)
    def poll_kiosk_feed(self):
        """Poll recent attendance feed."""
        self.client.get("/api/kiosk/recent", name="/api/kiosk/recent")
