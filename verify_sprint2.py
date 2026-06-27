import requests
import sys
import random
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:8000"

def check(label, condition):
    if condition:
        print(f"  [PASS] {label}")
    else:
        print(f"  [FAIL] {label}")
        sys.exit(1)

def register_and_login(email, role, interests, faculty, department):
    res = requests.post(f"{BASE_URL}/api/auth/register/", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Test User",
        "department": department,
        "faculty": faculty,
        "role": role,
        "interests": interests
    })
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


def score_event_locally(event, user_categories, user_faculty, user_dept):
    """Mirror the server-side scoring so we can print scores."""
    score = 0
    if event['category'] in user_categories:
        score += 2
    tf = event.get('target_faculty')
    if not tf or tf == user_faculty:
        score += 1
    td = event.get('target_department')
    if not td or td == user_dept:
        score += 1
    return score


rid = random.randint(10000, 99999)
future_date = (datetime.now() + timedelta(days=3)).isoformat() + "Z"

# ── Step A: Register and login ORGANISER ─────────────────────────────────
print("\n[A] Register and login ORGANISER")
org_token = register_and_login(f"org_s2v2_{rid}@test.com", "organiser", ["technology"], "Computing", "CS")

# ── Step B: Create 3 events ─────────────────────────────────────────────
print("\n[B] Create 3 test events")
events_data = [
    {
        "title": "Academic Computing Seminar",
        "description": "Deep dive into algorithms",
        "category": "academic",
        "date_time": future_date,
        "venue": "Hall A",
        "capacity": 100,
        "event_type": "free",
        "ticket_price": "0.00",
        "target_faculty": "Computing",
        "target_department": None      # open to all departments
    },
    {
        "title": "Cultural Night",
        "description": "University-wide cultural celebration",
        "category": "cultural",
        "date_time": future_date,
        "venue": "Main Auditorium",
        "capacity": 200,
        "event_type": "free",
        "ticket_price": "0.00",
        "target_faculty": None,        # open to all faculties
        "target_department": None       # open to all departments
    },
    {
        "title": "Arts Faculty Sports Day",
        "description": "Sports competition for Arts students",
        "category": "sports",
        "date_time": future_date,
        "venue": "Sports Complex",
        "capacity": 150,
        "event_type": "free",
        "ticket_price": "0.00",
        "target_faculty": "Arts",
        "target_department": None       # open to all departments within Arts
    },
]

event_ids = []
for ev in events_data:
    res = requests.post(f"{BASE_URL}/api/events/", json=ev, headers={"Authorization": f"Bearer {org_token}"})
    check(f"Created: {ev['title']}", res.status_code == 201)
    event_ids.append(res.json()['id'])

# ── Step C: Register STUDENT 1 ──────────────────────────────────────────
print("\n[C] Register STUDENT 1 (interests=[academic], faculty=Computing, dept=Computer Science)")
stu1_token = register_and_login(f"stu1_s2v2_{rid}@test.com", "student", ["academic"], "Computing", "Computer Science")

# ── Step D+E: Recommended events for Student 1 ──────────────────────────
print("\n[D/E] Recommended events for STUDENT 1:")
res = requests.get(f"{BASE_URL}/api/events/recommended/", headers={"Authorization": f"Bearer {stu1_token}"})
all_rec1 = res.json()

# Filter to only the 3 events created in this test run
rec1 = [e for e in all_rec1 if e['id'] in event_ids]

stu1_cats = ["academic"]
stu1_fac = "Computing"
stu1_dept = "Computer Science"

print(f"  Student profile: interests={stu1_cats}, faculty={stu1_fac}, dept={stu1_dept}")
print(f"  (Showing only the 3 test events out of {len(all_rec1)} total)")
print(f"  {'Rank':<6} {'Title':<30} {'Category':<12} {'Target Fac':<14} {'Target Dept':<14} {'Score'}")
print(f"  {'-'*6} {'-'*30} {'-'*12} {'-'*14} {'-'*14} {'-'*5}")
for i, ev in enumerate(rec1, 1):
    sc = score_event_locally(ev, stu1_cats, stu1_fac, stu1_dept)
    tf = ev.get('target_faculty') or '(open)'
    td = ev.get('target_department') or '(open)'
    print(f"  {i:<6} {ev['title']:<30} {ev['category']:<12} {tf:<14} {td:<14} {sc}")

