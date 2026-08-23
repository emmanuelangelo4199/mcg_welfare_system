from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from members.models import Member
from welfare_cases.models import WelfareCase, WelfareDisbursement, VisitationLog, WelfareCaseActivity
from accounts.models import UserProfile

User = get_user_model()


class WelfareCaseModelTestCase(TestCase):
    def setUp(self):
        self.member = Member.objects.create(
            first_name='Abena',
            last_name='Osei',
            gender='F',
            status='ACTIVE'
        )
        self.wcase = WelfareCase.objects.create(
            member=self.member,
            case_type='MEDICAL',
            title='Hospital Admission Support',
            description='Emergency medical bill assistance',
            requested_amount=1500.00
        )

    def test_welfare_case_creation(self):
        self.assertEqual(self.wcase.status, 'SUBMITTED')
        self.assertEqual(self.wcase.requested_amount, 1500.00)
        self.assertEqual(self.wcase.priority, 'MEDIUM')
        self.assertTrue(self.wcase.is_confidential)
        self.assertTrue(self.wcase.is_open)

    def test_disbursement_percentage(self):
        self.wcase.approved_amount = 750
        self.assertEqual(self.wcase.disbursement_percentage, 50.0)

        self.wcase.requested_amount = 0
        self.assertEqual(self.wcase.disbursement_percentage, 0)

    def test_can_transition_to(self):
        self.assertTrue(self.wcase.can_transition_to('UNDER_REVIEW'))
        self.assertTrue(self.wcase.can_transition_to('REJECTED'))
        self.assertFalse(self.wcase.can_transition_to('DISBURSED'))
        self.assertFalse(self.wcase.can_transition_to('CLOSED'))

        self.wcase.status = 'APPROVED'
        self.assertTrue(self.wcase.can_transition_to('DISBURSED'))
        self.assertFalse(self.wcase.can_transition_to('SUBMITTED'))

        self.wcase.status = 'CLOSED'
        self.assertFalse(self.wcase.can_transition_to('APPROVED'))
        self.assertFalse(self.wcase.is_open)

    def test_priority_and_confidential(self):
        self.wcase.priority = 'URGENT'
        self.wcase.is_confidential = False
        self.wcase.save()
        self.wcase.refresh_from_db()
        self.assertEqual(self.wcase.priority, 'URGENT')
        self.assertFalse(self.wcase.is_confidential)

    def test_disbursement(self):
        disbursement = WelfareDisbursement.objects.create(
            welfare_case=self.wcase,
            amount=1200.00,
            disbursement_date='2026-08-10',
            payment_method='MOBILE_MONEY'
        )
        self.wcase.status = 'DISBURSED'
        self.wcase.approved_amount = 1200.00
        self.wcase.save()

        self.assertEqual(self.wcase.status, 'DISBURSED')
        self.assertEqual(disbursement.amount, 1200.00)
        self.assertEqual(str(disbursement), f"Disbursement GHS 1200.0 for Case #{self.wcase.id}")


class VisitationLogModelTestCase(TestCase):
    def setUp(self):
        self.member = Member.objects.create(first_name='Kwame', last_name='Mensah', gender='M', status='ACTIVE')
        self.wcase = WelfareCase.objects.create(
            member=self.member,
            case_type='HARDSHIP',
            title='Financial Support',
            description='Need help',
            requested_amount=500
        )
        self.user = User.objects.create_user(username='officer', password='pass')

    def test_visitation_creation(self):
        visit = VisitationLog.objects.create(
            welfare_case=self.wcase,
            visit_date='2026-08-15',
            visitors='Rev. Mensah, Mrs. Osei',
            findings='Family in need, verified',
            recommendation='Approve GHS 400',
            created_by=self.user
        )
        self.assertEqual(str(visit), f"Visit on 2026-08-15 for Case #{self.wcase.id}")
        self.assertEqual(visit.welfare_case, self.wcase)
        self.assertEqual(visit.created_by, self.user)


class WelfareCaseActivityTestCase(TestCase):
    def setUp(self):
        self.member = Member.objects.create(first_name='Abena', last_name='Osei', gender='F', status='ACTIVE')
        self.wcase = WelfareCase.objects.create(
            member=self.member,
            case_type='MEDICAL',
            title='Test Case',
            description='Test',
            requested_amount=1000
        )
        self.user = User.objects.create_user(username='admin', password='pass')

    def test_activity_creation(self):
        activity = WelfareCaseActivity.objects.create(
            welfare_case=self.wcase,
            action='CREATED',
            description='Case created',
            performed_by=self.user
        )
        self.assertEqual(activity.welfare_case, self.wcase)
        self.assertEqual(activity.action, 'CREATED')
        self.assertIn('Case #', str(activity))


