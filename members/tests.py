from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from classes.models import ClassGroup
from members.models import Member, MembershipStatusChange
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



class StatusManagementTestCase(MembersTestCase):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_superuser(username='admin', password='admin-password')

    def test_status_page_requires_authentication(self):
        response = self.client.get(reverse('members:status_management'))
        self.assertRedirects(response, reverse('accounts:login'))

    def test_status_page_blocked_for_non_admin_users(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('members:status_management'))
        self.assertRedirects(response, reverse('dashboard:dashboard'))

    def test_search_finds_members_by_name_phone_and_id(self):
        self.client.force_login(self.admin)

        by_name = self.client.get(reverse('members:status_management'), {'q': 'kofi'})
        self.assertContains(by_name, 'Kofi Annan')

        by_phone = self.client.get(reverse('members:status_management'), {'q': '0209876543'})
        self.assertContains(by_phone, 'Kofi Annan')

        by_id = self.client.get(reverse('members:status_management'), {'q': str(self.member.id)})
        self.assertContains(by_id, 'Kofi Annan')

    def test_search_without_matches_shows_empty_state(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('members:status_management'), {'q': 'does-not-exist'})
        self.assertContains(response, 'No members matched')

    def test_selected_member_renders_context_and_form(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('members:status_management'), {'member': self.member.id})
        self.assertContains(response, 'Kofi Annan')
        self.assertContains(response, 'Active Full Member')
        self.assertContains(response, f'name="member" value="{self.member.id}"')

    def test_page_without_member_hides_form(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('members:status_management'))
        self.assertContains(response, 'No member selected')
        self.assertNotContains(response, 'name="new_status"')

    def test_status_update_changes_status_and_creates_records(self):
        from core.models import AuditLog

        self.client.force_login(self.admin)
        response = self.client.post(reverse('members:status_management'), {
            'member': self.member.id,
            'new_status': 'INACTIVE',
            'effective_date': '2026-08-01',
            'reason': 'Relocated abroad and no longer attending services.',
            'authorised_by': 'MINISTER',
            'note_reference': 'Minutes of Leaders Meeting (03/08/26)',
        })

        self.assertRedirects(response, f"{reverse('members:status_management')}?member={self.member.id}")
        self.member.refresh_from_db()
        self.assertEqual(self.member.status, 'INACTIVE')

        change = MembershipStatusChange.objects.get(member=self.member)
        self.assertEqual(change.previous_status, 'ACTIVE')
        self.assertEqual(change.new_status, 'INACTIVE')
        self.assertEqual(change.effective_date.isoformat(), '2026-08-01')
        self.assertEqual(change.authorised_by, 'MINISTER')
        self.assertEqual(change.recorded_by, self.admin)
        self.assertEqual(change.note_reference, 'Minutes of Leaders Meeting (03/08/26)')

        self.assertTrue(
            AuditLog.objects.filter(
                user=self.admin,
                model_name='Member',
                object_id=str(self.member.id),
            ).exists()
        )

    def test_status_update_rejects_unchanged_status(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('members:status_management'), {
            'member': self.member.id,
            'new_status': 'ACTIVE',
            'effective_date': '2026-08-01',
            'reason': 'Trying to set the same status again.',
            'authorised_by': 'STEWARD',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already marked as')
        self.assertFalse(MembershipStatusChange.objects.exists())

    def test_status_update_validates_required_fields(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('members:status_management'), {
            'member': self.member.id,
            'new_status': 'NOT_A_STATUS',
            'effective_date': 'not-a-date',
            'reason': 'short',
            'authorised_by': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select a valid new status.')
        self.assertContains(response, 'Enter a valid effective date.')
        self.assertContains(response, 'at least 10 characters')
        self.assertContains(response, 'Select the authorising officer.')
        self.member.refresh_from_db()
        self.assertEqual(self.member.status, 'ACTIVE')

    def test_status_update_requires_existing_member(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('members:status_management'), {
            'member': '99999',
            'new_status': 'INACTIVE',
            'effective_date': '2026-08-01',
            'reason': 'This should fail because the member does not exist.',
            'authorised_by': 'STEWARD',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select a member before updating their status.')

    def test_status_history_renders_for_selected_member(self):
        MembershipStatusChange.objects.create(
            member=self.member,
            previous_status='PENDING',
            new_status='ACTIVE',
            effective_date='2025-01-05',
            reason='Approved by leaders meeting after trial period.',
            authorised_by='LEADERS_MEETING',
            recorded_by=self.admin,
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse('members:status_management'), {'member': self.member.id})
        self.assertContains(response, 'Recent Status Changes')
        self.assertContains(response, 'Pending Approval &rarr; Active Full Member')
