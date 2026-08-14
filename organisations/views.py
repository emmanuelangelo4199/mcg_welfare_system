from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Organisation, OrganisationDues

@login_required(login_url='accounts:login')
def org_list_view(request):
    organisations = Organisation.objects.select_related('president').all()
    return render(request, "organisations/e1org_list.html", {
        "active_nav": "organisations",
        "organisations": organisations
    })

@login_required(login_url='accounts:login')
def org_details_view(request):
    org_id = request.GET.get('id')
    org = get_object_or_404(Organisation, id=org_id) if org_id else Organisation.objects.first()
    dues = OrganisationDues.objects.filter(organisation=org).order_by('-date_paid') if org else []
    return render(request, "organisations/e2org_details.html", {
        "active_nav": "organisations",
        "organisation": org,
        "dues": dues
    })

@login_required(login_url='accounts:login')
def add_edit_org_view(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        schedule = request.POST.get('meeting_schedule', '').strip()

        Organisation.objects.create(
            name=name,
            description=description,
            meeting_schedule=schedule
        )
        messages.success(request, f"Organisation '{name}' added successfully.")
        return redirect('organisations:org_list')

    return render(request, "organisations/e3add_org_edit.html", {"active_nav": "organisations"})

@login_required(login_url='accounts:login')
def dues_contribution_view(request):
    if request.method == 'POST':
        org_id = request.POST.get('org_id')
        member_name = request.POST.get('member_name', '').strip()
        amount = request.POST.get('amount')
        date_paid = request.POST.get('date_paid')

        org = get_object_or_404(Organisation, id=org_id) if org_id else Organisation.objects.first()
        if org:
            OrganisationDues.objects.create(
                organisation=org,
                member_name=member_name,
                amount=amount,
                date_paid=date_paid
            )
            messages.success(request, f"Dues contribution for {member_name} recorded.")
            return redirect('organisations:org_list')

    dues = OrganisationDues.objects.select_related('organisation').all().order_by('-date_paid')
    return render(request, "organisations/e5dues_contribution.html", {
        "active_nav": "organisations",
        "dues": dues
    })

@login_required(login_url='accounts:login')
def org_attendance_view(request):
    return render(request, "organisations/org_attendance.html", {"active_nav": "organisations"})