class WelfareCasesViewTestCase(TestCase):
    def setUp(self):
        self.member = Member.objects.create(first_name='Abena', last_name='Osei', gender='F', status='ACTIVE', phone_number='0241111111')
        self.member2 = Member.objects.create(first_name='Kwame', last_name='Mensah', gender='M', status='ACTIVE')

        self.admin_user = User.objects.create_user(username='admin', email='admin@test.com', password='Password123!')
        UserProfile.objects.create(user=self.admin_user, role='ADMIN')

        self.welfare_officer = User.objects.create_user(username='welfare', email='welfare@test.com', password='Password123!')
        UserProfile.objects.create(user=self.welfare_officer, role='WELFARE_OFFICER')

        self.wcase1 = WelfareCase.objects.create(
            member=self.member,
            case_type='MEDICAL',
            title='Hospital Bill',
            description='Emergency',
            requested_amount=1500,
            priority='HIGH',
            status='SUBMITTED',
            created_by=self.admin_user
        )
        self.wcase2 = WelfareCase.objects.create(
            member=self.member2,
            case_type='BEREAVEMENT',
            title='Funeral Support',
            description='Bereavement',
            requested_amount=2000,
            priority='URGENT',
            status='APPROVED',
            created_by=self.admin_user
        )

    def test_list_view_requires_login(self):
        response = self.client.get(reverse('welfare_cases:welfare_cases_list'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_list_view_renders(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('welfare_cases:welfare_cases_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welfare Cases Management')
        self.assertContains(response, 'Hospital Bill')

    def test_list_view_search(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('welfare_cases:welfare_cases_list') + '?q=Hospital')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hospital Bill')
        # Funeral Support appears in filter dropdown, so check member name instead
        self.assertNotContains(response, 'Kwame Mensah')
        # Also check filtered count
        self.assertContains(response, 'Filtered: 1 result')

    def test_list_view_filter_by_type(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('welfare_cases:welfare_cases_list') + '?case_type=MEDICAL')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hospital Bill')

    def test_list_view_filter_by_status(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('welfare_cases:welfare_cases_list') + '?status=APPROVED')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Funeral Support')

    def test_new_case_view_get(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('welfare_cases:new_welfare_case'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Open New Welfare Case')

    def test_new_case_creation(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse('welfare_cases:new_welfare_case'), {
            'member_id': self.member.id,
            'case_type': 'HARDSHIP',
            'title': 'School Fees Support',
            'description': 'Need help with school fees',
            'requested_amount': '800.00',
            'priority': 'MEDIUM',
            'is_confidential': 'on',
        })
        self.assertRedirects(response, reverse('welfare_cases:welfare_cases_list'))
        self.assertTrue(WelfareCase.objects.filter(title='School Fees Support').exists())
        new_case = WelfareCase.objects.get(title='School Fees Support')
        self.assertEqual(new_case.requested_amount, 800)
        self.assertTrue(new_case.is_confidential)
        # Check activity created
        self.assertTrue(WelfareCaseActivity.objects.filter(welfare_case=new_case, action='CREATED').exists())

    def test_new_case_invalid_amount(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse('welfare_cases:new_welfare_case'), {
            'member_id': self.member.id,
            'case_type': 'HARDSHIP',
            'title': 'Invalid Amount',
            'description': 'Test',
            'requested_amount': '-100',
        })
        self.assertRedirects(response, reverse('welfare_cases:new_welfare_case'))

    def test_details_view(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('welfare_cases:welfare_case_details') + f'?id={self.wcase1.id}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hospital Bill')
        self.assertContains(response, self.member.get_full_name())

    def test_details_view_status_change(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse('welfare_cases:welfare_case_details') + f'?id={self.wcase1.id}', {
            'action': 'change_status',
            'new_status': 'UNDER_REVIEW',
            'review_notes': 'Under review by committee',
        })
        self.assertRedirects(response, reverse('welfare_cases:welfare_case_details') + f'?id={self.wcase1.id}')
        self.wcase1.refresh_from_db()
        self.assertEqual(self.wcase1.status, 'UNDER_REVIEW')

    def test_visit_record_creation(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse('welfare_cases:visit_record_form'), {
            'case_id': self.wcase1.id,
            'visit_date': '2026-08-15',
            'visitors': 'Rev. Mensah, Mrs. Osei',
            'findings': 'Verified need, family in hardship',
            'recommendation': 'Approve GHS 1000',
        })
        self.assertRedirects(response, f'/welfare-cases/details/?id={self.wcase1.id}')
        self.assertTrue(VisitationLog.objects.filter(welfare_case=self.wcase1).exists())

    def test_payment_view_requires_role(self):
        member_user = User.objects.create_user(username='member', password='pass')
        UserProfile.objects.create(user=member_user, role='MEMBER')
        self.client.force_login(member_user)
        response = self.client.get(reverse('welfare_cases:welfare_payment'))
        self.assertRedirects(response, reverse('dashboard:dashboard'))

    def test_payment_disbursement(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse('welfare_cases:welfare_payment'), {
            'case_id': self.wcase2.id,
            'amount': '1800.00',
            'disbursement_date': '2026-08-20',
            'payment_method': 'MOBILE_MONEY',
            'reference_number': 'MOMO123456',
            'remarks': 'Disbursed via MTN MoMo',
        })
        self.assertRedirects(response, reverse('welfare_cases:welfare_cases_list'))
        self.wcase2.refresh_from_db()
        self.assertEqual(self.wcase2.status, 'DISBURSED')
        self.assertEqual(self.wcase2.approved_amount, 1800)
        self.assertTrue(WelfareDisbursement.objects.filter(welfare_case=self.wcase2).exists())
        disb = WelfareDisbursement.objects.get(welfare_case=self.wcase2)
        self.assertEqual(disb.reference_number, 'MOMO123456')

    def test_closure_view(self):
        self.client.force_login(self.welfare_officer)
        response = self.client.post(reverse('welfare_cases:welfare_closure'), {
            'case_id': self.wcase1.id,
            'closure_notes': 'Support provided, family stable now',
        })
        self.assertRedirects(response, reverse('welfare_cases:welfare_cases_list'))
        self.wcase1.refresh_from_db()
        self.assertEqual(self.wcase1.status, 'CLOSED')
        self.assertIsNotNone(self.wcase1.closed_at)

    def test_closure_requires_role(self):
        member_user = User.objects.create_user(username='member2', password='pass')
        UserProfile.objects.create(user=member_user, role='MEMBER')
        self.client.force_login(member_user)
        response = self.client.get(reverse('welfare_cases:welfare_closure'))
        self.assertRedirects(response, reverse('dashboard:dashboard'))