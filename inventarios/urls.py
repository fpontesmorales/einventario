from django.urls import path
from . import views

app_name = "inventarios"

urlpatterns = [
    path("importar/", views.importar_csv, name="importar_csv"),
    path("api/v1/vistoria/", views.api_criar_vistoria, name="api_criar_vistoria"),
]
