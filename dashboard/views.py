from datetime import date, timedelta

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.utils import timezone
from core.decorators import role_required
from members.models import Member
from welfare_cases.models import WelfareCase
from finance.models import IncomeLedger, ExpenseLedger, Budget
from services.models import ChurchService
from classes.models import ClassGroup
from communications.models import Announcement
from attendance.models import ClassAttendanceRecord, ServiceAttendance
from notifications.models import SystemNotification


def _month_starts(today, count=6):
    """Return the first day of the last `count` months, oldest first."""
    starts = []
    year, month = today.year, today.month
    for _ in range(count):
        starts.append(date(year, month, 1))
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return list(reversed(starts))


def _next_month(day):
    return date(day.year + 1, 1, 1) if day.month == 12 else date(day.year, day.month + 1, 1)


def _monthly_finance_series(today, months=6):
    """Income vs approved expenses per month, with bar heights as percentages."""
    series = []
    for start in _month_starts(today, months):
        end = _next_month(start)
        income = IncomeLedger.objects.filter(date__gte=start, date__lt=end).aggregate(
            total=Sum('amount'))['total'] or 0
        expense = ExpenseLedger.objects.filter(
            status__in=['APPROVED', 'PAID'], date__gte=start, date__lt=end).aggregate(
            total=Sum('amount'))['total'] or 0
        series.append({'label': start.strftime('%b'), 'income': income, 'expense': expense})

    peak = max([max(row['income'], row['expense']) for row in series] or [0]) or 1
    for row in series:
        row['income_height'] = round(float(row['income']) / float(peak) * 100)
        row['expense_height'] = round(float(row['expense']) / float(peak) * 100)

    return series, peak


def _upcoming_birthdays(today, days=7):
    """Members whose birthday falls within the next `days` days (ignores year)."""
    window = [(today + timedelta(days=offset)) for offset in range(days)]
    keys = {(day.month, day.day): index for index, day in enumerate(window)}

    upcoming = []
    for member in Member.objects.select_related('assigned_class').exclude(date_of_birth__isnull=True):
        position = keys.get((member.date_of_birth.month, member.date_of_birth.day))
        if position is not None:
            member.birthday_on = window[position]
            member.is_today = position == 0
            upcoming.append((position, member))

    return [member for _, member in sorted(upcoming, key=lambda pair: pair[0])]


def _user_initials(user):
    first = (getattr(user, 'first_name', '') or '').strip()
    last = (getattr(user, 'last_name', '') or '').strip()
    if first and last:
        return f'{first[0]}{last[0]}'.upper()
    if first:
        return first[:2].upper()
    username = (getattr(user, 'username', '') or '?').strip()
    return username[:2].upper()


@login_required(login_url='accounts:login')
def main_dashboard(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)

    members = Member.objects.all()
    total_members_count = members.count()
    active_members_count = members.filter(status__in=['ACTIVE', 'REGULARIZED']).count()
    pending_members_count = members.filter(status='PENDING').count()
    new_members_count = members.filter(created_at__date__gte=month_start).count()

    total_income = IncomeLedger.objects.aggregate(total=Sum('amount'))['total'] or 0
    total_expense = ExpenseLedger.objects.filter(
        status__in=['APPROVED', 'PAID']).aggregate(total=Sum('amount'))['total'] or 0
    outstanding_expense = ExpenseLedger.objects.filter(
        status='PENDING').aggregate(total=Sum('amount'))['total'] or 0

    latest_attendance = ServiceAttendance.objects.select_related('service').order_by(
        '-service__service_date').first()

    class_rows = list(
        ClassGroup.objects.annotate(
            active_member_count=Count('members', filter=Q(members__status='ACTIVE'))
        ).order_by('-active_member_count')[:6]
    )
    largest_class = max([row.active_member_count for row in class_rows] or [0]) or 1
    for row in class_rows:
        row.share = round(row.active_member_count / largest_class * 100)

    finance_series, finance_peak = _monthly_finance_series(today)

    context = {
        "active_nav": "dashboard",
        "today": today,
        "total_members_count": total_members_count,
        "active_members_count": active_members_count,
        "pending_members_count": pending_members_count,
        "new_members_count": new_members_count,
        "active_welfare_cases_count": WelfareCase.objects.exclude(status__in=['CLOSED', 'REJECTED']).count(),
        "total_income": total_income,
        "total_expense": total_expense,
        "outstanding_expense": outstanding_expense,
        "latest_attendance": latest_attendance,
        "class_rows": class_rows,
        "finance_series": finance_series,
        "finance_peak": finance_peak,
        "recent_members": members.select_related('assigned_class').order_by('-created_at')[:5],
        "upcoming_services": ChurchService.objects.filter(service_date__gte=today).order_by('service_date', 'start_time')[:5],
        "birthdays": _upcoming_birthdays(today),
        "welfare_alerts": WelfareCase.objects.select_related('member').exclude(status__in=['CLOSED', 'REJECTED']).order_by('-created_at')[:4],
        "announcements": Announcement.objects.filter(is_active=True).order_by('-created_at')[:3],
        "user_initials": _user_initials(request.user),
        "unread_notification_count": SystemNotification.objects.filter(
            user=request.user, is_read=False).count(),
    }
    return render(request, "dashboard/m_dashboard.html", context)

