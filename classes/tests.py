from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from classes.models import ClassGroup, ClassMeeting
from members.models import Member
from accounts.models import UserProfile
from attendance.models import ClassAttendanceRecord
import datetime
from django.utils import timezone

User = get_user_model()


class ClassGroupModelTestCase(TestCase):
    def test_class_creation(self):
        cls = ClassGroup.objects.create(
            name='Class A (St. Peter)',
            description='Main bible study class',
            category='BIBLE_STUDY',
            location='Main Chapel',
            meeting_time='Wednesdays, 6:00 PM',
            capacity=25,
            is_active=True
        )
        self.assertEqual(str(cls), 'Class A (St. Peter)')
        self.assertEqual(cls.category, 'BIBLE_STUDY')
        self.assertTrue(cls.is_active)
        self.assertEqual(cls.occupancy_rate, 0)
        self.assertFalse(cls.is_full)

    def test_member_count_and_occupancy(self):
        cls = ClassGroup.objects.create(name='Class B', capacity=10)
        m1 = Member.objects.create(first_name='Abena', last_name='Osei', gender='F', status='ACTIVE', assigned_class=cls)
        m2 = Member.objects.create(first_name='Kwame', last_name='Mensah', gender='M', status='ACTIVE', assigned_class=cls)
        self.assertEqual(cls.member_count, 2)
        self.assertEqual(cls.total_members, 2)
        self.assertEqual(cls.occupancy_rate, 20.0)

        # Fill up
        for i in range(8):
            Member.objects.create(first_name=f'M{i}', last_name='Test', gender='M', status='ACTIVE', assigned_class=cls)
        self.assertTrue(cls.is_full)
        self.assertEqual(cls.occupancy_rate, 100.0)


class ClassMeetingModelTestCase(TestCase):
    def test_meeting_creation(self):
        cls = ClassGroup.objects.create(name='Class A')
        meeting = ClassMeeting.objects.create(
            class_group=cls,
            date='2026-08-24',
            topic='Faith and Works',
            start_time='18:00',
            end_time='19:30'
        )
        self.assertEqual(str(meeting), 'Class A - 2026-08-24')
        self.assertEqual(meeting.topic, 'Faith and Works')

    def test_unique_together(self):
        cls = ClassGroup.objects.create(name='Class A')
        ClassMeeting.objects.create(class_group=cls, date='2026-08-24')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            ClassMeeting.objects.create(class_group=cls, date='2026-08-24')


class ClassViewsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='Password123!')
        UserProfile.objects.create(user=self.user, role='ADMIN')
        self.leader = User.objects.create_user(username='leader', password='pass', first_name='Beatrice', last_name='Osei')
        UserProfile.objects.create(user=self.leader, role='CLASS_LEADER')

        self.class1 = ClassGroup.objects.create(
            name='Class 1 (St. Peter)',
            category='BIBLE_STUDY',
            location='Main Chapel',
            meeting_time='Wednesdays, 6:00 PM',
            capacity=25,
            leader=self.leader,
            is_active=True
        )
        self.class2 = ClassGroup.objects.create(
            name='Youth Class',
            category='YOUTH',
            location='Youth Hall',
            meeting_time='Saturdays, 4:00 PM',
            capacity=30,
            is_active=True
        )
        self.member = Member.objects.create(first_name='Ama', last_name='Serwaa', gender='F', status='ACTIVE', assigned_class=self.class1)

    def test_class_list_requires_login(self):
        response = self.client.get(reverse('classes:class_list'))
        self.assertEqual(response.status_code, 302)

    def test_class_list_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('classes:class_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bible Study Classes')
        self.assertContains(response, 'Class 1 (St. Peter)')

    def test_class_list_search(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('classes:class_list') + '?q=St. Peter')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Class 1 (St. Peter)')

    def test_class_list_filter_category(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('classes:class_list') + '?category=YOUTH')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Youth Class')

    def test_class_detail_view(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('classes:class_detail') + f'?id={self.class1.id}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Class 1 (St. Peter)')
        self.assertContains(response, 'Ama Serwaa')

    def test_class_detail_search_member(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('classes:class_detail') + f'?id={self.class1.id}&q=Ama')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ama Serwaa')

    def test_add_edit_class_get(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('classes:add_edit_class'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add New Class')

    def test_add_class_create(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('classes:add_edit_class'), {
            'action': 'create',
            'name': 'New Convert Class',
            'description': 'For new converts',
            'category': 'NEW_CONVERT',
            'location': 'Room 2',
            'meeting_time': 'Sundays, 9:00 AM',
            'capacity': '20',
            'is_active': 'on',
            'leader': self.leader.id,
        })
        self.assertRedirects(response, reverse('classes:class_list'))
        self.assertTrue(ClassGroup.objects.filter(name='New Convert Class').exists())
        new_cls = ClassGroup.objects.get(name='New Convert Class')
        self.assertEqual(new_cls.capacity, 20)
        self.assertEqual(new_cls.leader, self.leader)

    def test_add_class_duplicate_fails(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('classes:add_edit_class'), {
            'action': 'create',
            'name': 'Class 1 (St. Peter)',
            'category': 'BIBLE_STUDY',
            'capacity': '25',
        })
        self.assertRedirects(response, reverse('classes:add_edit_class'))
        self.assertEqual(ClassGroup.objects.filter(name='Class 1 (St. Peter)').count(), 1)

    def test_edit_class(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('classes:add_edit_class') + f'?edit={self.class1.id}', {
            'action': 'edit',
            'name': 'Class 1 Updated',
            'description': 'Updated description',
            'category': 'BIBLE_STUDY',
            'location': 'Main Chapel Updated',
            'meeting_time': 'Wednesdays, 7:00 PM',
            'capacity': '30',
            'is_active': 'on',
            'leader': self.leader.id,
        })
        self.assertRedirects(response, reverse('classes:class_list'))
        self.class1.refresh_from_db()
        self.assertEqual(self.class1.name, 'Class 1 Updated')
        self.assertEqual(self.class1.capacity, 30)

    def test_class_attendance_record_view(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('classes:class_attendance_record'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Class Attendance')

    def test_class_attendance_record_create(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('classes:class_attendance_record'), {
            'action': 'record',
            'class_id': self.class1.id,
            'date': '2026-08-25',
            'present_members': [self.member.id],
            'remarks': 'Good attendance',
        })
        self.assertRedirects(response, reverse('classes:class_attendance_report'))
        self.assertTrue(ClassAttendanceRecord.objects.filter(date='2026-08-25', class_group=self.class1).exists())

    def test_class_attendance_report_view(self):
        self.client.force_login(self.user)
        # Create record
        rec = ClassAttendanceRecord.objects.create(class_group=self.class1, date='2026-08-24')
        rec.present_members.set([self.member])
        response = self.client.get(reverse('classes:class_attendance_report'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Class Attendance Report')
        self.assertContains(response, 'Class 1 (St. Peter)')

    def test_class_attendance_report_filter(self):
        self.client.force_login(self.user)
        rec = ClassAttendanceRecord.objects.create(class_group=self.class1, date='2026-08-24')
        response = self.client.get(reverse('classes:class_attendance_report') + f'?class_filter={self.class1.id}')
        self.assertEqual(response.status_code, 200)