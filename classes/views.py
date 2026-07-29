from django.shortcuts import render

def class_list_view(request):
    return render(request, "classes/d1class_list.html")

def class_detail_view(request):
    return render(request, "classes/d2class_detail.html")

def add_edit_class_view(request):
    return render(request, "classes/d3add_edit_classForm.html")

def class_attendance_record_view(request):
    return render(request, "classes/d4class_attendance_record.html")

def class_attendance_report_view(request):
    return render(request, "classes/d5class_att_report.html")
