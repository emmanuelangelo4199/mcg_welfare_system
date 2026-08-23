import csv
import datetime
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.core.paginator import Paginator
from django.utils import timezone
from core.models import AuditLog
from .models import GeneratedReportLog, ReportSchedule, ReportFavorite
from members.models import Member
from finance.models import IncomeLedger, ExpenseLedger
from welfare_cases.models import WelfareCase
from attendance.models import ServiceAttendance, ClassAttendanceRecord


def ensure_default_reports():
    """Seed some default report logs if empty"""
    if GeneratedReportLog.objects.count() == 0:
        defaults = [
            {"report_type": "MEMBERSHIP", "title": "Monthly Membership Summary", "description": "Active vs pending members overview"},
            {"report_type": "ATTENDANCE", "title": "Weekly Attendance Summary", "description": "Service and class attendance last week"},
            {"report_type": "FINANCIAL", "title": "Monthly Financial Statement", "description": "Income vs expenses for current month"},
            {"report_type": "WELFARE", "title": "Welfare Cases Overview", "description": "Open welfare cases and disbursements"},
            {"report_type": "ANNUAL", "title": "Annual Society Report 2024", "description": "Comprehensive annual report"},
        ]
        for data in defaults:
            GeneratedReportLog.objects.create(**data)


@login_required(login_url='accounts:login')
def reports_hub_view(request):
    ensure_default_reports()
    reports_qs = GeneratedReportLog.objects.select_related('generated_by').all()

    q = request.GET.get('q', '').strip()
    report_type = request.GET.get('type', '').strip()
    status_filter = request.GET.get('status', '').strip()

    if q:
        reports_qs = reports_qs.filter(
            models.Q(title__icontains=q) | models.Q(description__icontains=q)
        )

    if report_type:
        reports_qs = reports_qs.filter(report_type=report_type)

    if status_filter:
        reports_qs = reports_qs.filter(status=status_filter)

    # Stats
    total_reports = GeneratedReportLog.objects.count()
    pinned_reports = GeneratedReportLog.objects.filter(is_pinned=True).count()
    by_type = GeneratedReportLog.objects.values('report_type').annotate(count=models.Count('id'))
    recent_reports = reports_qs.order_by('-generated_at')[:5]

    # Favorites for current user
    favorites = ReportFavorite.objects.filter(user=request.user).select_related('report')[:5]

    # Schedules
    schedules = ReportSchedule.objects.filter(is_active=True).order_by('next_run')[:5]

    paginator = Paginator(reports_qs.order_by('-is_pinned', '-generated_at'), 12)
    page_number = request.GET.get('page')
    reports_page = paginator.get_page(page_number)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'toggle_pin':
            report_id = request.POST.get('report_id')
            report_obj = get_object_or_404(GeneratedReportLog, id=report_id)
            report_obj.is_pinned = not report_obj.is_pinned
            report_obj.save(update_fields=['is_pinned', 'updated_at'])
            messages.success(request, f"Report {'pinned' if report_obj.is_pinned else 'unpinned'}.")
            return redirect('reports:reports_hub')

        elif action == 'toggle_favorite':
            report_id = request.POST.get('report_id')
            report_obj = get_object_or_404(GeneratedReportLog, id=report_id)
            fav, created = ReportFavorite.objects.get_or_create(user=request.user, report=report_obj)
            if not created:
                fav.delete()
                messages.success(request, f"Removed '{report_obj.title}' from favorites.")
            else:
                messages.success(request, f"Added '{report_obj.title}' to favorites.")
            return redirect('reports:reports_hub')

        elif action == 'delete_report':
            report_id = request.POST.get('report_id')
            report_obj = get_object_or_404(GeneratedReportLog, id=report_id)
            title = report_obj.title
            report_obj.delete()
            AuditLog.objects.create(
                user=request.user,
                action=f"Deleted report {title}",
                model_name="GeneratedReportLog",
                object_id=str(report_id),
            )
            messages.success(request, f"Report '{title}' deleted.")
            return redirect('reports:reports_hub')

    context = {
        "active_nav": "reports",
        "reports": reports_page,
        "reports_page": reports_page,
        "paginator": paginator,
        "recent_reports": recent_reports,
        "favorites": favorites,
        "schedules": schedules,
        "q": q,
        "type_filter": report_type,
        "status_filter": status_filter,
        "total_reports": total_reports,
        "pinned_reports": pinned_reports,
        "by_type": by_type,
        "type_choices": GeneratedReportLog.REPORT_TYPE_CHOICES,
        "status_choices": GeneratedReportLog.STATUS_CHOICES,
        "filtered_count": reports_qs.count(),
    }
    return render(request, "reports/m1report_page.html", context)


