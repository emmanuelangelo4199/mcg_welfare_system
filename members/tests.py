from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from classes.models import ClassGroup
from members.models import Member, MemberRegularisation
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

    def test_registration_page_lists_gender_choices(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('members:member_registration'))

        self.assertContains(response, 'value="M"')
        self.assertContains(response, 'Male')
        self.assertContains(response, 'value="F"')
        self.assertContains(response, 'Female')

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
        self.member.user = self.user
        self.member.save()
        self.member.organisations.add(self.organisation)
        self.client.force_login(self.user)

        response = self.client.get(f"{reverse('members:member_profile')}?id={self.member.id}")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Methodist Youth Fellowship')

    def test_profile_defaults_to_the_logged_in_users_member_record(self):
        self.member.user = self.user
        self.member.save()
        another_user = User.objects.create_user(username='another-member', password='test-password')
        another_member = Member.objects.create(
            user=another_user,
            first_name='Abena',
            last_name='Owusu',
            gender='F',
            assigned_class=self.class_group,
            status='ACTIVE',
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('members:member_profile'))
        self.assertContains(response, 'Kofi Annan')
        self.assertNotContains(response, 'Abena Owusu')

        self.client.force_login(another_user)
        response = self.client.get(reverse('members:member_profile'))
        self.assertContains(response, 'Abena Owusu')
        self.assertNotContains(response, 'Kofi Annan')

    def test_member_cannot_open_another_members_profile(self):
        self.member.user = self.user
        self.member.save()
        another_user = User.objects.create_user(username='another-member', password='test-password')
        another_member = Member.objects.create(
            user=another_user,
            first_name='Abena',
            last_name='Owusu',
            gender='F',
        )

        self.client.force_login(self.user)
        response = self.client.get(f"{reverse('members:member_profile')}?id={another_member.id}")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kofi Annan')
        self.assertNotContains(response, 'Abena Owusu')

    def test_staff_without_a_member_record_does_not_see_the_first_member(self):
        UserProfile.objects.create(user=self.user, role='ADMIN')
        self.client.force_login(self.user)

        response = self.client.get(reverse('members:member_profile'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No member profile to display')
        self.assertNotContains(response, 'Kofi Annan')

    def test_staff_directory_link_can_open_an_explicit_member_profile(self):
        UserProfile.objects.create(user=self.user, role='ADMIN')
        self.client.force_login(self.user)

        response = self.client.get(
            f"{reverse('members:member_profile')}?id={self.member.id}&staff_view=1"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kofi Annan')

    def test_profile_links_a_single_email_matched_member_to_the_account(self):
        email_user = User.objects.create_user(
            username='email-member',
            email='member@example.com',
            password='test-password',
        )
        email_member = Member.objects.create(
            first_name='Esi',
            last_name='Asante',
            gender='F',
            email='member@example.com',
        )

        self.client.force_login(email_user)
        response = self.client.get(reverse('members:member_profile'))

        email_member.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Esi Asante')
        self.assertEqual(email_member.user, email_user)

    def test_regularisation_approval_updates_member_and_records_decision(self):
        UserProfile.objects.create(user=self.user, role='ADMIN')
        pending_member = Member.objects.create(
            first_name='Emmanuel',
            last_name='Osei Tutu',
            gender='M',
            status='PENDING',
        )
        self.client.force_login(self.user)
        page_response = self.client.get(
            f"{reverse('members:member_regularisation')}?id={pending_member.id}"
        )
        self.assertEqual(page_response.status_code, 200)
        self.assertContains(page_response, 'Leaders’ meeting decision')
        self.assertContains(page_response, 'Emmanuel Osei Tutu')

        response = self.client.post(
            f"{reverse('members:member_regularisation')}?id={pending_member.id}",
            {
                'member_id': pending_member.id,
                'meeting_reference': 'LDM/2026/08/45',
                'approval_date': '2026-08-19',
                'decision': 'APPROVED',
                'assigned_class': self.class_group.id,
                'remarks': 'Approved by the leaders’ meeting.',
            },
        )

        self.assertRedirects(response, reverse('members:member_directory'))
        pending_member.refresh_from_db()
        regularisation = MemberRegularisation.objects.get(member=pending_member)
        self.assertEqual(pending_member.status, 'REGULARIZED')
        self.assertEqual(pending_member.assigned_class, self.class_group)
        self.assertEqual(regularisation.decision, 'APPROVED')
        self.assertEqual(regularisation.processed_by, self.user)