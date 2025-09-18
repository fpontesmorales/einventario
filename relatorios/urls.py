from django.urls import path
from . import views

urlpatterns = [
    path("nao-localizados/", views.nao_localizados_view, name="rel_nao_localizados"),
    path("nao-localizados.csv", views.nao_localizados_csv, name="rel_nao_localizados_csv"),
]
