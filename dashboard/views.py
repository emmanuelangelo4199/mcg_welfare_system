from django.shortcuts import render

def main_dashboard(request):
    return render(request, "dashboard/m_dashboard.html")

def treasurer_dashboard(request):
    return render(request, "dashboard/treasurer.html")

def class_leader_dashboard(request):
    return render(request, "dashboard/class_leader.html")