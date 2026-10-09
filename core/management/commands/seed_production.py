from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random
import secrets

class Command(BaseCommand):
    help = 'Seeds production database with super admin, sample events, tickets, and dashboard analytics'

    def handle(self, *args, **options):
        from core.models import User, Event, Ticket, Payment, Notification, Interest

        self.stdout.write("Seeding production database...")

        # 0. Import pre-production accounts from users_dump.json
        import os, json
        dump_path = os.path.join(os.path.dirname(__file__), 'users_dump.json')
        if os.path.exists(dump_path):
            try:
                with open(dump_path, 'r', encoding='utf-8') as f:
                    dumped_users = json.load(f)
                imported_count = 0
                for u in dumped_users:
                    email = u.get('email', '').strip()
                    if not email:
                        continue
                    u_obj, _ = User.objects.get_or_create(
                        email=email,
                        defaults={
                            'username': u.get('username') or email,
                            'first_name': u.get('first_name', ''),
                            'last_name': u.get('last_name', ''),
                            'role': u.get('role', 'student'),
                            'department': u.get('department', ''),
                            'faculty': u.get('faculty', ''),
                            'is_staff': u.get('is_staff', False),
                            'is_superuser': u.get('is_superuser', False),
                        }
                    )
                    # Restore exact hashed password from pre-production
                    if u.get('password'):
                        u_obj.password = u['password']
                    u_obj.role = u.get('role', 'student')
                    u_obj.is_staff = u.get('is_staff', False)
                    u_obj.is_superuser = u.get('is_superuser', False)
                    u_obj.save()
                    imported_count += 1
                self.stdout.write(f"Restored {imported_count} pre-production user accounts.")
            except Exception as e:
                self.stdout.write(f"Warning: could not import users_dump: {e}")

        # 1. Guaranteed Super Admin Users (Both correct spelling and previous typo)
        for admin_email in ['mahmudlawanalkasim@gmail.com', 'amhmudlawanalkasim@gmail.com']:
            admin_user, _ = User.objects.get_or_create(
                email=admin_email,
                defaults={
                    'username': admin_email.split('@')[0],
                    'first_name': 'Mahmud',
                    'last_name': 'Lawan Alkasim',
                    'role': 'admin',
                    'is_staff': True,
                    'is_superuser': True,
                    'department': 'Computer Science',
                    'faculty': 'Science',
                }
            )
            admin_user.set_password('Mah@236900')
            admin_user.role = 'admin'
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.save()
            for cat in ['technology', 'academic']:
                Interest.objects.get_or_create(user=admin_user, category=cat)
            self.stdout.write(f"Super admin confirmed: {admin_email}")

        # Guaranteed Organiser
        org_user, _ = User.objects.get_or_create(
            email='abutturab236900@gmail.com',
            defaults={
                'username': 'MAHMUD',
                'first_name': 'Mahmud',
                'last_name': 'Lawan',
                'role': 'organiser',
                'is_staff': True,
            }
        )
        org_user.set_password('Mah@236900')
        org_user.role = 'organiser'
        org_user.is_staff = True
        org_user.save()
        self.stdout.write("Organiser confirmed: abutturab236900@gmail.com")

        # Guaranteed Student accounts with Mah@236900
        for s_email, s_name in [
            ('sukainatlawan@gmail.com', 'Sukainat'),
            ('aliyulawan@gmail.com', 'Aliyu'),
            ('ahmadlawan@gmail.com', 'Ahmad'),
        ]:
            stu_obj, _ = User.objects.get_or_create(
                email=s_email,
                defaults={
                    'username': s_name,
                    'first_name': s_name,
                    'last_name': 'Lawan',
                    'role': 'student',
                }
            )
            stu_obj.set_password('Mah@236900')
            stu_obj.role = 'student'
            stu_obj.save()
            self.stdout.write(f"Student confirmed: {s_email}")

        # 2. Student Demo Users
        student_email = 'student@futb.edu.ng'
        student_user, _ = User.objects.get_or_create(
            email=student_email,
            defaults={
                'username': 'student_demo',
                'first_name': 'Amina',
                'last_name': 'Ibrahim',
                'role': 'student',
                'department': 'Software Engineering',
                'faculty': 'Science',
            }
        )
        student_user.set_password('Password123!')
        student_user.role = 'student'
        student_user.save()
        for cat in ['technology', 'sports', 'social']:
            Interest.objects.get_or_create(user=student_user, category=cat)

        # 3. Sample Events
        now = timezone.now()
        events_data = [
            {
                'title': 'FUTB Annual Tech Summit & Innovation Expo 2026',
                'description': 'The biggest campus technology gathering featuring keynote speakers from top Nigerian tech hubs, startup pitches, and AI robotics demonstrations.',
                'category': 'technology',
                'date_time': now + timedelta(days=14, hours=10),
                'venue': 'Main Campus Auditorium, Complex A',
                'capacity': 500,
                'event_type': 'free',
                'ticket_price': 0.00,
            },
            {
                'title': 'Campus Hackathon: Smart Campus Solutions',
                'description': 'A 48-hour competitive coding hackathon addressing campus logistical, security, and educational challenges with prize pools and mentorship.',
                'category': 'technology',
                'date_time': now + timedelta(days=21, hours=9),
                'venue': 'ICT Complex, Lab 3 & 4',
                'capacity': 150,
                'event_type': 'free',
                'ticket_price': 0.00,
            },
            {
                'title': 'Inter-Faculty Football Championship Final',
                'description': 'The climax of the semester intramural football league: Faculty of Science vs Faculty of Engineering for the prestigious VC Cup.',
                'category': 'sports',
                'date_time': now + timedelta(days=7, hours=16),
                'venue': 'FUTB Sports Stadium Pavilion',
                'capacity': 1000,
                'event_type': 'free',
                'ticket_price': 0.00,
            },
            {
                'title': 'Cultural Fiesta & Arts Night',
                'description': 'Celebration of rich cultural heritage across Nigerian ethnic groups featuring traditional dances, music, drama, and authentic cuisines.',
                'category': 'cultural',
                'date_time': now + timedelta(days=28, hours=18),
                'venue': 'Student Center Open Amphitheatre',
                'capacity': 400,
                'event_type': 'paid',
                'ticket_price': 500.00,
            },
            {
                'title': 'Career & Entrepreneurship Masterclass',
                'description': 'Practical career guidance seminar with industry leaders, resume reviews, scholarship application tips, and graduate internship opportunities.',
                'category': 'academic',
                'date_time': now + timedelta(days=10, hours=11),
                'venue': 'Lecture Theatre 1, School of Science',
                'capacity': 300,
                'event_type': 'free',
                'ticket_price': 0.00,
            },
            {
                'title': 'Campus Music Gala & Award Dinner',
                'description': 'End-of-session social celebration featuring student music performances, campus awards presentation, and dinner.',
                'category': 'social',
                'date_time': now + timedelta(days=35, hours=19),
                'venue': 'University Central Garden & Hall',
                'capacity': 600,
                'event_type': 'paid',
                'ticket_price': 1000.00,
            },
        ]

        created_events = []
        for ed in events_data:
            event, e_created = Event.objects.get_or_create(
                title=ed['title'],
                defaults={
                    'organiser': admin_user,
                    'description': ed['description'],
                    'category': ed['category'],
                    'date_time': ed['date_time'],
                    'venue': ed['venue'],
                    'capacity': ed['capacity'],
                    'event_type': ed['event_type'],
                    'ticket_price': ed['ticket_price'],
                    'status': 'published',
                }
            )
            created_events.append(event)
            self.stdout.write(f"Event {'created' if e_created else 'already exists'}: {event.title}")

        # 4. Sample Tickets and Payments for Analytics
        first_event = created_events[0]
        paid_event = created_events[3]

        # Ticket 1 for admin
        Ticket.objects.get_or_create(
            user=admin_user,
            event=first_event,
            defaults={
                'qr_code_hash': secrets.token_hex(16),
                'ticket_type': 'Regular',
                'status': 'active',
            }
        )

        # Ticket 2 for student
        Ticket.objects.get_or_create(
            user=student_user,
            event=first_event,
            defaults={
                'qr_code_hash': secrets.token_hex(16),
                'ticket_type': 'Regular',
                'status': 'used',
                'scanned_at': now - timedelta(hours=2),
            }
        )

        # Paid ticket & payment for paid_event
        paid_ticket, _ = Ticket.objects.get_or_create(
            user=student_user,
            event=paid_event,
            defaults={
                'qr_code_hash': secrets.token_hex(16),
                'ticket_type': 'VIP',
                'status': 'active',
            }
        )

        Payment.objects.get_or_create(
            ticket=paid_ticket,
            defaults={
                'event': paid_event,
                'user': student_user,
                'amount': 500.00,
                'paystack_ref': f'FUTB-REF-{secrets.token_hex(6)}',
                'status': 'success',
                'paid_at': now - timedelta(days=1),
            }
        )

        # 5. Sample Notification
        Notification.objects.get_or_create(
            user=admin_user,
            event=first_event,
            type='push',
            defaults={
                'title': 'Welcome to FUTB Smart Campus!',
                'body': 'Your production environment has been initialized with super admin access and verified campus events.',
                'status': 'sent',
                'sent_at': now,
            }
        )

        self.stdout.write(self.style.SUCCESS("Production seed completed successfully!"))
