﻿from django.urls import path
from . import views

app_name = "relatorios"
urlpatterns = [ path("resumo/", views.resumo, name="resumo") ]
