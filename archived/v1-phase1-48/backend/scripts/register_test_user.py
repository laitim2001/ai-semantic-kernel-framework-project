"""Register and login a test user for development."""
import requests

BASE = 'http://localhost:8000/api/v1/auth'

# Try register new user
r = requests.post(f'{BASE}/register', json={
    'email': 'dev@example.com',
    'password': 'DevTest2024!',
    'full_name': 'Dev Tester'
})
print(f'Register: {r.status_code} — {r.text[:300]}')

# Try login (OAuth2 form data format)
r2 = requests.post(f'{BASE}/login', data={
    'username': 'dev@example.com',
    'password': 'DevTest2024!',
})
print(f'Login: {r2.status_code} — {r2.text[:300]}')
