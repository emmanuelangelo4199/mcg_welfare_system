"""Normalise legacy free-text expense categories onto the shared keys.

0002 (auto-generated) added the `choices` to Budget.category and
ExpenseLedger.category, but choices are validation-only: rows written before
that migration still hold free text such as "Utilities" or "Welfare Support".
Until they are converted, budget utilisation keeps missing the spend it is
supposed to match, which is the bug the shared vocabulary was meant to fix.

This runs as a separate migration rather than being folded into 0002 because
0002 has already been applied.
"""

from django.db import migrations

CHOICES = [
    ('UTILITIES', 'Utility Bills (Water/Electricity)'),
    ('WELFARE', 'Member Welfare Support'),
    ('MAINTENANCE', 'Sanctuary Maintenance'),
    ('REPAIRS', 'Repairs & Equipment'),
    ('TRANSPORT', 'Transport & Fuel'),
    ('EVANGELISM', 'Evangelism & Mission'),
    ('ADMIN', 'Administrative Supplies'),
    ('STATUTORY', 'Statutory / Connexional Payments'),
    ('OTHER', 'Other Expenditure'),
]

# Legacy free-text values (lower-cased) mapped onto the new keys.
LEGACY_MAP = {
    'utilities': 'UTILITIES',
    'utility': 'UTILITIES',
    'utility bills': 'UTILITIES',
    'utility bills (water/electricity)': 'UTILITIES',
    'electricity': 'UTILITIES',
    'water': 'UTILITIES',
    'welfare': 'WELFARE',
    'welfare support': 'WELFARE',
    'member welfare support': 'WELFARE',
    'maintenance': 'MAINTENANCE',
    'sanctuary maintenance': 'MAINTENANCE',
    'building maintenance': 'MAINTENANCE',
    'repairs': 'REPAIRS',
    'repairs & equipment': 'REPAIRS',
    'equipment': 'REPAIRS',
    'transport': 'TRANSPORT',
    'transport & fuel': 'TRANSPORT',
    'fuel': 'TRANSPORT',
    'evangelism': 'EVANGELISM',
    'evangelism & mission': 'EVANGELISM',
    'mission': 'EVANGELISM',
    'missions': 'EVANGELISM',
    'admin': 'ADMIN',
    'administration': 'ADMIN',
    'administrative supplies': 'ADMIN',
    'statutory': 'STATUTORY',
    'connexional': 'STATUTORY',
    'statutory / connexional payments': 'STATUTORY',
    'other': 'OTHER',
    'other expenditure': 'OTHER',
}

VALID_KEYS = {key for key, _ in CHOICES}


def normalise(apps, schema_editor):
    """Map free text onto the shared keys, keeping anything unrecognised in a
    note rather than silently discarding it. Safe to re-run."""
    Expense = apps.get_model('finance', 'ExpenseLedger')
    Budget = apps.get_model('finance', 'Budget')

    for expense in Expense.objects.all():
        raw = (expense.category or '').strip()
        if raw in VALID_KEYS:
            continue
        key = LEGACY_MAP.get(raw.lower(), 'OTHER')
        if key == 'OTHER' and raw:
            note = f"[Imported category: {raw}]"
            expense.description = f"{expense.description}\n{note}" if expense.description else note
        expense.category = key
        expense.save(update_fields=['category', 'description'])

    for budget in Budget.objects.all():
        raw = (budget.category or '').strip()
        if raw in VALID_KEYS:
            continue
        key = LEGACY_MAP.get(raw.lower(), 'OTHER')
        if key == 'OTHER' and raw:
            note = f"[Imported category: {raw}]"
            budget.notes = f"{budget.notes}\n{note}" if budget.notes else note
        budget.category = key
        budget.save(update_fields=['category', 'notes'])


def restore(apps, schema_editor):
    """Reverse: put the human-readable label back as free text."""
    labels = dict(CHOICES)
    for model_name in ('ExpenseLedger', 'Budget'):
        model = apps.get_model('finance', model_name)
        for row in model.objects.all():
            row.category = labels.get(row.category, row.category)
            row.save(update_fields=['category'])


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0002_alter_budget_category_alter_expenseledger_category'),
    ]

    operations = [
        migrations.RunPython(normalise, restore),
    ]
