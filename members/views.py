from django.shortcuts import render

def member_directory_view(request):
    return render(request, "members/c1member_directory.html")

def member_registration_view(request):
    return render(request, "members/c2member_registration.html")

def member_profile_view(request):
    return render(request, "members/c3member_profile.html")

def edit_member_view(request):
    return render(request, "members/c4edit_member.html")

def pending_members_view(request):
    return render(request, "members/c5pending_member_list.html")

def member_regularisation_view(request):
    return render(request, "members/c6member_regularisation.html")

def member_transfer_view(request):
    return render(request, "members/c7member_transfer.html")

def status_management_view(request):
    return render(request, "members/c8status_management.html")
