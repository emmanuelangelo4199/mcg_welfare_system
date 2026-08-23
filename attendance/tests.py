from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from attendance.models import ServiceAttendance, ClassAttendanceRecord, OrganisationAttendanceRecord, AttendanceSummary, AbsenteeFollowUp
from services.models import ChurchService
from classes.models import ClassGroup
from organisations.models import Organisation
from members.models import Member
from accounts.models import UserProfile
import datetime
from django.utils import timezone

User = get_user_model()


class ServiceAttendanceModelTestCase(TestCase):
    def setUp(self):
        self.service = ChurchService.objects.create(
            title='Sunday Service',
            service_date='2026-08-24',
            start_time='08:00',
            end_time='11:00'
        )

    def test_service_attendance_creation(self):
        att = ServiceAttendance.objects.create(
            service=self.service,
            male_count=30,
            female_count=40,
            children_count=10
        )
        self.assertEqual(att.total_count, 80)
        self.assertEqual(att.male_percentage, 37.5)
        self.assertEqual(att.female_percentage, 50.0)
        self.assertIn('Sunday Service', str(att))

    def test_service_date_auto(self):
        att = ServiceAttendance.objects.create(
            service=self.service,
            male_count=10,
            female_count=10
        )
        self.assertEqual(att.service_date, self.service.service_date)


class ClassAttendanceRecordModelTestCase(TestCase):
    def setUp(self):
        self.class_group = ClassGroup.objects.create(name='Class A')
        self.member1 = Member.objects.create(first_name='Abena', last_name='Osei', gender='F', status='ACTIVE', assigned_class=self.class_group)
        self.member2 = Member.objects.create(first_name='Kwame', last_name='Mensah', gender='M', status='ACTIVE', assigned_class=self.class_group)

    def test_class_attendance_creation(self):
        record = ClassAttendanceRecord.objects.create(
            class_group=self.class_group,
            date='2026-08-24'
        )
        record.present_members.set([self.member1])
        self.assertEqual(record.present_count, 1)
        self.assertEqual(record.absent_count, 1)
        self.assertEqual(record.attendance_rate, 50.0)

    def test_unique_together(self):
        ClassAttendanceRecord.objects.create(class_group=self.class_group, date='2026-08-24')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            ClassAttendanceRecord.objects.create(class_group=self.class_group, date='2026-08-24')


class OrganisationAttendanceModelTestCase(TestCase):
    def test_org_attendance_creation(self):
        org = Organisation.objects.create(name='Choir')
        rec = OrganisationAttendanceRecord.objects.create(
            organisation=org,
            date='2026-08-24',
            attendees_count=25,
            male_count=10,
            female_count=15
        )
        self.assertEqual(rec.attendees_count, 25)
        self.assertIn('Choir', str(rec))


class AttendanceSummaryTestCase(TestCase):
    def test_summary_creation(self):
        summary = AttendanceSummary.objects.create(
            date='2026-08-24',
            total_service_attendance=100,
            total_class_attendance=50,
            total_org_attendance=30,
            total_absentees=5
        )
        self.assertIn('2026-08-24', str(summary))


class AbsenteeFollowUpTestCase(TestCase):
    def test_followup_creation(self):
        member = Member.objects.create(first_name='Abena', last_name='Osei', gender='F', status='ACTIVE')
        fu = AbsenteeFollowUp.objects.create(
            member=member,
            absence_date='2026-08-24',
            reason='Illness',
            follow_up_status='PENDING'
        )
        self.assertEqual(fu.follow_up_status, 'PENDING')
        self.assertIn('Abena Osei', str(fu))


class AttendanceViewsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='Password123!')
        UserProfile.objects.create(user=self.user, role='ADMIN')

        self.service = ChurchService.objects.create(
            title='Sunday Service',
            service_date=timezone.now().date(),
            start_time='08:00',
            status='SCHEDULED'
        )
        self.class_group = ClassGroup.objects.create(name='Class A')
        self.member = Member.objects.create(first_name='Abena', last_name='Osei', gender='F', status='ACTIVE', assigned_class=self.class_group)
        self.org = Organisation.objects.create(name='Choir')

        ServiceAttendance.objects.create(service=self.service, male_count=10, female_count=20, children_count=5)
        ClassAttendanceRecord.objects.create(class_group=self.class_group, date=timezone.now().date())
        OrganisationAttendanceRecord.objects.create(organisation=self.org, date=timezone.now().date(), attendees_count=15)

    def test_overview_requires_login(self):
        response = self.client.get(reverse('attendance:overview'))
        self.assertEqual(response.status_code, 302)

    def test_overview_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('attendance:overview'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Attendance Overview')

    def test_service_attendance_view(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('attendance:service_attendance'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Service Attendance Recording')

    def test_service_attendance_create(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('attendance:service_attendance'), {
            'action': 'create',
            'service_id': self.service.id,
            'male_count': '20',
            'female_count': '30',
            'children_count': '10',
            'notes': 'Good attendance',
        })
        self.assertRedirects(response, reverse('attendance:overview'))
        self.assertTrue(ServiceAttendance.objects.filter(notes='Good attendance').exists())

    def test_service_attendance_invalid_counts(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('attendance:service_attendance'), {
            'action': 'create',
            'service_id': self.service.id,
            'male_count': '-5',
            'female_count': '10',
            'children_count': '5',
        })
        self.assertRedirects(response, reverse('attendance:service_attendance'))

    def test_class_attendance_view(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('attendance:class_attendance'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Class Attendance Recording')

    def test_class_attendance_create(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('attendance:class_attendance'), {
            'action': 'create',
            'class_id': self.class_group.id,
            'date': '2026-08-25',
            'present_members': [self.member.id],
            'remarks': 'Test remarks',
        })
        self.assertRedirects(response, reverse('attendance:overview'))
        self.assertTrue(ClassAttendanceRecord.objects.filter(date='2026-08-25').exists())

    def test_class_attendance_duplicate_fails(self):
        self.client.force_login(self.user)
        ClassAttendanceRecord.objects.create(class_group=self.class_group, date='2026-08-26')
        response = self.client.post(reverse('attendance:class_attendance'), {
            'action': 'create',
            'class_id': self.class_group.id,
            'date': '2026-08-26',
        })
        self.assertRedirects(response, reverse('attendance:class_attendance'))

    def test_org_attendance_view(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('attendance:org_attendance'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Organisation Attendance')

    def test_org_attendance_create(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('attendance:org_attendance'), {
            'action': 'create',
            'org_id': self.org.id,
            'date': '2026-08-25',
            'attendees_count': '20',
            'male_count': '8',
            'female_count': '12',
            'remarks': 'Choir practice',
        })
        self.assertRedirects(response, reverse('attendance:overview'))
        self.assertTrue(OrganisationAttendanceRecord.objects.filter(remarks='Choir practice').exists())

    def test_absentee_report_view(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('attendance:absentee_report'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Absentee Report')

    def test_absentee_followup_create(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('attendance:absentee_report'), {
            'action': 'create_followup',
            'member_id': self.member.id,
            'absence_date': '2026-08-24',
            'reason': 'Illness',
            'follow_up_status': 'CONTACTED',
            'follow_up_notes': 'Called and prayed',
        })
        self.assertRedirects(response, reverse('attendance:absentee_report'))
        self.assertTrue(AbsenteeFollowUp.objects.filter(member=self.member).exists())

    def test_absentee_followup_update(self):
        self.client.force_login(self.user)
        fu = AbsenteeFollowUp.objects.create(
            member=self.member,
            absence_date='2026-08-24',
            follow_up_status='PENDING'
        )
        response = self.client.post(reverse('attendance:absentee_report'), {
            'action': 'update_followup',
            'followup_id': fu.id,
            'follow_up_status': 'VISITED',
            'follow_up_notes': 'Visited home',
        })
        self.assertRedirects(response, reverse('attendance:absentee_report'))
        fu.refresh_from_db()
        self.assertEqual(fu.follow_up_status, 'VISITED')