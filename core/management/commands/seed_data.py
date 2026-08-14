from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import UserProfile
from classes.models import ClassGroup
from organisations.models import Organisation
from members.models import Member
from welfare_cases.models import WelfareCase, VisitationLog, WelfareDisbursement
from finance.models import IncomeLedger, ExpenseLedger, Budget
from services.models import ChurchService
from attendance.models import ServiceAttendance
from communications.models import Announcement
import datetime

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds initial sample data for MCG Welfare System'

    def handle(self, *args, **options):
        self.stdout.write("Seeding sample data...")

        # 1. Create Users
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@mcgwelfare.org',
                'first_name': 'System',
                'last_name': 'Administrator',
                'is_staff': True,
                'is_superuser': True
            }
        )
        admin_user.set_password('admin123')
        admin_user.save()
        UserProfile.objects.get_or_create(user=admin_user, defaults={'role': 'ADMIN', 'title': 'System Administrator'})

        treasurer_user, _ = User.objects.get_or_create(
            username='treasurer',
            defaults={
                'email': 'treasurer@mcgwelfare.org',
                'first_name': 'Kofi',
                'last_name': 'Boateng' 
            }
        )
        treasurer_user.set_password('treasurer123')
        treasurer_user.save()
        UserProfile.objects.get_or_create(user=treasurer_user, defaults={'role': 'TREASURER', 'title': 'Society Treasurer'})

        class_leader_user, _ = User.objects.get_or_create(
            username='classleader',
            defaults={
                'email': 'leader@mcgwelfare.org',
                'first_name': 'Kwame',
                'last_name': 'Mensah'
            }
        )
        class_leader_user.set_password('leader123')
        class_leader_user.save()
        UserProfile.objects.get_or_create(user=class_leader_user, defaults={'role': 'CLASS_LEADER', 'title': 'Class Leader'})

        # 2. Create Classes
        c1, _ = ClassGroup.objects.get_or_create(name='Ebenezer Class', defaults={'description': 'Sunday morning Bible study', 'leader': class_leader_user, 'meeting_time': 'Sundays 8:00 AM'})
        c2, _ = ClassGroup.objects.get_or_create(name='John Wesley Class', defaults={'description': 'Mid-week prayer and study', 'meeting_time': 'Wednesdays 6:00 PM'})
        c3, _ = ClassGroup.objects.get_or_create(name='Calvary Class', defaults={'description': 'Youth & Young Adults Bible class', 'meeting_time': 'Fridays 6:30 PM'})

        # 3. Create Organisations
        org1, _ = Organisation.objects.get_or_create(name="Women's Fellowship", defaults={'description': 'Society Women Guild', 'meeting_schedule': 'Tuesdays 5:00 PM'})
        org2, _ = Organisation.objects.get_or_create(name="Men's Fellowship", defaults={'description': 'Society Men Fellowship', 'meeting_schedule': 'Saturdays 7:00 AM'})

        # 4. Create Members
        m1, _ = Member.objects.get_or_create(
            first_name='Abena', last_name='Ofori',
            defaults={'gender': 'F', 'date_of_birth': '1985-04-12', 'phone_number': '0244123456', 'email': 'abena.ofori@example.com', 'assigned_class': c1, 'status': 'ACTIVE', 'emergency_contact_name': 'Yaw Ofori', 'emergency_contact_phone': '0244999888'}
        )
        m2, _ = Member.objects.get_or_create(
            first_name='Kwaku', last_name='Addo',
            defaults={'gender': 'M', 'date_of_birth': '1978-09-25', 'phone_number': '0208112233', 'email': 'kwaku.addo@example.com', 'assigned_class': c2, 'status': 'ACTIVE', 'emergency_contact_name': 'Akosua Addo', 'emergency_contact_phone': '0208776655'}
        )
        m3, _ = Member.objects.get_or_create(
            first_name='Ama', last_name='Serwaa',
            defaults={'gender': 'F', 'date_of_birth': '1992-11-05', 'phone_number': '0277445566', 'email': 'ama.serwaa@example.com', 'assigned_class': c3, 'status': 'PENDING'}
        )
        m4, _ = Member.objects.get_or_create(
            first_name='Yaw', last_name='Asare',
            defaults={'gender': 'M', 'date_of_birth': '1965-01-30', 'phone_number': '0243332211', 'email': 'yaw.asare@example.com', 'assigned_class': c1, 'status': 'ACTIVE'}
        )

        # 5. Create Welfare Cases
        wcase1, _ = WelfareCase.objects.get_or_create(
            title='Medical Support for Surgery',
            defaults={
                'member': m1,
                'case_type': 'MEDICAL',
                'description': 'Assistance for eye surgery medical bills at Korle Bu Teaching Hospital.',
                'requested_amount': 2500.00,
                'approved_amount': 2000.00,
                'status': 'APPROVED',
                'assigned_officer': admin_user
            }
        )
        wcase2, _ = WelfareCase.objects.get_or_create(
            title='Bereavement Support',
            defaults={
                'member': m2,
                'case_type': 'BEREAVEMENT',
                'description': 'Funeral support for late mother.',
                'requested_amount': 1500.00,
                'approved_amount': 1500.00,
                'status': 'DISBURSED',
                'assigned_officer': admin_user
            }
        )
        WelfareDisbursement.objects.get_or_create(
            welfare_case=wcase2,
            defaults={'amount': 1500.00, 'disbursement_date': datetime.date.today(), 'payment_method': 'Mobile Money', 'reference_number': 'MM-8849201'}
        )

        VisitationLog.objects.get_or_create(
            welfare_case=wcase1,
            defaults={'visit_date': datetime.date.today(), 'visitors': 'Rev. Mensah, Sister Grace', 'findings': 'Patient recovering well. Recommended GHS 2000 disbursement.', 'recommendation': 'Approve funding.'}
        )

        # 6. Finance Entries
        IncomeLedger.objects.get_or_create(category='TITHE', amount=8500.00, date=datetime.date.today(), defaults={'remarks': 'Sunday tithes collection', 'recorded_by': treasurer_user})
        IncomeLedger.objects.get_or_create(category='OFFERING', amount=3200.00, date=datetime.date.today(), defaults={'remarks': 'Sunday main service offering', 'recorded_by': treasurer_user})
        IncomeLedger.objects.get_or_create(category='WELFARE', amount=1800.00, date=datetime.date.today(), defaults={'remarks': 'Monthly welfare dues', 'recorded_by': treasurer_user})

        ExpenseLedger.objects.get_or_create(title='Church Hall Electricity Bill', defaults={'category': 'Utilities', 'amount': 750.00, 'date': datetime.date.today(), 'status': 'APPROVED', 'recorded_by': treasurer_user, 'approved_by': admin_user})
        ExpenseLedger.objects.get_or_create(title='Sound System Maintenance', defaults={'category': 'Maintenance', 'amount': 450.00, 'date': datetime.date.today(), 'status': 'PENDING', 'recorded_by': treasurer_user})

        Budget.objects.get_or_create(fiscal_year=2026, category='Welfare Support', defaults={'allocated_amount': 25000.00, 'notes': 'Annual welfare fund allocation'})
        Budget.objects.get_or_create(fiscal_year=2026, category='Utilities & Admin', defaults={'allocated_amount': 15000.00, 'notes': 'Annual administrative budget'})

        # 7. Services & Attendance
        s1, _ = ChurchService.objects.get_or_create(
            title='Sunday Divine Service',
            defaults={'service_date': datetime.date.today(), 'start_time': '09:00:00', 'end_time': '11:30:00', 'preacher': 'Rev. Dr. Ekow Mensah', 'liturgist': 'Bro. Yaw Asare', 'theme': 'Walking in Divine Grace'}
        )
        ServiceAttendance.objects.get_or_create(
            service=s1,
            defaults={'male_count': 120, 'female_count': 165, 'children_count': 45}
        )

        # 8. Announcements
        Announcement.objects.get_or_create(
            title='Quarterly Leaders Meeting Notice',
            defaults={'content': 'All Leaders, Society Stewards, and Guild Executives are reminded of the quarterly meeting this Saturday at 10:00 AM.', 'is_active': True, 'created_by': admin_user}
        )

        self.stdout.write(self.style.SUCCESS("Successfully seeded sample data!"))
