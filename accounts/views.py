from django.shortcuts import render

def login_view(request):
    return render(request, "accounts/a1.html")

def register_view(request):
    return render(request, "accounts/a2.html")

def password_reset_view(request):
    return render(request, "accounts/a3.html")

def profile_view(request):
    return render(request, "accounts/n2.html")

def user_list_view(request):
    return render(request, "accounts/n3.html")

def roles_permissions_view(request):
    return render(request, "accounts/n5.html")