@login_required(login_url='accounts:login')
def membership_report_view(request):
    members_qs = Member.objects.select_related('assigned_class').all()

    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    class_filter = request.GET.get('class', '').strip()
    gender_filter = request.GET.get('gender', '').strip()

    if q:
        members_qs = members_qs.filter(
            models.Q(first_name__icontains=q)
            | models.Q(last_name__icontains=q)
            | models.Q(phone_number__icontains=q)
            | models.Q(email__icontains=q)
        )

    if status_filter:
        members_qs = members_qs.filter(status=status_filter)

    if class_filter:
        members_qs = members_qs.filter(assigned_class_id=class_filter)

    if gender_filter:
        members_qs = members_qs.filter(gender=gender_filter)

    # Stats
    total_members = Member.objects.count()
    active_members = Member.objects.filter(status='ACTIVE').count()
    pending_members = Member.objects.filter(status='PENDING').count()
    by_status = Member.objects.values('status').annotate(count=models.Count('id'))
    by_gender = Member.objects.values('gender').annotate(count=models.Count('id'))
    by_class = Member.objects.values('assigned_class__name').annotate(count=models.Count('id')).order_by('-count')[:5]

    paginator = Paginator(members_qs.order_by('first_name', 'last_name'), 20)
    page_number = request.GET.get('page')
    members_page = paginator.get_page(page_number)

    from classes.models import ClassGroup
    classes = ClassGroup.objects.filter(is_active=True).order_by('name')

    # Log report generation
    if request.GET.get('log') == '1':
        GeneratedReportLog.objects.create(
            report_type='MEMBERSHIP',
            title=f"Membership Report – {timezone.now().date()}",
            description=f"Filters: status={status_filter}, class={class_filter}, q={q}",
            parameters={"q": q, "status": status_filter, "class": class_filter, "gender": gender_filter},
            generated_by=request.user,
        )
        messages.success(request, "Membership report logged.")

    context = {
        "active_nav": "reports",
        "members": members_page,
        "members_page": members_page,
        "paginator": paginator,
        "classes": classes,
        "q": q,
        "status_filter": status_filter,
        "class_filter": class_filter,
        "gender_filter": gender_filter,
        "total_members": total_members,
        "active_members": active_members,
        "pending_members": pending_members,
        "by_status": by_status,
        "by_gender": by_gender,
        "by_class": by_class,
        "status_choices": Member.STATUS_CHOICES,
        "gender_choices": Member.GENDER_CHOICES,
        "filtered_count": members_qs.count(),
    }
    return render(request, "reports/m2membership_report.html", context)


