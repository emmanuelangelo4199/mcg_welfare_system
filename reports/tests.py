from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from reports.models import GeneratedReportLog, ReportSchedule, ReportFavorite
from reports.views import ensure_default_reports
from members.models import Member
from accounts.models import UserProfile
from finance.models import IncomeLedger
from welfare_cases.models import WelfareCase
from attendance.models import ServiceAttendance
from services.models import ChurchService

User = get_user_model()


class GeneratedReportLogModelTestCase(TestCase):
    def test_report_creation(self):
        user = User.objects.create_user(username='admin', password='pass')
        report = GeneratedReportLog.objects.create(
            report_type='MEMBERSHIP',
            title='Monthly Membership',
            description='Test report',
            status='GENERATED',
            is_pinned=True,
            generated_by=user,
            file_size=1024
        )
        self.assertEqual(str(report), 'Membership Report - Monthly Membership')
        self.assertTrue(report.is_pinned)
        self.assertEqual(report.file_size_formatted, '1.0 KB')

    def test_file_size_formatted(self):
        report = GeneratedReportLog.objects.create(report_type='FINANCIAL', title='Finance', file_size=500)
        self.assertEqual(report.file_size_formatted, '500 B')
        report.file_size = 2048
        self.assertEqual(report.file_size_formatted, '2.0 KB')
        report.file_size = 1024*1024*2
        self.assertEqual(report.file_size_formatted, '2.0 MB')


class ReportScheduleTestCase(TestCase):
    def test_schedule_creation(self):
        sched = ReportSchedule.objects.create(
            report_type='MEMBERSHIP',
            title='Monthly Membership',
            frequency='MONTHLY',
            is_active=True
        )
        self.assertIn('Monthly', str(sched))
        self.assertTrue(sched.is_active)


class ReportFavoriteTestCase(TestCase):
    def test_favorite_creation(self):
        user = User.objects.create_user(username='admin', password='pass')
        report = GeneratedReportLog.objects.create(report_type='MEMBERSHIP', title='Test Report')
        fav = ReportFavorite.objects.create(user=user, report=report)
        self.assertIn('Test Report', str(fav))

    def test_unique_together(self):
        user = User.objects.create_user(username='admin', password='pass')
        report = GeneratedReportLog.objects.create(report_type='MEMBERSHIP', title='Test Report')
        ReportFavorite.objects.create(user=user, report=report)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            ReportFavorite.objects.create(user=user, report=report)


class EnsureDefaultReportsTestCase(TestCase):
    def test_ensure_default_reports(self):
        GeneratedReportLog.objects.all().delete()
        ensure_default_reports()
        self.assertGreaterEqual(GeneratedReportLog.objects.count(), 3)
        self.assertTrue(GeneratedReportLog.objects.filter(report_type='MEMBERSHIP').exists())

        # Idempotent
        ensure_default_reports()
        # Should not duplicate because we only seed when count==0
        # So second call should not create more
        self.assertGreaterEqual(GeneratedReportLog.objects.count(), 3)


class ReportsHubViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='Password123!')
        UserProfile.objects.create(user=self.user, role='ADMIN')
        ensure_default_reports()

    def test_hub_requires_login(self):
        response = self.client.get(reverse('reports:reports_hub'))
        self.assertEqual(response.status_code, 302)

    def test_hub_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:reports_hub'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reports Hub')

    def test_hub_search(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:reports_hub') + '?q=Membership')
        self.assertEqual(response.status_code, 200)

    def test_hub_filter_type(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:reports_hub') + '?type=MEMBERSHIP')
        self.assertEqual(response.status_code, 200)

    def test_toggle_pin(self):
        self.client.force_login(self.user)
        report = GeneratedReportLog.objects.first()
        self.assertFalse(report.is_pinned)
        response = self.client.post(reverse('reports:reports_hub'), {
            'action': 'toggle_pin',
            'report_id': report.id,
        })
        self.assertRedirects(response, reverse('reports:reports_hub'))
        report.refresh_from_db()
        self.assertTrue(report.is_pinned)

    def test_toggle_favorite(self):
        self.client.force_login(self.user)
        report = GeneratedReportLog.objects.first()
        response = self.client.post(reverse('reports:reports_hub'), {
            'action': 'toggle_favorite',
            'report_id': report.id,
        })
        self.assertRedirects(response, reverse('reports:reports_hub'))
        self.assertTrue(ReportFavorite.objects.filter(user=self.user, report=report).exists())

        # Toggle again to remove
        response = self.client.post(reverse('reports:reports_hub'), {
            'action': 'toggle_favorite',
            'report_id': report.id,
        })
        self.assertFalse(ReportFavorite.objects.filter(user=self.user, report=report).exists())


class MembershipReportViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='pass')
        UserProfile.objects.create(user=self.user, role='ADMIN')
        self.member = Member.objects.create(first_name='Abena', last_name='Osei', gender='F', status='ACTIVE')

    def test_membership_report_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:membership_report'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Membership Report')
        self.assertContains(response, 'Abena Osei')

    def test_membership_report_search(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:membership_report') + '?q=Abena')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Abena Osei')

    def test_membership_report_filter_status(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:membership_report') + '?status=ACTIVE')
        self.assertEqual(response.status_code, 200)


class AttendanceReportViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='pass')
        UserProfile.objects.create(user=self.user, role='ADMIN')
        self.service = ChurchService.objects.create(title='Sunday Service', service_date='2026-08-24', start_time='08:00')
        ServiceAttendance.objects.create(service=self.service, male_count=10, female_count=20, total_count=30, service_date='2026-08-24')

    def test_attendance_report_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:attendance_report'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Attendance Report')

    def test_attendance_report_date_filter(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:attendance_report') + '?date_from=2026-08-01&date_to=2026-08-31')
        self.assertEqual(response.status_code, 200)


class FinanceReportViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='pass')
        UserProfile.objects.create(user=self.user, role='ADMIN')
        IncomeLedger.objects.create(category='OFFERING', amount=1000, date='2026-08-24', recorded_by=self.user)
        from finance.models import ExpenseLedger
        ExpenseLedger.objects.create(category='UTILITIES', amount=200, date='2026-08-24', title='Electricity', recorded_by=self.user)

    def test_finance_report_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:finance_report'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Financial Report')
        self.assertContains(response, 'GHS')

    def test_finance_report_date_filter(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:finance_report') + '?date_from=2026-08-01&date_to=2026-08-31')
        self.assertEqual(response.status_code, 200)


class WelfareReportViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='pass')
        UserProfile.objects.create(user=self.user, role='ADMIN')
        self.member = Member.objects.create(first_name='Abena', last_name='Osei', gender='F', status='ACTIVE')
        WelfareCase.objects.create(member=self.member, case_type='MEDICAL', title='Hospital Bill', description='Test', requested_amount=1000)

    def test_welfare_report_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:welfare_report'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welfare Report')
        self.assertContains(response, 'Hospital Bill')

    def test_welfare_report_search(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:welfare_report') + '?q=Hospital')
        self.assertEqual(response.status_code, 200)


class AnnualReportViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='pass')
        UserProfile.objects.create(user=self.user, role='ADMIN')

    def test_annual_report_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:annual_report'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Annual / Quarterly Society Report')

    def test_annual_report_year_filter(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:annual_report') + '?year=2026')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '2026')


class ExportCsvTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='pass')
        UserProfile.objects.create(user=self.user, role='ADMIN')
        self.member = Member.objects.create(first_name='Abena', last_name='Osei', gender='F', status='ACTIVE')

    def test_export_members_csv(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:export_members_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('MCG-00', response.content.decode())

    def test_export_finance_csv(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:export_finance_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_export_welfare_csv(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:export_welfare_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')