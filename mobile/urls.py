from django.urls import path
from . import views

urlpatterns = [
    path('bens/<int:bem_id>/', views.bem_acao, name='mobile_bem_detail'),
    path('salas/lista/', views.home, name='mobile_salas'),
    path('api/salas/', views.api_salas, name='mobile_api_salas'),
    path("", views.home, name="mobile_home"),
    path("buscar/", views.buscar_global, name="mobile_buscar_global"),
    path("salas/<int:sala_id>/", views.sala_detail, name="mobile_sala_detail"),
    path("salas/<int:sala_id>/buscar/", views.buscar_tombamento, name="mobile_buscar_tombamento"),
    path("salas/<int:sala_id>/sem-registro/", views.sem_registro, name="mobile_sem_registro"),
    path("salas/<int:sala_id>/puxar/", views.puxar_para_sala, name="mobile_puxar_para_sala"),
    path("salas/<int:sala_id>/fechar/", views.marcar_restantes_nl, name="mobile_fechar_sala"),
    path("bens/<int:bem_id>/", views.bem_acao, name="mobile_bem_acao"),
]