@role_required(allowed_roles=['ADMIN', 'TREASURER'])
def treasurer_dashboard(request):
    today = timezone.localdate()

    # Month filter (?month=YYYY-MM), defaulting to the current month.
    month_start = today.replace(day=1)
    raw_month = request.GET.get('month', '')
    if raw_month:
        try:
            year, month = raw_month.split('-')
            month_start = date(int(year), int(month), 1)
        except (ValueError, TypeError):
            month_start = today.replace(day=1)
    month_end = _next_month(month_start)

    approved_states = ['APPROVED', 'PAID']

    # All-time position.
    total_income = IncomeLedger.objects.aggregate(total=Sum('amount'))['total'] or 0
    total_expense = ExpenseLedger.objects.filter(
        status__in=approved_states).aggregate(total=Sum('amount'))['total'] or 0
    net_balance = total_income - total_expense

    # Selected month.
    month_income_qs = IncomeLedger.objects.filter(date__gte=month_start, date__lt=month_end)
    month_expense_qs = ExpenseLedger.objects.filter(
        status__in=approved_states, date__gte=month_start, date__lt=month_end)
    month_income = month_income_qs.aggregate(total=Sum('amount'))['total'] or 0
    month_expense = month_expense_qs.aggregate(total=Sum('amount'))['total'] or 0

    pending_expenses = ExpenseLedger.objects.filter(
        status='PENDING').select_related('recorded_by').order_by('-date')
    pending_total = pending_expenses.aggregate(total=Sum('amount'))['total'] or 0

    # Income mix for the selected month, as donut segments.
    palette = ['#5c0219', '#775a00', '#A3283F', '#eec04f', '#7b1c2d', '#897172']
    labels = dict(IncomeLedger.CATEGORY_CHOICES)
    rows = month_income_qs.values('category').annotate(total=Sum('amount')).order_by('-total')

    income_sources = []
    cursor = 0.0
    stops = []
    for index, row in enumerate(rows):
        share = float(row['total']) / float(month_income) * 100 if month_income else 0
        colour = palette[index % len(palette)]
        stops.append(f"{colour} {cursor:.2f}% {cursor + share:.2f}%")
        cursor += share
        income_sources.append({
            'label': labels.get(row['category'], row['category']),
            'total': row['total'],
            'share': round(share),
            'colour': colour,
        })
    donut_gradient = f"conic-gradient({', '.join(stops)})" if stops else ''

    # Budget utilisation for the current fiscal year.
    budgets = []
    for budget in Budget.objects.filter(fiscal_year=month_start.year).order_by('category'):
        spent = ExpenseLedger.objects.filter(
            status__in=approved_states,
            category=budget.category,
            date__year=budget.fiscal_year,
        ).aggregate(total=Sum('amount'))['total'] or 0

        allocated = budget.allocated_amount or 0
        share = round(float(spent) / float(allocated) * 100) if allocated else 0
        budgets.append({
            'category': budget.get_category_display(),
            'allocated': allocated,
            'spent': spent,
            'share': min(share, 100),
            'raw_share': share,
            'state': 'over' if share > 100 else ('warning' if share >= 80 else 'ok'),
        })

    # Recent transactions: income and approved expenses merged, newest first.
    transactions = [
        {
            'date': row.date,
            'description': row.remarks or labels.get(row.category, row.category),
            'category': labels.get(row.category, row.category),
            'amount': row.amount,
            'is_income': True,
            'recorded_by': row.recorded_by,
        }
        for row in IncomeLedger.objects.select_related('recorded_by').order_by('-date')[:10]
    ] + [
        {
            'date': row.date,
            'description': row.title,
            'category': row.get_category_display(),
            'amount': row.amount,
            'is_income': False,
            'recorded_by': row.recorded_by,
        }
        for row in ExpenseLedger.objects.select_related('recorded_by').filter(
            status__in=approved_states).order_by('-date')[:10]
    ]
    transactions.sort(key=lambda row: row['date'], reverse=True)

    context = {
        "active_nav": "dashboard",
        "today": today,
        "month_start": month_start,
        "month_value": month_start.strftime('%Y-%m'),
        "total_income": total_income,
        "total_expense": total_expense,
        "net_balance": net_balance,
        "month_income": month_income,
        "month_expense": month_expense,
        "pending_expenses": pending_expenses,
        "pending_count": pending_expenses.count(),
        "pending_total": pending_total,
        "income_sources": income_sources,
        "donut_gradient": donut_gradient,
        "budgets": budgets,
        "transactions": transactions[:10],
        "transactions_total": IncomeLedger.objects.count() + ExpenseLedger.objects.filter(status__in=approved_states).count(),
    }
    return render(request, "dashboard/treasurer.html", context)

