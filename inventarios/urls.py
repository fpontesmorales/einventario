from django.urls import path
from . import views

app_name = "inventarios"

urlpatterns = [
    path("relatorios/divergencias/", views.relatorio_divergencias, name="relatorio_divergencias"),
    path("relatorios/divergencias.csv", views.relatorio_divergencias_csv, name="relatorio_divergencias_csv"),
]