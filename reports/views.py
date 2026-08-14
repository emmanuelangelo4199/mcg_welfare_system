import csv
from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import GeneratedReportLog
from members.models import Member
from finance.models import IncomeLedger, ExpenseLedger
from welfare_cases.models import WelfareCase

@login_required(login_url='accounts:login')
def reports_hub_view(request):
    reports = GeneratedReportLog.objects.all().order_by('-generated_at')
    return render(request, "reports/m1report_page.html", {
        "active_nav": "reports",
        "reports": reports
    })

@login_required(login_url='accounts:login')
def membership_report_view(request):
    members = Member.objects.select_related('assigned_class').all()
    return render(request, "reports/m2membership_report.html", {
        "active_nav": "reports",
        "members": members
    })

@login_required(login_url='accounts:login')
def attendance_report_view(request):
    return render(request, "reports/m3att_report.html", {"active_nav": "reports"})

@login_required(login_url='accounts:login')
def finance_report_view(request):
    incomes = IncomeLedger.objects.all()
    expenses = ExpenseLedger.objects.all()
    return render(request, "reports/m4finance_report.html", {
        "active_nav": "reports",
        "incomes": incomes,
        "expenses": expenses
    })

@login_required(login_url='accounts:login')
def welfare_report_view(request):
    cases = WelfareCase.objects.select_related('member').all()
    return render(request, "reports/m5welfare_report.html", {
        "active_nav": "reports",
        "cases": cases
    })

@login_required(login_url='accounts:login')
def annual_report_view(request):
    return render(request, "reports/annual_report.html", {"active_nav": "reports"})

# CSV Exports
@login_required(login_url='accounts:login')
def export_members_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="mcg_society_members.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Member ID', 'First Name', 'Last Name', 'Gender', 'Phone', 'Email', 'Assigned Class', 'Status', 'Date Joined'])
    
    members = Member.objects.select_related('assigned_class').all()
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
            m.created_at.strftime('%Y-%m-%d')
        ])
    return response

@login_required(login_url='accounts:login')
def export_finance_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="mcg_cashbook_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Ref No', 'Type', 'Category', 'Amount (GHS)', 'Date', 'Recorded By', 'Remarks'])
    
    for inc in IncomeLedger.objects.all():
        writer.writerow([
            f"INC-{inc.id}",
            'Income',
            inc.get_category_display(),
            inc.amount,
            inc.date,
            inc.recorded_by.username if inc.recorded_by else 'System',
            inc.remarks or ''
        ])
    for exp in ExpenseLedger.objects.all():
        writer.writerow([
            f"EXP-{exp.id}",
            'Expense',
            exp.category,
            exp.amount,
            exp.date,
            exp.recorded_by.username if exp.recorded_by else 'System',
            exp.title
        ])
    return response

@login_required(login_url='accounts:login')
def export_welfare_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="mcg_welfare_cases.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Case ID', 'Member', 'Case Type', 'Requested (GHS)', 'Approved (GHS)', 'Status', 'Date Created'])
    
    cases = WelfareCase.objects.select_related('member').all()
    for c in cases:
        writer.writerow([
            f"WF-2026-00{c.id}",
            c.member.get_full_name(),
            c.get_case_type_display(),
            c.requested_amount,
            c.approved_amount,
            c.get_status_display(),
            c.created_at.strftime('%Y-%m-%d')
        ])
    return response
