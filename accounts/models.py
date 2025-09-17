from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Perfil(models.TextChoices):
        GESTOR = "GESTOR", "Gestor"
        VISTORIADOR = "VISTORIADOR", "Vistoriador"

    perfil = models.CharField(
        max_length=20,
        choices=Perfil.choices,
        default=Perfil.VISTORIADOR,
    )

    def is_gestor(self):
        return self.perfil == self.Perfil.GESTOR

    def is_vistoriador(self):
        return self.perfil == self.Perfil.VISTORIADOR