@login_required(login_url='accounts:login')
def attendance_report_view(request):
    service_qs = ServiceAttendance.objects.select_related('service').all()
    class_qs = ClassAttendanceRecord.objects.select_related('class_group').all()

    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    service_type = request.GET.get('service_type', '').strip()

    if date_from:
        try:
            from_date = datetime.datetime.strptime(date_from, '%Y-%m-%d').date()
            service_qs = service_qs.filter(service_date__gte=from_date)
            class_qs = class_qs.filter(date__gte=from_date)
        except ValueError:
            pass

    if date_to:
        try:
            to_date = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()
            service_qs = service_qs.filter(service_date__lte=to_date)
            class_qs = class_qs.filter(date__lte=to_date)
        except ValueError:
            pass

    if service_type:
        service_qs = service_qs.filter(service__service_type=service_type)

    # Stats
    total_service = service_qs.aggregate(total=models.Sum('total_count'))['total'] or 0
    avg_service = service_qs.aggregate(avg=models.Avg('total_count'))['avg'] or 0
    total_class_records = class_qs.count()
    avg_class_rate = 0
    if class_qs.exists():
        rates = [r.attendance_rate for r in class_qs[:50]]
        avg_class_rate = sum(rates) / len(rates) if rates else 0

    # Monthly trend
    today = timezone.now().date()
    monthly_trend = []
    for i in range(5, -1, -1):
        m_date = today - datetime.timedelta(days=30*i)
        m_total = ServiceAttendance.objects.filter(
            service_date__month=m_date.month,
            service_date__year=m_date.year
        ).aggregate(total=models.Sum('total_count'))['total'] or 0
        monthly_trend.append({'label': m_date.strftime('%b'), 'total': m_total})

    paginator = Paginator(service_qs.order_by('-service_date'), 15)
    page_number = request.GET.get('page')
    service_page = paginator.get_page(page_number)

    from services.models import ChurchService
    type_choices = ChurchService.SERVICE_TYPE_CHOICES

    context = {
        "active_nav": "reports",
        "service_attendances": service_page,
        "service_page": service_page,
        "class_records": class_qs.order_by('-date')[:10],
        "paginator": paginator,
        "date_from": date_from,
        "date_to": date_to,
        "type_filter": service_type,
        "total_service": total_service,
        "avg_service": round(avg_service, 1),
        "total_class_records": total_class_records,
        "avg_class_rate": round(avg_class_rate, 1),
        "monthly_trend": monthly_trend,
        "type_choices": type_choices,
        "filtered_count": service_qs.count(),
    }
    return render(request, "reports/m3att_report.html", context)


@login_required(login_url='accounts:login')
def finance_report_view(request):
    incomes_qs = IncomeLedger.objects.select_related('recorded_by').all()
    expenses_qs = ExpenseLedger.objects.select_related('recorded_by').all()

    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    category = request.GET.get('category', '').strip()

    if date_from:
        try:
            from_date = datetime.datetime.strptime(date_from, '%Y-%m-%d').date()
            incomes_qs = incomes_qs.filter(date__gte=from_date)
            expenses_qs = expenses_qs.filter(date__gte=from_date)
        except ValueError:
            pass

    if date_to:
        try:
            to_date = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()
            incomes_qs = incomes_qs.filter(date__lte=to_date)
            expenses_qs = expenses_qs.filter(date__lte=to_date)
        except ValueError:
            pass

    if category:
        incomes_qs = incomes_qs.filter(category=category)
        expenses_qs = expenses_qs.filter(category=category)

    # Stats
    total_income = incomes_qs.aggregate(total=models.Sum('amount'))['total'] or 0
    total_expense = expenses_qs.aggregate(total=models.Sum('amount'))['total'] or 0
    balance = total_income - total_expense
    avg_income = incomes_qs.aggregate(avg=models.Avg('amount'))['avg'] or 0

    # By category
    income_by_cat = incomes_qs.values('category').annotate(total=models.Sum('amount')).order_by('-total')
    expense_by_cat = expenses_qs.values('category').annotate(total=models.Sum('amount')).order_by('-total')

    # Monthly trend
    today = timezone.now().date()
    finance_trend = []
    for i in range(5, -1, -1):
        m_date = today - datetime.timedelta(days=30*i)
        m_income = IncomeLedger.objects.filter(date__month=m_date.month, date__year=m_date.year).aggregate(total=models.Sum('amount'))['total'] or 0
        m_expense = ExpenseLedger.objects.filter(date__month=m_date.month, date__year=m_date.year).aggregate(total=models.Sum('amount'))['total'] or 0
        finance_trend.append({
            'label': m_date.strftime('%b'),
            'income': m_income,
            'expense': m_expense,
        })

    # Recent
    recent_incomes = incomes_qs.order_by('-date')[:10]
    recent_expenses = expenses_qs.order_by('-date')[:10]

    context = {
        "active_nav": "reports",
        "incomes": recent_incomes,
        "expenses": recent_expenses,
        "incomes_qs": incomes_qs,
        "expenses_qs": expenses_qs,
        "date_from": date_from,
        "date_to": date_to,
        "category_filter": category,
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": balance,
        "avg_income": round(avg_income, 2),
        "income_by_cat": income_by_cat,
        "expense_by_cat": expense_by_cat,
        "finance_trend": finance_trend,
        "filtered_income_count": incomes_qs.count(),
        "filtered_expense_count": expenses_qs.count(),
    }
    return render(request, "reports/m4finance_report.html", context)


