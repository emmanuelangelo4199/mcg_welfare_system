from django.test import TestCase
from django.contrib.auth import get_user_model
from members.models import Member
from classes.models import ClassGroup

User = get_user_model()

class MembersTestCase(TestCase):
    def setUp(self):
        self.class_group = ClassGroup.objects.create(name='Ebenezer Class')
        self.member = Member.objects.create(
            first_name='Kofi',
            last_name='Annan',
            gender='M',
            phone_number='0209876543',
            assigned_class=self.class_group,
            status='ACTIVE'
        )

    def test_member_creation(self):
        self.assertEqual(self.member.get_full_name(), "Kofi Annan")
        self.assertEqual(self.member.assigned_class.name, "Ebenezer Class")
        self.assertEqual(str(self.member), "Kofi Annan (Active Full Member)")
