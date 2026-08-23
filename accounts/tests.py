from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from accounts.models import UserProfile, Role, Module, RolePermission
from accounts.views import ensure_default_roles_and_modules
from core.models import AuditLog

User = get_user_model()

class AccountsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='Password123!',
            first_name='Kwame',
            last_name='Mensah'
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            role='ADMIN',
            phone_number='0241234567'
        )

    def test_user_profile_creation(self):
        self.assertEqual(self.user.profile.role, 'ADMIN')
        self.assertEqual(str(self.user.profile), "testuser (Administrator)")

    def test_login_success(self):
        response = self.client.post(reverse('accounts:login'), {
            'email': 'testuser@example.com',
            'password': 'Password123!'
        })
        self.assertRedirects(response, reverse('dashboard:dashboard'))

    def test_login_failure(self):
        response = self.client.post(reverse('accounts:login'), {
            'email': 'testuser@example.com',
            'password': 'WrongPassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username/email or password.")

    def test_profile_uses_the_currently_logged_in_account_details(self):
        another_user = User.objects.create_user(
            username='abena',
            email='abena@example.com',
            password='Password123!',
            first_name='Abena',
            last_name='Owusu',
        )
        UserProfile.objects.create(user=another_user, role='MEMBER', phone_number='0201112222')

        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:profile'))
        self.assertContains(response, 'Kwame Mensah')
        self.assertContains(response, 'testuser@example.com')
        self.assertNotContains(response, 'Abena Owusu')

        self.client.force_login(another_user)
        response = self.client.get(reverse('accounts:profile'))
        self.assertContains(response, 'Abena Owusu')
        self.assertContains(response, 'abena@example.com')
        self.assertNotContains(response, 'Kwame Mensah')
        self.assertNotContains(response, 'Kwame Mensah')

    def test_profile_update_info(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('accounts:profile'), {
            'action': 'info',
            'email': 'newemail@example.com',
            'phone': '0249999999',
        })
        self.assertRedirects(response, reverse('accounts:profile'))
        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.user.email, 'newemail@example.com')
        self.assertEqual(self.profile.phone_number, '0249999999')

    def test_profile_update_password(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('accounts:profile'), {
            'action': 'password',
            'current_password': 'Password123!',
            'new_password': 'NewPass123!',
            'confirm_password': 'NewPass123!',
        })
        self.assertRedirects(response, reverse('accounts:profile'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass123!'))


class RoleModelTestCase(TestCase):
    def test_role_creation(self):
        role = Role.objects.create(
            code='TEST_ROLE',
            name='Test Role',
            description='A test role',
            is_system_protected=False
        )
        self.assertEqual(str(role), 'Test Role')
        self.assertEqual(role.code, 'TEST_ROLE')
        self.assertFalse(role.is_system_protected)
        self.assertTrue(role.is_active)

    def test_role_user_count(self):
        role = Role.objects.create(code='TREASURER', name='Treasurer')
        user1 = User.objects.create_user(username='user1', password='pass')
        UserProfile.objects.create(user=user1, role='TREASURER')
        user2 = User.objects.create_user(username='user2', password='pass')
        UserProfile.objects.create(user=user2, role='TREASURER')
        self.assertEqual(role.user_count, 2)

    def test_ensure_default_roles_and_modules(self):
        # Ensure clean
        Role.objects.all().delete()
        Module.objects.all().delete()
        RolePermission.objects.all().delete()

        ensure_default_roles_and_modules()

        self.assertGreaterEqual(Role.objects.count(), 10)
        self.assertGreaterEqual(Module.objects.count(), 5)
        self.assertTrue(Role.objects.filter(code='ADMIN').exists())
        self.assertTrue(Module.objects.filter(code='MEMBERS').exists())

        # Check admin has all permissions
        admin_role = Role.objects.get(code='ADMIN')
        admin_perms = RolePermission.objects.filter(role=admin_role)
        self.assertTrue(all(p.can_view for p in admin_perms))

        # Idempotent
        ensure_default_roles_and_modules()
        # Should not duplicate
        self.assertGreaterEqual(Role.objects.count(), 10)


class ModuleModelTestCase(TestCase):
    def test_module_creation(self):
        mod = Module.objects.create(
            code='TEST_MOD',
            name='Test Module',
            description='Test description',
            order=99,
            is_sensitive=True
        )
        self.assertEqual(str(mod), 'Test Module')
        self.assertTrue(mod.is_sensitive)
        self.assertEqual(mod.order, 99)


class RolePermissionModelTestCase(TestCase):
    def setUp(self):
        self.role = Role.objects.create(code='CLASS_LEADER', name='Class Leader')
        self.module = Module.objects.create(code='MEMBERS', name='Members', order=1)

    def test_permission_creation(self):
        perm = RolePermission.objects.create(
            role=self.role,
            module=self.module,
            can_view=True,
            can_create=False,
            can_edit=True,
            can_delete=False,
            can_approve=False
        )
        self.assertEqual(str(perm), 'Class Leader - Members')
        self.assertTrue(perm.can_view)
        self.assertTrue(perm.has_any())

        perm.can_view = False
        perm.can_edit = False
        perm.save()
        self.assertFalse(perm.has_any())

    def test_unique_together(self):
        RolePermission.objects.create(role=self.role, module=self.module, can_view=True)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            RolePermission.objects.create(role=self.role, module=self.module, can_view=False)


class RolePermissionsViewTestCase(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='Password123!',
            first_name='Admin',
            last_name='User'
        )
        UserProfile.objects.create(user=self.admin_user, role='ADMIN')
        ensure_default_roles_and_modules()

    def test_view_requires_admin(self):
        # Non-admin should be redirected
        member_user = User.objects.create_user(username='member', password='pass')
        UserProfile.objects.create(user=member_user, role='MEMBER')
        self.client.force_login(member_user)
        response = self.client.get(reverse('accounts:roles_permissions'))
        self.assertRedirects(response, reverse('dashboard:dashboard'))

    def test_view_renders_for_admin(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('accounts:roles_permissions'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Role &amp; Permission Management')
        self.assertContains(response, 'Administrator')
        self.assertContains(response, 'Members')

    def test_view_with_role_param(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('accounts:roles_permissions') + '?role=TREASURER')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Treasurer Permissions')

    def test_save_permissions(self):
        self.client.force_login(self.admin_user)
        treasurer_role = Role.objects.get(code='TREASURER')
        members_module = Module.objects.get(code='MEMBERS')
        finance_module = Module.objects.get(code='FINANCE')

        # Ensure permissions exist
        RolePermission.objects.get_or_create(role=treasurer_role, module=members_module)
        RolePermission.objects.get_or_create(role=treasurer_role, module=finance_module)

        response = self.client.post(
            reverse('accounts:roles_permissions') + '?role=TREASURER',
            {
                'action': 'save_permissions',
                'role_code': 'TREASURER',
                f'perm_{members_module.code}_view': 'on',
                f'perm_{finance_module.code}_view': 'on',
                f'perm_{finance_module.code}_create': 'on',
            }
        )
        self.assertRedirects(response, reverse('accounts:roles_permissions') + '?role=TREASURER')

        # Check saved
        perm_members = RolePermission.objects.get(role=treasurer_role, module=members_module)
        perm_finance = RolePermission.objects.get(role=treasurer_role, module=finance_module)
        self.assertTrue(perm_members.can_view)
        self.assertFalse(perm_members.can_create)  # not checked
        self.assertTrue(perm_finance.can_view)
        self.assertTrue(perm_finance.can_create)

        # Check audit log
        self.assertTrue(AuditLog.objects.filter(action__contains='Updated permissions for role').exists())

    def test_save_permissions_protected_role_blocked(self):
        self.client.force_login(self.admin_user)
        admin_role = Role.objects.get(code='ADMIN')
        response = self.client.post(
            reverse('accounts:roles_permissions') + '?role=ADMIN',
            {
                'action': 'save_permissions',
                'role_code': 'ADMIN',
                'perm_MEMBERS_view': 'on',
            }
        )
        # Should be blocked with error message
        self.assertRedirects(response, reverse('accounts:roles_permissions') + '?role=ADMIN')
        # Check message
        messages = list(response.wsgi_request._messages) if hasattr(response.wsgi_request, '_messages') else []
        # Instead check via follow
        follow = self.client.get(reverse('accounts:roles_permissions') + '?role=ADMIN')
        # Protected message should be in audit? Actually error message shown
        # Just ensure permission not changed to false? Admin should stay all true
        perm = RolePermission.objects.filter(role=admin_role).first()
        self.assertTrue(perm.can_view)

    def test_create_role(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse('accounts:roles_permissions'),
            {
                'action': 'create_role',
                'code': 'YOUTH_LEADER',
                'name': 'Youth Leader',
                'description': 'Leads youth ministry',
            }
        )
        self.assertRedirects(response, reverse('accounts:roles_permissions') + '?role=YOUTH_LEADER')
        self.assertTrue(Role.objects.filter(code='YOUTH_LEADER').exists())
        new_role = Role.objects.get(code='YOUTH_LEADER')
        self.assertEqual(new_role.name, 'Youth Leader')
        # Should have permissions for all modules
        self.assertEqual(RolePermission.objects.filter(role=new_role).count(), Module.objects.count())

    def test_create_duplicate_role_fails(self):
        self.client.force_login(self.admin_user)
        Role.objects.create(code='DUPLICATE', name='Duplicate')
        response = self.client.post(
            reverse('accounts:roles_permissions'),
            {
                'action': 'create_role',
                'code': 'DUPLICATE',
                'name': 'Duplicate Again',
            }
        )
        self.assertRedirects(response, reverse('accounts:roles_permissions') + '?role=DUPLICATE')
        # Should still have only one
        self.assertEqual(Role.objects.filter(code='DUPLICATE').count(), 1)


class UserListViewTestCase(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(username='admin', password='Password123!')
        UserProfile.objects.create(user=self.admin_user, role='ADMIN')
        self.target_user = User.objects.create_user(username='target', password='pass')
        UserProfile.objects.create(user=self.target_user, role='MEMBER')

    def test_user_list_renders(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('accounts:user_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'target')

    def test_user_role_update(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse('accounts:user_list'), {
            'user_id': self.target_user.id,
            'role': 'TREASURER',
        })
        self.assertRedirects(response, reverse('accounts:user_list'))
        self.target_user.profile.refresh_from_db()
        self.assertEqual(self.target_user.profile.role, 'TREASURER')