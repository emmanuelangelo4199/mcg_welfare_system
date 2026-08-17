from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse, NoReverseMatch
from accounts.models import UserProfile

User = get_user_model()


class MeetingsRouteTest(TestCase):
    """Regression tests for meetings routes — ensures no NoReverseMatch or HTTP 500."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='meetinguser',
            email='meetinguser@example.com',
            password='Password123!',
        )
        UserProfile.objects.create(user=self.user, role='ADMIN', phone_number='0241234567')
        self.client.login(username='meetinguser', password='Password123!')

    # ------------------------------------------------------------------ routes

    def test_action_item_tracker_url_resolves(self):
        """The URL name 'meetings:action_item_tracker' must resolve without error."""
        try:
            url = reverse('meetings:action_item_tracker')
        except NoReverseMatch as exc:
            self.fail(f"NoReverseMatch for 'meetings:action_item_tracker': {exc}")
        self.assertEqual(url, '/meetings/action-items/')

    def test_action_item_tracker_get_returns_200(self):
        """Authenticated GET /meetings/action-items/ must not return 500."""
        url = reverse('meetings:action_item_tracker')
        response = self.client.get(url)
        self.assertEqual(
            response.status_code, 200,
            f"Expected 200 but got {response.status_code} for {url}",
        )

    def test_meeting_list_get_returns_200(self):
        url = reverse('meetings:meeting_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_meeting_schedule_get_returns_200(self):
        url = reverse('meetings:meeting_schedule')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_action_item_post_redirect_uses_correct_name(self):
        """POST to action_item_tracker must redirect back to the same page (no NoReverseMatch)."""
        url = reverse('meetings:action_item_tracker')
        response = self.client.post(url, {'action': 'create'})
        # Without required fields the view skips creation but still redirects
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertIn('/meetings/action-items/', response['Location'])
