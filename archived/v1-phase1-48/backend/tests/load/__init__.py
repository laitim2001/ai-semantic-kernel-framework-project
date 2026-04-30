"""
IPA Platform - Load Tests

This package contains load testing scripts using Locust
for performance validation.

Usage:
    locust -f tests/load/locustfile.py --host=http://localhost:8000
    locust -f tests/load/locustfile.py --host=http://localhost:8000 --headless -u 50 -r 5 -t 10m

Parameters:
    -u: Number of users
    -r: Spawn rate (users per second)
    -t: Test duration
"""
