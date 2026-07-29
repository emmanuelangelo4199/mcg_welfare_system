from django.shortcuts import render

def org_list_view(request):
    return render(request, "organisations/e1org_list.html")

def org_details_view(request):
    return render(request, "organisations/e2org_details.html")

def add_edit_org_view(request):
    return render(request, "organisations/e3add_org_edit.html")

def dues_contribution_view(request):
    return render(request, "organisations/e5dues_contribution.html")

def org_attendance_view(request):
    return render(request, "organisations/org_attendance.html")
