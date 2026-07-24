from django.shortcuts import render

def main_dashboard(request):
    context = {}
    
    return render(request, "dashboard/m_dashboard.html", context)