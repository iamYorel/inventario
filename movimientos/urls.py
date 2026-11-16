from django.urls import path

from . import views

app_name = 'movimientos'

urlpatterns = [
    path('', views.MovimientoListView.as_view(), name='lista'),
    path('nuevo/', views.MovimientoCrearView.as_view(), name='crear'),
    path('<int:pk>/', views.MovimientoDetailView.as_view(), name='detalle'),
    path('<int:pk>/editar/', views.MovimientoEditarView.as_view(), name='editar'),
    path('<int:pk>/eliminar/', views.MovimientoEliminarView.as_view(), name='eliminar'),
]
