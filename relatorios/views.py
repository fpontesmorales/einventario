from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.db.models import Count
from inventarios.models import Inventario, Vistoria

def is_gestor(user):
    return getattr(user, "perfil", None) == "GESTOR" or user.is_superuser

@login_required
@user_passes_test(is_gestor)
def resumo(request):
    inv = Inventario.objects.filter(ativo=True).order_by("-ano").first()
    por_status = Vistoria.objects.filter(inventario=inv).values("status").annotate(qtd=Count("id")).order_by("status") if inv else []
    por_vistoriador = Vistoria.objects.filter(inventario=inv).values("vistoriador__username").annotate(qtd=Count("id")).order_by("-qtd") if inv else []
    return render(request, "relatorios/resumo.html", {"inventario": inv, "por_status": por_status, "por_vistoriador": por_vistoriador})
