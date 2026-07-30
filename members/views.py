from django.shortcuts import render

def member_directory_view(request):
    return render(request, "members/c1member_directory.html", {"active_nav": "members"})

def member_registration_view(request):
    return render(request, "members/c2member_registration.html", {"active_nav": "members"})

def member_profile_view(request):
    return render(request, "members/c3member_profile.html", {"active_nav": "members"})

def edit_member_view(request):
    return render(request, "members/c4edit_member.html", {"active_nav": "members"})

def pending_members_view(request):
    return render(request, "members/c5pending_member_list.html", {"active_nav": "members"})

def member_regularisation_view(request):
    return render(request, "members/c6member_regularisation.html", {"active_nav": "members"})

def member_transfer_view(request):
    return render(request, "members/c7member_transfer.html", {"active_nav": "members"})

def status_management_view(request):
    return render(request, "members/c8status_management.html", {"active_nav": "members"})
