from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from core.decorators import role_required
from .models import SystemSetting, AuditLog

# Each settings panel maps to a list of (key, label, kind) stored in the
# SystemSetting key/value store. Kinds drive validation and rendering.
SETTINGS_SECTIONS = {
    'society_profile': {
        'title': 'Society profile',
        'tab_id': 'society-profile',
        'fields': [
            ('SOCIETY_NAME', 'Society name', 'text'),
            ('SOCIETY_DESCRIPTION', 'Circuit and diocese description', 'text'),
            ('SOCIETY_ADDRESS', 'Society postal address', 'text'),
            ('SOCIETY_EMAIL', 'Society email address', 'email'),
            ('SOCIETY_PHONE', 'Society phone number', 'text'),
        ],
    },
    'financial': {
        'title': 'Financial configuration',
        'tab_id': 'financial-config',
        'fields': [
            ('TREASURER_APPROVAL_LIMIT', 'Treasurer approval limit (GHS)', 'amount'),
            ('FINANCE_COMMITTEE_THRESHOLD', 'Finance committee threshold (GHS)', 'amount'),
            ('DIOCESE_ASSESSMENT_RATE', 'Diocese assessment levy (percent)', 'percent'),
            ('CONNEXION_QUOTA_RATE', 'Connexion quota levy (percent)', 'percent'),
            ('CIRCUIT_SUPPORT_RATE', 'Circuit support levy (percent)', 'percent'),
        ],
    },
    'notifications': {
        'title': 'Communication gateways',
        'tab_id': 'notification-config',
        'fields': [
            ('SMS_API_KEY', 'SMS gateway API key', 'text'),
            ('SMTP_ENDPOINT', 'SMTP email endpoint', 'text'),
        ],
    },
    'backup': {
        'title': 'Data backup',
        'tab_id': 'data-backup',
        'fields': [
            ('BACKUP_FREQUENCY', 'Backup frequency', 'choice'),
        ],
    },
    'security': {
        'title': 'Session and security',
        'tab_id': 'session-security',
        'fields': [
            ('SESSION_TIMEOUT_MINUTES', 'Session timeout (minutes)', 'integer'),
            ('PASSWORD_EXPIRY_DAYS', 'Password expiry (days)', 'integer'),
            ('MFA_REQUIRED', 'Require multi-factor authentication', 'boolean'),
            ('HIGH_RISK_CONFIRMATION', 'Require master password for high-risk actions', 'boolean'),
        ],
    },
}

SETTING_DEFAULTS = {
    'SOCIETY_NAME': '',
    'SOCIETY_DESCRIPTION': '',
    'SOCIETY_ADDRESS': '',
    'SOCIETY_EMAIL': '',
    'SOCIETY_PHONE': '',
    'TREASURER_APPROVAL_LIMIT': '5000.00',
    'FINANCE_COMMITTEE_THRESHOLD': '15000.00',
    'DIOCESE_ASSESSMENT_RATE': '30',
    'CONNEXION_QUOTA_RATE': '15',
    'CIRCUIT_SUPPORT_RATE': '5',
    'SMS_API_KEY': '',
    'SMTP_ENDPOINT': '',
    'BACKUP_FREQUENCY': '24',
    'SESSION_TIMEOUT_MINUTES': '30',
    'PASSWORD_EXPIRY_DAYS': '90',
    'MFA_REQUIRED': 'TRUE',
    'HIGH_RISK_CONFIRMATION': 'TRUE',
}

BACKUP_FREQUENCY_CHOICES = [
    ('24', 'Every 24 hours'),
    ('12', 'Every 12 hours'),
    ('168', 'Weekly'),
]


def _section_for_tab(tab_id):
    for section in SETTINGS_SECTIONS.values():
        if section['tab_id'] == tab_id:
            return section
    return None


@role_required(allowed_roles=['ADMIN'])
def system_settings_view(request):
    if request.method == 'POST':
        section = SETTINGS_SECTIONS.get(request.POST.get('section', ''))
        if section is None:
            messages.error(request, 'Unknown settings section.')
            return redirect('core:system_settings')

        values, errors = {}, {}
        for key, label, kind in section['fields']:
            raw = request.POST.get(key, '').strip()
            if kind == 'boolean':
                values[key] = 'TRUE' if request.POST.get(key) else 'FALSE'
            elif kind == 'email':
                if raw:
                    try:
                        validate_email(raw)
                        values[key] = raw
                    except ValidationError:
                        errors[key] = 'Enter a valid email address.'
                else:
                    values[key] = ''
            elif kind in ('amount', 'percent', 'integer'):
                normalised = raw.replace(',', '')
                try:
                    number = float(normalised) if kind != 'integer' else int(normalised)
                    if number < 0:
                        raise ValueError
                    if kind == 'percent' and number > 100:
                        errors[key] = 'Enter a percentage between 0 and 100.'
                        continue
                    values[key] = normalised
                except ValueError:
                    errors[key] = 'Enter a valid number.'
            else:
                values[key] = raw

        if errors:
            messages.error(request, 'Some settings could not be saved. Review the highlighted fields.')
            context = _settings_context(submitted={**SETTING_DEFAULTS, **values}, errors=errors, active_tab=section['tab_id'])
            return render(request, "core/system_setting.html", context)

        changed = []
        for key, label, kind in section['fields']:
            new_value = values[key]
            existing = SystemSetting.objects.filter(key=key).first()
            if existing is None or existing.value != new_value:
                changed.append(key)
            SystemSetting.objects.update_or_create(
                key=key,
                defaults={'value': new_value, 'description': label},
            )

        if changed:
            AuditLog.objects.create(
                user=request.user,
                action=f"Updated system settings: {section['title']}",
                model_name='SystemSetting',
                object_id=section['tab_id'],
                details=f'Changed keys: {", ".join(sorted(changed))}',
            )
            messages.success(request, f"{section['title'].capitalize()} settings saved.")
        else:
            messages.info(request, f"No changes were made to the {section['title'].lower()} settings.")
        return redirect(f"{reverse('core:system_settings')}?tab={section['tab_id']}")

    requested_tab = request.GET.get('tab', 'society-profile')
    section = _section_for_tab(requested_tab)
    return render(request, "core/system_setting.html", _settings_context(active_tab=section['tab_id'] if section else 'society-profile'))


def _settings_context(submitted=None, errors=None, active_tab='society-profile'):
    stored = {s.key: s.value for s in SystemSetting.objects.all()}
    values = submitted if submitted is not None else {**SETTING_DEFAULTS, **stored}
    return {
        "active_nav": "core",
        "settings_values": values,
        "errors": errors or {},
        "active_tab": active_tab,
        "backup_frequency_choices": BACKUP_FREQUENCY_CHOICES,
    }


@role_required(allowed_roles=['ADMIN'])
def audit_log_view(request):
    logs = AuditLog.objects.select_related('user').all()[:100]

    context = {
        "active_nav": "core",
        "logs": logs
    }
    return render(request, "core/audit_log.html", context)
