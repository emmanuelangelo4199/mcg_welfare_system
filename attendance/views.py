from django.shortcuts import render

def overview_view(request):
    return render(request, "attendance/attendance_overview.html")

def service_attendance_view(request):
    return render(request, "attendance/service_att.html")

def class_attendance_view(request):
    return render(request, "attendance/class_att.html")

def org_attendance_view(request):
    return render(request, "attendance/org_attendance.html")

def absentee_report_view(request):
    return render(request, "attendance/abstee_report.html")