@role_required(allowed_roles=['ADMIN', 'CLASS_LEADER'])
def class_leader_dashboard(request):
    today = timezone.localdate()

    my_classes = ClassGroup.objects.filter(leader=request.user).order_by('name')
    profile = getattr(request.user, 'profile', None)
    is_admin = request.user.is_superuser or (profile and profile.role == 'ADMIN')
    if is_admin and not my_classes.exists():
        my_classes = ClassGroup.objects.order_by('name')

    selected_id = request.GET.get('class')
    active_class = my_classes.filter(id=selected_id).first() if selected_id else my_classes.first()

    members = []
    records = []
    if active_class:
        members = list(
            Member.objects.filter(assigned_class=active_class).order_by('first_name', 'last_name')
        )
        records = list(
            ClassAttendanceRecord.objects.filter(class_group=active_class)
            .prefetch_related('present_members').order_by('-date')[:52]
        )

    # Last time each member was marked present (records are newest first).
    last_seen = {}
    for record in records:
        for member in record.present_members.all():
            last_seen.setdefault(member.id, record.date)

    latest = records[0] if records else None
    present_ids = {member.id for member in latest.present_members.all()} if latest else set()

    for member in members:
        member.last_seen = last_seen.get(member.id)
        member.was_present = member.id in present_ids
        member.initials = f"{member.first_name[:1]}{member.last_name[:1]}".upper()

    class_size = len(members)
    present_count = len(present_ids)
    absentees = [member for member in members if not member.was_present] if latest else []
    attendance_rate = round(present_count / class_size * 100) if class_size and latest else 0

    # Attendance trend, oldest first, scaled against the busiest session.
    trend = [
        {'date': record.date, 'count': record.present_members.count()}
        for record in reversed(records[:12])
    ]
    trend_peak = max([row['count'] for row in trend] or [0]) or 1
    for row in trend:
        row['height'] = round(row['count'] / trend_peak * 100)

    birthdays = sorted(
        (member for member in members
         if member.date_of_birth and member.date_of_birth.month == today.month),
        key=lambda member: member.date_of_birth.day,
    )
    for member in birthdays:
        member.is_today = member.date_of_birth.day == today.day

    alerts = []
    if active_class:
        alerts = list(
            WelfareCase.objects.filter(member__assigned_class=active_class)
            .exclude(status__in=['CLOSED', 'REJECTED'])
            .select_related('member').order_by('created_at')
        )
        for case in alerts:
            case.days_open = (today - case.created_at.date()).days

    context = {
        "active_nav": "dashboard",
        "today": today,
        "my_classes": my_classes,
        "active_class": active_class,
        "members": members,
        "class_size": class_size,
        "latest_record": latest,
        "present_count": present_count,
        "absentees": absentees,
        "absent_count": len(absentees),
        "attendance_rate": attendance_rate,
        "trend": trend,
        "birthdays": birthdays,
        "welfare_alerts": alerts,
    }
    return render(request, "dashboard/class_leader.html", context)