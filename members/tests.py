from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from classes.models import ClassGroup
from members.models import Member
from organisations.models import Organisation


User = get_user_model()


class MembersTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='member-admin', password='test-password')
        self.class_group = ClassGroup.objects.create(name='Ebenezer Class')
        self.organisation = Organisation.objects.create(name='Methodist Youth Fellowship')
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

    def test_registration_page_requires_authentication(self):
        response = self.client.get(reverse('members:member_registration'))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('members:member_registration')}")

    def test_registration_creates_full_member_record_and_organisations(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('members:member_registration'), {
            'first_name': 'Akosua',
            'middle_name': 'Ama',
            'last_name': 'Mensah',
            'gender': 'F',
            'date_of_birth': '1991-05-14',
            'marital_status': 'MARRIED',
            'occupation': 'Teacher',
            'hometown': 'Kumasi',
            'phone_number': '0241234567',
            'email': 'akosua@example.com',
            'residential_address': '12 Wesley Road, Kumasi',
            'membership_type': 'FULL',
            'date_of_baptism': '2004-09-10',
            'assigned_class': self.class_group.id,
            'organisations': [self.organisation.id],
            'emergency_contact_name': 'Ama Mensah',
            'emergency_contact_relationship': 'Sister',
            'emergency_contact_phone': '0201112222',
        })

        self.assertRedirects(response, reverse('members:member_directory'))
        member = Member.objects.get(first_name='Akosua', last_name='Mensah')
        self.assertEqual(member.status, 'PENDING')
        self.assertEqual(member.middle_name, 'Ama')
        self.assertEqual(member.membership_type, 'FULL')
        self.assertEqual(member.emergency_contact_relationship, 'Sister')
        self.assertEqual(list(member.organisations.all()), [self.organisation])

    def test_registration_preserves_values_when_required_fields_are_missing(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('members:member_registration'), {
            'first_name': 'Abena',
            'last_name': 'Owusu',
            'gender': 'F',
            'membership_type': 'FULL',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enter the member’s date of birth.')
        self.assertContains(response, 'value="Abena"')
        self.assertFalse(Member.objects.filter(first_name='Abena', last_name='Owusu').exists())

    def test_profile_displays_selected_organisations(self):
        self.member.organisations.add(self.organisation)
        self.client.force_login(self.user)

        response = self.client.get(f"{reverse('members:member_profile')}?id={self.member.id}")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Methodist Youth Fellowship')