@login_required(login_url='accounts:login')
def welfare_report_view(request):
    cases_qs = WelfareCase.objects.select_related('member', 'assigned_officer').all()

    q = request.GET.get('q', '').strip()
    case_type = request.GET.get('case_type', '').strip()
    status_filter = request.GET.get('status', '').strip()
    priority = request.GET.get('priority', '').strip()

    if q:
        cases_qs = cases_qs.filter(
            models.Q(title__icontains=q) | models.Q(description__icontains=q) | models.Q(member__first_name__icontains=q)
        )

    if case_type:
        cases_qs = cases_qs.filter(case_type=case_type)

    if status_filter:
        cases_qs = cases_qs.filter(status=status_filter)

    if priority:
        cases_qs = cases_qs.filter(priority=priority)

    # Stats
    total_cases = WelfareCase.objects.count()
    open_cases = WelfareCase.objects.exclude(status__in=['CLOSED', 'REJECTED']).count()
    total_requested = WelfareCase.objects.aggregate(total=models.Sum('requested_amount'))['total'] or 0
    total_approved = WelfareCase.objects.aggregate(total=models.Sum('approved_amount'))['total'] or 0
    by_status = WelfareCase.objects.values('status').annotate(count=models.Count('id'))
    by_type = WelfareCase.objects.values('case_type').annotate(count=models.Count('id'))

    paginator = Paginator(cases_qs.order_by('-created_at'), 15)
    page_number = request.GET.get('page')
    cases_page = paginator.get_page(page_number)

    context = {
        "active_nav": "reports",
        "cases": cases_page,
        "cases_page": cases_page,
        "paginator": paginator,
        "q": q,
        "case_type_filter": case_type,
        "status_filter": status_filter,
        "priority_filter": priority,
        "total_cases": total_cases,
        "open_cases": open_cases,
        "total_requested": total_requested,
        "total_approved": total_approved,
        "by_status": by_status,
        "by_type": by_type,
        "case_type_choices": WelfareCase.CASE_TYPE_CHOICES,
        "status_choices": WelfareCase.STATUS_CHOICES,
        "priority_choices": WelfareCase.PRIORITY_CHOICES,
        "filtered_count": cases_qs.count(),
    }
    return render(request, "reports/m5welfare_report.html", context)


@login_required(login_url='accounts:login')
def annual_report_view(request):
    year = request.GET.get('year', str(timezone.now().year))
    try:
        year_int = int(year)
    except ValueError:
        year_int = timezone.now().year

    # Yearly aggregates
    members_total = Member.objects.count()
    members_new_year = Member.objects.filter(created_at__year=year_int).count() if hasattr(Member, 'created_at') else 0
    attendance_total = ServiceAttendance.objects.filter(service_date__year=year_int).aggregate(total=models.Sum('total_count'))['total'] or 0
    income_total = IncomeLedger.objects.filter(date__year=year_int).aggregate(total=models.Sum('amount'))['total'] or 0
    expense_total = ExpenseLedger.objects.filter(date__year=year_int).aggregate(total=models.Sum('amount'))['total'] or 0
    welfare_total = WelfareCase.objects.filter(created_at__year=year_int).count()
    welfare_approved = WelfareCase.objects.filter(created_at__year=year_int).aggregate(total=models.Sum('approved_amount'))['total'] or 0

    # Quarterly breakdown
    quarterly = []
    for q in range(1, 5):
        months = range((q-1)*3+1, q*3+1)
        q_income = IncomeLedger.objects.filter(date__month__in=months, date__year=year_int).aggregate(total=models.Sum('amount'))['total'] or 0
        q_expense = ExpenseLedger.objects.filter(date__month__in=months, date__year=year_int).aggregate(total=models.Sum('amount'))['total'] or 0
        q_att = ServiceAttendance.objects.filter(service_date__month__in=months, service_date__year=year_int).aggregate(total=models.Sum('total_count'))['total'] or 0
        quarterly.append({
            'quarter': f'Q{q}',
            'income': q_income,
            'expense': q_expense,
            'attendance': q_att,
            'balance': q_income - q_expense,
        })

    # Generate log
    if request.GET.get('log') == '1':
        GeneratedReportLog.objects.create(
            report_type='ANNUAL',
            title=f"Annual Report {year_int}",
            description=f"Yearly summary for {year_int}",
            parameters={"year": year_int},
            generated_by=request.user,
        )
        messages.success(request, f"Annual report for {year_int} logged.")

    context = {
        "active_nav": "reports",
        "year": year_int,
        "members_total": members_total,
        "members_new_year": members_new_year,
        "attendance_total": attendance_total,
        "income_total": income_total,
        "expense_total": expense_total,
        "balance": income_total - expense_total,
        "welfare_total": welfare_total,
        "welfare_approved": welfare_approved,
        "quarterly": quarterly,
    }
    return render(request, "reports/annual_report.html", context)


