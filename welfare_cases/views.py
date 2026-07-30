from django.shortcuts import render

def welfare_cases_list_view(request):
    return render(request, "welfare_cases/welfare_cases_list.html", {"active_nav": "welfare_cases"})

def new_welfare_case_view(request):
    return render(request, "welfare_cases/new_welfare_case.html", {"active_nav": "welfare_cases"})

def welfare_case_details_view(request):
    return render(request, "welfare_cases/welfare_case_details.html", {"active_nav": "welfare_cases"})

def visit_record_form_view(request):
    return render(request, "welfare_cases/visit_record_form.html", {"active_nav": "welfare_cases"})

def welfare_payment_view(request):
    return render(request, "welfare_cases/welfare_payment.html", {"active_nav": "welfare_cases"})

def welfare_closure_view(request):
    return render(request, "welfare_cases/closure.html", {"active_nav": "welfare_cases"})
