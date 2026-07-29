from django.urls import path
from . import views

app_name = 'welfare_cases'

urlpatterns = [
    path('', views.welfare_cases_list_view, name='welfare_cases_list'),
    path('new/', views.new_welfare_case_view, name='new_welfare_case'),
    path('details/', views.welfare_case_details_view, name='welfare_case_details'),
    path('visit-record/', views.visit_record_form_view, name='visit_record_form'),
    path('payment/', views.welfare_payment_view, name='welfare_payment'),
    path('closure/', views.welfare_closure_view, name='welfare_closure'),
]
