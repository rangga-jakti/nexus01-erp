from django.urls import path
from . import views
app_name = 'organization'
urlpatterns = [
    path('company/', views.placeholder, name='company_detail'),
]
