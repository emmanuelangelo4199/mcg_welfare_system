from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from communications.models import Announcement, OutgoingMessage, MessageTemplate, CommunicationLog
from communications.views import ensure_default_templates
from members.models import Member
from accounts.models import UserProfile

User = get_user_model()


class AnnouncementModelTestCase(TestCase):
    def test_announcement_creation(self):
        user = User.objects.create_user(username='admin', password='pass')
        ann = Announcement.objects.create(
            title='Sunday Service',
            content='Join us for Sunday service at 8am',
            category='EVENT',
            priority='HIGH',
            is_pinned=True,
            created_by=user
        )
        self.assertEqual(str(ann), 'Sunday Service')
        self.assertTrue(ann.is_pinned)
        self.assertEqual(ann.category, 'EVENT')
        self.assertFalse(ann.is_expired)

    def test_announcement_expiry(self):
        from django.utils import timezone
        import datetime
        past_date = timezone.now().date() - datetime.timedelta(days=1)
        ann = Announcement.objects.create(
            title='Expired',
            content='Old',
            expiry_date=past_date
        )
        self.assertTrue(ann.is_expired)


class OutgoingMessageModelTestCase(TestCase):
    def test_message_creation(self):
        msg = OutgoingMessage.objects.create(
            recipient_group='All Members',
            recipient_count=100,
            message_type='SMS',
            subject='Test',
            content='Hello members',
            status='SENT'
        )
        self.assertIn('All Members', str(msg))
        self.assertEqual(msg.recipient_count, 100)


class MessageTemplateTestCase(TestCase):
    def test_template_creation(self):
        tmpl = MessageTemplate.objects.create(
            code='TEST_TMPL',
            name='Test Template',
            template_type='GENERAL',
            content='Hello {{name}}'
        )
        self.assertEqual(str(tmpl), 'Test Template (General)')
        self.assertTrue(tmpl.is_active)

    def test_ensure_default_templates(self):
        MessageTemplate.objects.all().delete()
        ensure_default_templates()
        self.assertGreaterEqual(MessageTemplate.objects.count(), 3)
        self.assertTrue(MessageTemplate.objects.filter(code='BIRTHDAY_SMS').exists())

        # Idempotent
        ensure_default_templates()
        self.assertGreaterEqual(MessageTemplate.objects.count(), 3)


class CommunicationLogTestCase(TestCase):
    def test_log_creation(self):
        out_msg = OutgoingMessage.objects.create(
            recipient_group='Test Group',
            content='Test',
            message_type='SMS'
        )
        log = CommunicationLog.objects.create(
            outgoing_message=out_msg,
            recipient_name='Kwame Mensah',
            recipient_contact='0241111111',
            status='SENT'
        )
        self.assertEqual(log.recipient_name, 'Kwame Mensah')
        self.assertIn('Kwame Mensah', str(log))


class ComposeMessageViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='Password123!')
        UserProfile.objects.create(user=self.user, role='ADMIN')
        self.member = Member.objects.create(first_name='Abena', last_name='Osei', gender='F', status='ACTIVE', phone_number='0241111111')
        ensure_default_templates()

    def test_compose_requires_login(self):
        response = self.client.get(reverse('communications:compose_message'))
        self.assertEqual(response.status_code, 302)

    def test_compose_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('communications:compose_message'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Compose Message')

    def test_compose_send_sms(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('communications:compose_message'), {
            'action': 'send',
            'type': 'SMS',
            'recipient_group': 'All Members',
            'subject': '',
            'content': 'Hello members, meeting tomorrow',
            'recipient_count': '10',
        })
        self.assertRedirects(response, reverse('communications:message_history'))
        self.assertTrue(OutgoingMessage.objects.filter(content='Hello members, meeting tomorrow').exists())
        msg = OutgoingMessage.objects.get(content='Hello members, meeting tomorrow')
        self.assertEqual(msg.message_type, 'SMS')
        self.assertEqual(msg.recipient_count, 10)


class MessageHistoryViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='pass')
        UserProfile.objects.create(user=self.user, role='ADMIN')
        OutgoingMessage.objects.create(recipient_group='All Members', content='Test message 1', message_type='SMS', status='SENT')
        OutgoingMessage.objects.create(recipient_group='Choir', content='Choir practice', message_type='EMAIL', status='SENT', subject='Choir')

    def test_history_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('communications:message_history'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Message History')

    def test_history_search(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('communications:message_history') + '?q=Choir')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Choir')

    def test_history_filter_type(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('communications:message_history') + '?type=EMAIL')
        self.assertEqual(response.status_code, 200)


class AnnouncementBoardViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='Password123!')
        UserProfile.objects.create(user=self.user, role='ADMIN')
        self.ann = Announcement.objects.create(title='Test Announcement', content='Content here', category='GENERAL', created_by=self.user)

    def test_board_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('communications:announcement_board'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Announcement Board')
        self.assertContains(response, 'Test Announcement')

    def test_create_announcement(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('communications:announcement_board'), {
            'action': 'create',
            'title': 'New Event',
            'content': 'Event details',
            'category': 'EVENT',
            'priority': 'HIGH',
            'is_pinned': 'on',
        })
        self.assertRedirects(response, reverse('communications:announcement_board'))
        self.assertTrue(Announcement.objects.filter(title='New Event').exists())
        new_ann = Announcement.objects.get(title='New Event')
        self.assertTrue(new_ann.is_pinned)
        self.assertEqual(new_ann.category, 'EVENT')

    def test_toggle_active(self):
        self.client.force_login(self.user)
        self.assertTrue(self.ann.is_active)
        response = self.client.post(reverse('communications:announcement_board'), {
            'action': 'toggle_active',
            'announcement_id': self.ann.id,
        })
        self.assertRedirects(response, reverse('communications:announcement_board'))
        self.ann.refresh_from_db()
        self.assertFalse(self.ann.is_active)

    def test_delete_announcement(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('communications:announcement_board'), {
            'action': 'delete',
            'announcement_id': self.ann.id,
        })
        self.assertRedirects(response, reverse('communications:announcement_board'))
        self.assertFalse(Announcement.objects.filter(id=self.ann.id).exists())


class BirthdayMessagesViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='pass')
        UserProfile.objects.create(user=self.user, role='ADMIN')
        import datetime
        today = datetime.date.today()
        self.member = Member.objects.create(
            first_name='Abena',
            last_name='Osei',
            gender='F',
            status='ACTIVE',
            date_of_birth=datetime.date(1990, today.month, today.day),
            phone_number='0241111111'
        )
        ensure_default_templates()

    def test_birthday_view_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('communications:birthday_messages'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Birthday Messages')

    def test_send_birthday_sms(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('communications:birthday_messages'), {
            'member_id': self.member.id,
        })
        self.assertRedirects(response, reverse('communications:birthday_messages'))
        self.assertTrue(OutgoingMessage.objects.filter(recipient_group=self.member.get_full_name()).exists())


class ReminderDueNoticeViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='pass')
        UserProfile.objects.create(user=self.user, role='ADMIN')
        self.member = Member.objects.create(first_name='Kwame', last_name='Mensah', gender='M', status='PENDING', phone_number='0241111111')
        ensure_default_templates()

    def test_reminder_view_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('communications:reminder_due_notice'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welfare Dues Reminders')

    def test_broadcast_reminder(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('communications:reminder_due_notice'), {
            'action': 'broadcast',
            'group': 'Pending Dues',
            'message_text': 'Please pay your dues',
            'amount': '50',
            'month': 'August 2026',
        })
        self.assertRedirects(response, reverse('communications:reminder_due_notice'))
        self.assertTrue(OutgoingMessage.objects.filter(subject='Welfare Dues Reminder').exists())

    def test_broadcast_with_selected_members(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('communications:reminder_due_notice'), {
            'action': 'broadcast',
            'group': 'Selected',
            'message_text': 'Reminder for {{name}}',
            'selected_members': [self.member.id],
        })
        self.assertRedirects(response, reverse('communications:reminder_due_notice'))
        msg = OutgoingMessage.objects.filter(recipient_group='Selected').first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.recipient_count, 1)