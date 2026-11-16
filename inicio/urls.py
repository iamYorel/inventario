from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'inicio'

urlpatterns = [
    path('', views.InicioView.as_view(), name='inicio'),
    path('ingresar/', auth_views.LoginView.as_view(
        template_name='inicio/ingresar.html',
        redirect_authenticated_user=True), name='ingresar'),
    path('salir/', auth_views.LogoutView.as_view(), name='salir'),
]
