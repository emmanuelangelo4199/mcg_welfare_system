from django.shortcuts import render

def reports_hub_view(request):
    return render(request, "reports/m1report_page.html")

def membership_report_view(request):
    return render(request, "reports/m2membership_report.html")

def attendance_report_view(request):
    return render(request, "reports/m3att_report.html")

def finance_report_view(request):
    return render(request, "reports/m4finance_report.html")

def welfare_report_view(request):
    return render(request, "reports/m5welfare_report.html")

def annual_report_view(request):
    return render(request, "reports/annual_report.html")
