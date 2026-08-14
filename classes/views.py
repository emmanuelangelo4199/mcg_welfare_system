from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import ClassGroup
from members.models import Member

@login_required(login_url='accounts:login')
def class_list_view(request):
    classes = ClassGroup.objects.select_related('leader').all()
    return render(request, "classes/d1class_list.html", {
        "active_nav": "classes",
        "classes": classes
    })

@login_required(login_url='accounts:login')
def class_detail_view(request):
    class_id = request.GET.get('id')
    class_group = get_object_or_404(ClassGroup, id=class_id) if class_id else ClassGroup.objects.first()
    members = Member.objects.filter(assigned_class=class_group) if class_group else []
    return render(request, "classes/d2class_detail.html", {
        "active_nav": "classes",
        "class_group": class_group,
        "members": members,
        "members_count": len(members)
    })

@login_required(login_url='accounts:login')
def add_edit_class_view(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        meeting_time = request.POST.get('meeting_time', '').strip()

        ClassGroup.objects.create(
            name=name,
            description=description,
            meeting_time=meeting_time
        )
        messages.success(request, f"Class '{name}' created successfully.")
        return redirect('classes:class_list')

    return render(request, "classes/d3add_edit_classForm.html", {"active_nav": "classes"})

@login_required(login_url='accounts:login')
def class_attendance_record_view(request):
    return render(request, "classes/d4class_attendance_record.html", {"active_nav": "classes"})

@login_required(login_url='accounts:login')
def class_attendance_report_view(request):
    return render(request, "classes/d5class_att_report.html", {"active_nav": "classes"})
