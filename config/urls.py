from django.urls import path
from tasks import views

urlpatterns = [
    path("api/health/", views.health),
    path("api/csrf/", views.csrf),
    path("api/login/", views.sign_in),
    path("api/logout/", views.sign_out),
    path("api/tasks/", views.tasks),
    path("api/tasks/<int:task_id>/", views.task_detail),
]