check("Event 1 (academic+Computing) is FIRST with score 4", 
      rec1[0]['category'] == 'academic' and score_event_locally(rec1[0], stu1_cats, stu1_fac, stu1_dept) == 4)
check("Event 2 (cultural, open) is SECOND with score 2",
      rec1[1]['category'] == 'cultural' and score_event_locally(rec1[1], stu1_cats, stu1_fac, stu1_dept) == 2)
check("Event 3 (sports, Arts) is LAST with score 1",
      rec1[2]['category'] == 'sports' and score_event_locally(rec1[2], stu1_cats, stu1_fac, stu1_dept) == 1)

# ── Step F: Register STUDENT 2 (no matching interests/faculty) ───────────
print("\n[F] Register STUDENT 2 (interests=[social], faculty=Arts, dept=Fine Arts)")
stu2_token = register_and_login(f"stu2_s2v2_{rid}@test.com", "student", ["social"], "Arts", "Fine Arts")

print("\n    Recommended events for STUDENT 2:")
res = requests.get(f"{BASE_URL}/api/events/recommended/", headers={"Authorization": f"Bearer {stu2_token}"})
all_rec2 = res.json()

# Filter to only the 3 events created in this test run
rec2 = [e for e in all_rec2 if e['id'] in event_ids]

stu2_cats = ["social"]
stu2_fac = "Arts"
stu2_dept = "Fine Arts"

print(f"  Student profile: interests={stu2_cats}, faculty={stu2_fac}, dept={stu2_dept}")
print(f"  (Showing only the 3 test events out of {len(all_rec2)} total)")
print(f"  {'Rank':<6} {'Title':<30} {'Category':<12} {'Target Fac':<14} {'Target Dept':<14} {'Score'}")
print(f"  {'-'*6} {'-'*30} {'-'*12} {'-'*14} {'-'*14} {'-'*5}")
for i, ev in enumerate(rec2, 1):
    sc = score_event_locally(ev, stu2_cats, stu2_fac, stu2_dept)
    tf = ev.get('target_faculty') or '(open)'
    td = ev.get('target_department') or '(open)'
    print(f"  {i:<6} {ev['title']:<30} {ev['category']:<12} {tf:<14} {td:<14} {sc}")

check("Student 2 sees all 3 test events", len(rec2) == 3)
order1 = [e['id'] for e in rec1]
order2 = [e['id'] for e in rec2]
check("Ranking order differs between Student 1 and Student 2", order1 != order2)

# ── Step G: Student tries to create event (should be 403) ───────────────
print("\n[G] Student tries to create an event")
res = requests.post(f"{BASE_URL}/api/events/", json=events_data[0], headers={"Authorization": f"Bearer {stu1_token}"})
check("Rejected with 403 Forbidden", res.status_code == 403)

# ── Step H: Different organiser tries to edit/cancel (should be 403) ────
print("\n[H] Different organiser tries to edit/cancel another's event")
org2_token = register_and_login(f"org2_s2v2_{rid}@test.com", "organiser", ["sports"], "Arts", "Drama")

target_id = event_ids[0]
res = requests.put(f"{BASE_URL}/api/events/{target_id}/", json={"title": "Hacked"}, headers={"Authorization": f"Bearer {org2_token}"})
check("Edit rejected with 403 Forbidden", res.status_code == 403)

res = requests.delete(f"{BASE_URL}/api/events/{target_id}/", headers={"Authorization": f"Bearer {org2_token}"})
check("Cancel rejected with 403 Forbidden", res.status_code == 403)

print("\n" + "=" * 65)
print("  ALL CHECKS PASSED SUCCESSFULLY!")
print("=" * 65)
