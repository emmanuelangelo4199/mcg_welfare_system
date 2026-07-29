from django.urls import path
from . import views

app_name = 'communications'

urlpatterns = [
    path('compose/', views.compose_message_view, name='compose_message'),
    path('history/', views.message_history_view, name='message_history'),
    path('announcements/', views.announcement_board_view, name='announcement_board'),
    path('birthdays/', views.birthday_messages_view, name='birthday_messages'),
    path('reminders/', views.reminder_due_notice_view, name='reminder_due_notice'),
]
