from django.shortcuts import render

def welfare_cases_list_view(request):
    return render(request, "welfare_cases/welfare_cases_list.html")

def new_welfare_case_view(request):
    return render(request, "welfare_cases/new_welfare_case.html")

def welfare_case_details_view(request):
    return render(request, "welfare_cases/welfare_case_details.html")

def visit_record_form_view(request):
    return render(request, "welfare_cases/visit_record_form.html")

def welfare_payment_view(request):
    return render(request, "welfare_cases/welfare_payment.html")

def welfare_closure_view(request):
    return render(request, "welfare_cases/closure.html")