# CSV Exports – enhanced with filters
@login_required(login_url='accounts:login')
def export_members_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="mcg_society_members.csv"'

    writer = csv.writer(response)
    writer.writerow(['Member ID', 'First Name', 'Last Name', 'Gender', 'Phone', 'Email', 'Assigned Class', 'Status', 'Date Joined'])

    members = Member.objects.select_related('assigned_class').all()
    # Apply same filters as report if provided
    q = request.GET.get('q')
    if q:
        members = members.filter(
            models.Q(first_name__icontains=q) | models.Q(last_name__icontains=q)
        )

    for m in members:
        writer.writerow([
            f"MCG-00{m.id}",
            m.first_name,
            m.last_name,
            m.get_gender_display(),
            m.phone_number or '',
            m.email or '',
            m.assigned_class.name if m.assigned_class else 'Unassigned',
            m.get_status_display(),
            m.created_at.strftime('%Y-%m-%d') if hasattr(m, 'created_at') and m.created_at else '',
        ])

    # Log export
    GeneratedReportLog.objects.create(
        report_type='MEMBERSHIP',
        title=f"Members Export {timezone.now().date()}",
        description=f"Exported {members.count()} members",
        parameters={"q": q or ''},
        generated_by=request.user,
        file_size=len(response.content),
    )

    return response


@login_required(login_url='accounts:login')
def export_finance_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="mcg_cashbook_export.csv"'

    writer = csv.writer(response)
    writer.writerow(['Ref No', 'Type', 'Category', 'Amount (GHS)', 'Date', 'Recorded By', 'Remarks'])

    incomes = IncomeLedger.objects.all()
    expenses = ExpenseLedger.objects.all()

    for inc in incomes:
        writer.writerow([
            f"INC-{inc.id}",
            'Income',
            inc.get_category_display(),
            inc.amount,
            inc.date,
            inc.recorded_by.username if inc.recorded_by else 'System',
            inc.remarks or ''
        ])
    for exp in expenses:
        writer.writerow([
            f"EXP-{exp.id}",
            'Expense',
            exp.get_category_display(),
            exp.amount,
            exp.date,
            exp.recorded_by.username if exp.recorded_by else 'System',
            exp.title
        ])

    GeneratedReportLog.objects.create(
        report_type='FINANCIAL',
        title=f"Finance Export {timezone.now().date()}",
        description=f"Income: {incomes.count()}, Expenses: {expenses.count()}",
        generated_by=request.user,
        file_size=len(response.content),
    )

    return response


@login_required(login_url='accounts:login')
def export_welfare_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="mcg_welfare_cases.csv"'

    writer = csv.writer(response)
    writer.writerow(['Case ID', 'Member', 'Case Type', 'Requested (GHS)', 'Approved (GHS)', 'Status', 'Priority', 'Date Created'])

    cases = WelfareCase.objects.select_related('member').all()
    for c in cases:
        writer.writerow([
            f"WF-2026-00{c.id}",
            c.member.get_full_name(),
            c.get_case_type_display(),
            c.requested_amount,
            c.approved_amount,
            c.get_status_display(),
            c.get_priority_display(),
            c.created_at.strftime('%Y-%m-%d')
        ])

    GeneratedReportLog.objects.create(
        report_type='WELFARE',
        title=f"Welfare Export {timezone.now().date()}",
        description=f"Exported {cases.count()} cases",
        generated_by=request.user,
        file_size=len(response.content),
    )

    return response