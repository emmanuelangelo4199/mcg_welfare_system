from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.decorators import role_required
from .models import Member
from classes.models import ClassGroup

@login_required(login_url='accounts:login')
def member_directory_view(request):
    search_query = request.GET.get('q', '').strip()
    members = Member.objects.select_related('assigned_class').all()
    if search_query:
        members = members.filter(
            first_name__icontains=search_query
        ) | members.filter(
            last_name__icontains=search_query
        ) | members.filter(
            phone_number__icontains=search_query
        )

    return render(request, "members/c1member_directory.html", {
        "active_nav": "members",
        "members": members,
        "search_query": search_query
    })

@login_required(login_url='accounts:login')
def member_registration_view(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        gender = request.POST.get('gender', 'M')
        dob = request.POST.get('date_of_birth') or None
        phone = request.POST.get('phone_number', '').strip()
        email = request.POST.get('email', '').strip()
        address = request.POST.get('residential_address', '').strip()
        class_id = request.POST.get('assigned_class')
        emergency_name = request.POST.get('emergency_contact_name', '').strip()
        emergency_phone = request.POST.get('emergency_contact_phone', '').strip()

        assigned_class = None
        if class_id:
            assigned_class = ClassGroup.objects.filter(id=class_id).first()

        member = Member.objects.create(
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            date_of_birth=dob,
            phone_number=phone,
            email=email,
            residential_address=address,
            assigned_class=assigned_class,
            status='PENDING',
            emergency_contact_name=emergency_name,
            emergency_contact_phone=emergency_phone
        )
        messages.success(request, f"Member {member.get_full_name()} registered successfully!")
        return redirect('members:member_directory')

    classes = ClassGroup.objects.all()
    return render(request, "members/c2member_registration.html", {
        "active_nav": "members",
        "classes": classes
    })

@login_required(login_url='accounts:login')
def member_profile_view(request):
    member_id = request.GET.get('id')
    member = None
    if member_id:
        member = get_object_or_404(Member, id=member_id)
    else:
        member = Member.objects.first()

    return render(request, "members/c3member_profile.html", {
        "active_nav": "members",
        "member": member
    })

@login_required(login_url='accounts:login')
def edit_member_view(request):
    member_id = request.GET.get('id')
    member = get_object_or_404(Member, id=member_id) if member_id else Member.objects.first()

    if request.method == 'POST' and member:
        member.first_name = request.POST.get('first_name', member.first_name).strip()
        member.last_name = request.POST.get('last_name', member.last_name).strip()
        member.phone_number = request.POST.get('phone_number', member.phone_number).strip()
        member.email = request.POST.get('email', member.email).strip()
        member.save()
        messages.success(request, f"Updated profile for {member.get_full_name()}")
        return redirect('members:member_directory')

    classes = ClassGroup.objects.all()
    return render(request, "members/c4edit_member.html", {
        "active_nav": "members",
        "member": member,
        "classes": classes
    })

@role_required(allowed_roles=['ADMIN', 'CLASS_LEADER'])
def pending_members_view(request):
    pending_members = Member.objects.filter(status='PENDING').select_related('assigned_class')
    return render(request, "members/c5pending_member_list.html", {
        "active_nav": "members",
        "pending_members": pending_members
    })

@login_required(login_url='accounts:login')
def member_regularisation_view(request):
    return render(request, "members/c6member_regularisation.html", {"active_nav": "members"})

@login_required(login_url='accounts:login')
def member_transfer_view(request):
    return render(request, "members/c7member_transfer.html", {"active_nav": "members"})

@login_required(login_url='accounts:login')
def status_management_view(request):
    return render(request, "members/c8status_management.html", {"active_nav": "members"})
