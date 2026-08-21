from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from classes.models import ClassGroup
from members.models import Member, MemberRegularisation, MembershipStatusChange, MemberTransfer
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
    def test_profile_history_lists_membership_status_changes(self):
        MembershipStatusChange.objects.create(
            member=self.member,
            previous_status='ACTIVE',
            new_status='TRANSFERRED',
            effective_date='2026-08-01',
            reason='Transferred to Wesley Cathedral society.',
            authorised_by='MINISTER',
            note_reference='LDM/2026/08/45',
            recorded_by=self.admin,
        )
        self.client.force_login(self.admin)

        response = self.client.get(f"{reverse('members:member_profile')}?id={self.member.id}")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Membership status changes')
        self.assertContains(response, 'Active Full Member')
        self.assertContains(response, 'Transferred')
        self.assertContains(response, 'Rev. Superintendent Minister')
        self.assertContains(response, 'LDM/2026/08/45')


class MemberTransferTestCase(MembersTestCase):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_superuser(username='admin', password='admin-password')

    def test_transfer_page_requires_authentication(self):
        response = self.client.get(reverse('members:member_transfer'))
        self.assertRedirects(response, reverse('accounts:login'))

    def test_transfer_page_blocked_for_non_admin_users(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('members:member_transfer'))
        self.assertRedirects(response, reverse('dashboard:dashboard'))

    def test_transfer_page_renders_classes_and_empty_history(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('members:member_transfer'))
        self.assertContains(response, 'Ebenezer Class')
        self.assertContains(response, 'No transfers have been recorded yet.')

    def test_transfer_out_marks_member_and_records_history(self):
        from core.models import AuditLog

        self.client.force_login(self.admin)
        response = self.client.post(reverse('members:member_transfer'), {
            'direction': 'OUT',
            'member': self.member.id,
            'destination_society': 'Wesley Society',
            'destination_circuit': 'Accra North Circuit',
            'reason': 'RELOCATION',
            'effective_date': '2026-08-19',
        })

        self.assertRedirects(response, f"{reverse('members:member_transfer')}?member={self.member.id}")
        self.member.refresh_from_db()
        self.assertEqual(self.member.status, 'TRANSFERRED')

        transfer = MemberTransfer.objects.get(member=self.member)
        self.assertEqual(transfer.direction, 'OUT')
        self.assertEqual(transfer.destination_society, 'Wesley Society')
        self.assertEqual(transfer.circuit, 'Accra North Circuit')
        self.assertEqual(transfer.reason, 'RELOCATION')
        self.assertEqual(transfer.recorded_by, self.admin)
        self.assertTrue(
            AuditLog.objects.filter(user=self.admin, model_name='Member', object_id=str(self.member.id)).exists()
        )

        page = self.client.get(reverse('members:member_transfer'))
        self.assertContains(page, 'Kofi Annan')
        self.assertContains(page, 'Wesley Society (Accra North Circuit)')

    def test_transfer_out_rejects_already_transferred_member(self):
        self.member.status = 'TRANSFERRED'
        self.member.save()
        self.client.force_login(self.admin)

        response = self.client.post(reverse('members:member_transfer'), {
            'direction': 'OUT',
            'member': self.member.id,
            'destination_society': 'Wesley Society',
            'reason': 'RELOCATION',
            'effective_date': '2026-08-19',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already been transferred out')
        self.assertEqual(MemberTransfer.objects.count(), 0)

    def test_transfer_out_validates_required_fields(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('members:member_transfer'), {
            'direction': 'OUT',
            'member': self.member.id,
            'destination_society': '',
            'reason': '',
            'effective_date': 'not-a-date',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enter the destination society.')
        self.assertContains(response, 'Select the reason for the transfer.')
        self.assertContains(response, 'Enter a valid effective date.')
        self.member.refresh_from_db()
        self.assertEqual(self.member.status, 'ACTIVE')

    def test_transfer_in_creates_member_and_records_history(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('members:member_transfer'), {
            'direction': 'IN',
            'full_name': 'Akosua Sarpong',
            'gender': 'F',
            'previous_society': 'St. Paul&#39;s, Tema',
            'letter_reference': 'TR-2026-045',
            'membership_type': 'FULL',
            'assigned_class': self.class_group.id,
            'effective_date': '2026-08-19',
        })

        new_member = Member.objects.get(first_name='Akosua', last_name='Sarpong')
        self.assertRedirects(response, f"{reverse('members:member_transfer')}?member={new_member.id}")
        self.assertEqual(new_member.status, 'ACTIVE')
        self.assertEqual(new_member.assigned_class, self.class_group)

        transfer = MemberTransfer.objects.get(member=new_member)
        self.assertEqual(transfer.direction, 'IN')
        self.assertEqual(transfer.letter_reference, 'TR-2026-045')
        self.assertEqual(transfer.previous_society, 'St. Paul&#39;s, Tema')

    def test_transfer_in_validates_required_fields(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('members:member_transfer'), {
            'direction': 'IN',
            'full_name': 'SoloName',
            'gender': '',
            'previous_society': '',
            'letter_reference': '',
            'membership_type': 'FULL',
            'effective_date': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'first and last name')
        self.assertContains(response, 'Select the member’s gender.')
        self.assertContains(response, 'Enter the previous society.')
        self.assertContains(response, 'Enter the transfer letter reference.')
        self.assertContains(response, 'Enter a valid effective date.')
        self.assertFalse(Member.objects.filter(first_name='SoloName').exists())

    def test_history_search_filters_by_name(self):
        MemberTransfer.objects.create(
            direction='OUT', member=self.member, member_name='Kofi Annan',
            destination_society='Wesley Society', effective_date='2026-08-01',
            recorded_by=self.admin,
        )
        MemberTransfer.objects.create(
            direction='IN', member_name='Grace Ofori',
            previous_society='Calvary Chapel', effective_date='2026-08-02',
            recorded_by=self.admin,
        )
        self.client.force_login(self.admin)

        response = self.client.get(reverse('members:member_transfer'), {'history_q': 'grace'})

        self.assertContains(response, 'Grace Ofori')
        self.assertNotContains(response, 'Kofi Annan')


class PendingMembersTestCase(MembersTestCase):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_superuser(username='admin', password='admin-password')
        self.pending_member = Member.objects.create(
            first_name='Kwame',
            last_name='Mensah',
            gender='M',
            assigned_class=self.class_group,
            status='PENDING',
        )

    def test_pending_page_requires_authentication(self):
        response = self.client.get(reverse('members:pending_members'))
        self.assertRedirects(response, reverse('accounts:login'))

    def test_pending_page_blocked_for_users_without_a_role(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('members:pending_members'))
        self.assertRedirects(response, reverse('dashboard:dashboard'))

    def test_pending_page_renders_members_with_review_links(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('members:pending_members'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kwame Mensah')
        self.assertContains(response, 'Ebenezer Class')
        self.assertContains(response, 'Showing 1 pending record')
        self.assertContains(response, f'/members/regularisation/?id={self.pending_member.id}')

    def test_pending_page_highlights_submissions_older_than_sixty_days(self):
        from django.utils import timezone as tz
        from datetime import timedelta

        Member.objects.filter(id=self.pending_member.id).update(
            created_at=tz.now() - timedelta(days=82)
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse('members:pending_members'))

        self.assertContains(response, 'bg-[#FEF9C3]')
        self.assertContains(response, 'text-warning')

    def test_pending_page_shows_empty_state_when_nothing_is_pending(self):
        self.pending_member.delete()
        self.client.force_login(self.admin)
        response = self.client.get(reverse('members:pending_members'))

        self.assertContains(response, 'All members are regularised. Great work!')
        self.assertNotContains(response, 'Showing 1 pending record')

    def test_class_leader_role_can_access_pending_page(self):
        from accounts.models import UserProfile
        UserProfile.objects.create(user=self.user, role='CLASS_LEADER')
        self.client.force_login(self.user)
        response = self.client.get(reverse('members:pending_members'))
        self.assertEqual(response.status_code, 200)


class PrivilegedProfileAccessTestCase(MembersTestCase):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_superuser(username='admin', password='admin-password')

    def test_admin_with_linked_record_can_open_any_member_profile(self):
        # An admin account linked to a member record (e.g. by the email
        # auto-link) must still be able to review other members explicitly.
        self.member.user = self.admin
        self.member.save()
        other_member = Member.objects.create(
            first_name='Abena', last_name='Owusu', gender='F', status='ACTIVE'
        )

        self.client.force_login(self.admin)
        response = self.client.get(f"{reverse('members:member_profile')}?id={other_member.id}")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Abena Owusu')
        self.assertNotContains(response, 'Kofi Annan')

    def test_admin_defaults_to_own_linked_record_without_an_explicit_id(self):
        self.member.user = self.admin
        self.member.save()

        self.client.force_login(self.admin)
        response = self.client.get(reverse('members:member_profile'))

        self.assertContains(response, 'Kofi Annan')

    def test_regular_member_with_linked_record_still_cannot_browse_others(self):
        self.member.user = self.user
        self.member.save()
        other_member = Member.objects.create(
            first_name='Abena', last_name='Owusu', gender='F', status='ACTIVE'
        )

        self.client.force_login(self.user)
        response = self.client.get(f"{reverse('members:member_profile')}?id={other_member.id}")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kofi Annan')
        self.assertNotContains(response, 'Abena Owusu')


class EditMemberTestCase(MembersTestCase):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_superuser(username='admin', password='admin-password')

    def test_edit_page_requires_authentication(self):
        response = self.client.get(reverse('members:edit_member'))
        self.assertRedirects(response, reverse('accounts:login'))

    def test_edit_page_blocked_for_users_without_a_role(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('members:edit_member'), {'id': self.member.id})
        self.assertRedirects(response, reverse('dashboard:dashboard'))

    def test_edit_page_without_a_member_redirects_to_directory(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('members:edit_member'))
        self.assertRedirects(response, reverse('members:member_directory'))

    def test_edit_page_renders_member_values_and_class_options(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('members:edit_member'), {'id': self.member.id})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Kofi"')
        self.assertContains(response, 'value="Annan"')
        self.assertContains(response, 'Ebenezer Class')
        self.assertContains(response, 'name="gender"')
        self.assertContains(response, 'name="assigned_class"')
        self.assertContains(response, 'name="membership_type"')
        self.assertContains(response, 'name="residential_address"')

    def test_edit_updates_all_fields_and_writes_audit_log(self):
        from core.models import AuditLog

        other_class = ClassGroup.objects.create(name='John Wesley Class')
        self.client.force_login(self.admin)
        response = self.client.post(f"{reverse('members:edit_member')}?id={self.member.id}", {
            'first_name': 'Kwame',
            'last_name': 'Annan',
            'gender': 'M',
            'date_of_birth': '1980-06-15',
            'date_of_baptism': '1995-03-12',
            'membership_type': 'ADHERENT',
            'assigned_class': other_class.id,
            'phone_number': '0209998877',
            'email': 'kofi.annan@example.com',
            'residential_address': '12 Wesley Road, Kumasi',
        })

        self.assertRedirects(response, f"{reverse('members:member_profile')}?id={self.member.id}")
        self.member.refresh_from_db()
        self.assertEqual(self.member.first_name, 'Kwame')
        self.assertEqual(self.member.date_of_birth.isoformat(), '1980-06-15')
        self.assertEqual(self.member.date_of_baptism.isoformat(), '1995-03-12')
        self.assertEqual(self.member.membership_type, 'ADHERENT')
        self.assertEqual(self.member.assigned_class, other_class)
        self.assertEqual(self.member.residential_address, '12 Wesley Road, Kumasi')
        self.assertTrue(
            AuditLog.objects.filter(
                user=self.admin,
                model_name='Member',
                object_id=str(self.member.id),
                details__contains='first_name',
            ).exists()
        )

    def test_edit_validates_fields_and_preserves_input(self):
        self.client.force_login(self.admin)
        response = self.client.post(f"{reverse('members:edit_member')}?id={self.member.id}", {
            'first_name': '',
            'last_name': '',
            'gender': 'X',
            'date_of_birth': 'not-a-date',
            'membership_type': 'NOT_A_TYPE',
            'assigned_class': '99999',
            'email': 'not-an-email',
            'phone_number': '',
            'residential_address': '',
            'date_of_baptism': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enter the member’s first name.')
        self.assertContains(response, 'Enter the member’s last name.')
        self.assertContains(response, 'Select the member’s gender.')
        self.assertContains(response, 'valid date of birth')
        self.assertContains(response, 'valid membership type')
        self.assertContains(response, 'Select a valid class.')
        self.assertContains(response, 'valid email address')
        self.assertContains(response, 'value="not-an-email"')
        self.member.refresh_from_db()
        self.assertEqual(self.member.first_name, 'Kofi')

    def test_edit_without_changes_skips_audit_log(self):
        from core.models import AuditLog

        self.client.force_login(self.admin)
        self.client.post(f"{reverse('members:edit_member')}?id={self.member.id}", {
            'first_name': self.member.first_name,
            'last_name': self.member.last_name,
            'gender': self.member.gender,
            'date_of_birth': '',
            'date_of_baptism': '',
            'membership_type': self.member.membership_type,
            'assigned_class': self.member.assigned_class_id or '',
            'phone_number': self.member.phone_number or '',
            'email': self.member.email or '',
            'residential_address': self.member.residential_address or '',
        })

        self.assertFalse(
            AuditLog.objects.filter(model_name='Member', object_id=str(self.member.id)).exists()
        )