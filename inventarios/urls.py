from django.urls import path
from . import views

app_name = "inventarios"

urlpatterns = [
    path('importacoes/previa/', views.importacao_previa, name='importacao_previa'),
    path('importacoes/previa.csv', views.importacao_previa_csv, name='importacao_previa_csv'),
    path("relatorios/divergencias/", views.relatorio_divergencias, name="relatorio_divergencias"),
    path("relatorios/divergencias.csv", views.relatorio_divergencias_csv, name="relatorio_divergencias_csv"),
]