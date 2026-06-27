import requests
import json
import sys
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:8000"

def print_step(msg):
    print(f"\n[STEP] {msg}")

def check(label, condition):
    if condition:
        print(f"  [PASS] {label}")
    else:
        print(f"  [FAIL] {label}")
        sys.exit(1)

def register_and_login(email, role, interests, faculty):
    res = requests.post(f"{BASE_URL}/api/auth/register/", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Test User",
        "department": "CS",
        "faculty": faculty,
        "role": role,
        "interests": interests
    })
    # If 400 because email already exists, just login
    if res.status_code == 400 and "already exists" in str(res.json()):
        pass
    elif res.status_code != 201:
        print("Registration failed:", res.json())
        sys.exit(1)
        
    res = requests.post(f"{BASE_URL}/api/auth/login/", json={
        "email": email,
        "password": "Password123!"
    })
    if res.status_code != 200:
        print("Login failed:", res.json())
        sys.exit(1)
    return res.json()['access']

# ── Clean up db first to ensure tests pass ──
# Not deleting db, just making sure emails are unique
import random
rid = random.randint(1000, 9999)

# a. Register & login organiser
print_step("Register and login ORGANISER")
org1_token = register_and_login(f"org1_{rid}@test.com", "organiser", ["technology"], "Computing")

# b. Create 3 events as organiser
print_step("Create 3 events as ORGANISER")
future_date = (datetime.now() + timedelta(days=3)).isoformat() + "Z"

events = [
    {"title": "Cultural Event", "description": "Desc", "category": "cultural", "date_time": future_date, "venue": "Hall B", "capacity": 100, "event_type": "free", "ticket_price": "0.00"},
    {"title": "Sports Event", "description": "Desc", "category": "sports", "date_time": future_date, "venue": "Field", "capacity": 100, "event_type": "free", "ticket_price": "0.00"},
    {"title": "Academic Event", "description": "Desc", "category": "academic", "date_time": future_date, "venue": "Hall A", "capacity": 100, "event_type": "free", "ticket_price": "0.00"}
]

event_ids = []
for ev in events:
    res = requests.post(f"{BASE_URL}/api/events/", json=ev, headers={"Authorization": f"Bearer {org1_token}"})
    check(f"Created event: {ev['title']}", res.status_code == 201)
    event_ids.append(res.json()['id'])

# c. Register & login student matching 'academic' and 'Computing'
print_step("Register and login STUDENT 1 (academic, Computing)")
stu1_token = register_and_login(f"stu1_{rid}@test.com", "student", ["academic"], "Computing")

# d & e. Get recommended events for Student 1
print_step("Get recommended events for STUDENT 1")
res = requests.get(f"{BASE_URL}/api/events/recommended/", headers={"Authorization": f"Bearer {stu1_token}"})
rec_events1 = res.json()
print("  Ranking for Student 1:")
for ev in rec_events1:
    print(f"    - {ev['title']} (Cat: {ev['category']}, Fac: {ev['organiser']['full_name']})")

check("Academic event is FIRST (matches both interest and faculty)", rec_events1[0]['title'] == "Academic Event")

# f. Register & login student matching nothing
print_step("Register and login STUDENT 2 (social, Arts)")
stu2_token = register_and_login(f"stu2_{rid}@test.com", "student", ["social"], "Arts")

print_step("Get recommended events for STUDENT 2")
res = requests.get(f"{BASE_URL}/api/events/recommended/", headers={"Authorization": f"Bearer {stu2_token}"})
rec_events2 = res.json()
print("  Ranking for Student 2:")
for ev in rec_events2:
    print(f"    - {ev['title']} (Cat: {ev['category']}, Fac: {ev['organiser']['full_name']})")

order1 = [e['id'] for e in rec_events1]
order2 = [e['id'] for e in rec_events2]
check("Order is different for Student 2", order1 != order2)

# g. Student tries to create an event
print_step("Student tries to create an event")
res = requests.post(f"{BASE_URL}/api/events/", json=events[0], headers={"Authorization": f"Bearer {stu1_token}"})
check("Rejected with 403 Forbidden", res.status_code == 403)

# h. Different organiser tries to edit/cancel event
print_step("Different organiser tries to edit/cancel event")
org2_token = register_and_login(f"org2_{rid}@test.com", "organiser", ["sports"], "Computing")

target_event_id = event_ids[0]
res = requests.put(f"{BASE_URL}/api/events/{target_event_id}/", json={"title": "Hacked"}, headers={"Authorization": f"Bearer {org2_token}"})
check("Edit rejected with 403 Forbidden", res.status_code == 403)

res = requests.delete(f"{BASE_URL}/api/events/{target_event_id}/", headers={"Authorization": f"Bearer {org2_token}"})
check("Cancel rejected with 403 Forbidden", res.status_code == 403)

print("\nALL CHECKS PASSED SUCCESSFULLY!")
