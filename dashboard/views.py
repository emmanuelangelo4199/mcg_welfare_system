from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from core.decorators import role_required
from members.models import Member
from welfare_cases.models import WelfareCase
from finance.models import IncomeLedger, ExpenseLedger
from services.models import ChurchService
from classes.models import ClassGroup

@login_required(login_url='accounts:login')
def main_dashboard(request):
    total_members_count = Member.objects.count()
    pending_members_count = Member.objects.filter(status='PENDING').count()
    active_welfare_cases_count = WelfareCase.objects.exclude(status__in=['CLOSED', 'REJECTED']).count()
    
    total_income = IncomeLedger.objects.aggregate(total=Sum('amount'))['total'] or 0
    total_expense = ExpenseLedger.objects.filter(status='APPROVED').aggregate(total=Sum('amount'))['total'] or 0

    recent_members = Member.objects.select_related('assigned_class').all().order_by('-created_at')[:5]
    upcoming_services = ChurchService.objects.all().order_by('service_date')[:5]

    return render(request, "dashboard/m_dashboard.html", {
        "active_nav": "dashboard",
        "total_members_count": total_members_count,
        "pending_members_count": pending_members_count,
        "active_welfare_cases_count": active_welfare_cases_count,
        "total_income": total_income,
        "total_expense": total_expense,
        "recent_members": recent_members,
        "upcoming_services": upcoming_services
    })

@role_required(allowed_roles=['ADMIN', 'TREASURER'])
def treasurer_dashboard(request):
    total_income = IncomeLedger.objects.aggregate(total=Sum('amount'))['total'] or 0
    total_expense = ExpenseLedger.objects.filter(status='APPROVED').aggregate(total=Sum('amount'))['total'] or 0
    net_balance = total_income - total_expense
    pending_expenses = ExpenseLedger.objects.filter(status='PENDING').order_by('-date')

    return render(request, "dashboard/treasurer.html", {
        "active_nav": "dashboard",
        "total_income": total_income,
        "total_expense": total_expense,
        "net_balance": net_balance,
        "pending_expenses": pending_expenses
    })

@role_required(allowed_roles=['ADMIN', 'CLASS_LEADER'])
def class_leader_dashboard(request):
    classes = ClassGroup.objects.all()
    members = Member.objects.select_related('assigned_class').all()

    return render(request, "dashboard/class_leader.html", {
        "active_nav": "dashboard",
        "classes": classes,
        "members": members
    })