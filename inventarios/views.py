import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.utils import timezone
from .forms import CSVUploadForm
from .models import Inventario, Vistoria
from patrimonio.models import Bem, Sala
from patrimonio.utils_csv import importar_bens_csv

def is_gestor(user):
    return getattr(user, "perfil", None) == "GESTOR" or user.is_superuser

@login_required
@user_passes_test(is_gestor)
@require_http_methods(["GET", "POST"])
def importar_csv(request):
    if request.method == "POST":
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            res = importar_bens_csv(form.cleaned_data["arquivo"])
            messages.success(request, f"Importação concluída. Novos: {res['novos']} | Atualizados: {res['atualizados']}")
            return redirect("inventarios:importar_csv")
    else:
        form = CSVUploadForm()
    return render(request, "inventarios/importar_csv.html", {"form": form})

@login_required
@require_http_methods(["POST"])
def api_criar_vistoria(request):
    payload = json.loads(request.body.decode("utf-8"))
    tomb = payload.get("tombamento")
    status = payload.get("status")
    inventario_ano = int(payload.get("inventario_ano"))
    sala_nome = payload.get("sala_encontrada")
    obs = payload.get("observacao") or ""

    inventario, _ = Inventario.objects.get_or_create(ano=inventario_ano, defaults={"ativo": True})
    try:
        bem = Bem.objects.get(tombamento=tomb)
    except Bem.DoesNotExist:
        sala, _ = Sala.objects.get_or_create(nome=sala_nome or "SEM SALA")
        bem = Bem.objects.create(tombamento=tomb, descricao="(Bem sem registro)", sala_oficial=sala)

    sala_encontrada = None
    if sala_nome:
        sala_encontrada, _ = Sala.objects.get_or_create(nome=sala_nome)

    vistoria = Vistoria.objects.create(
        inventario=inventario,
        bem=bem,
        sala_encontrada=sala_encontrada,
        vistoriador=request.user,
        status=status,
        observacao=obs,
        criado_em=timezone.now(),
    )

    if sala_encontrada and bem.sala_oficial and sala_encontrada != bem.sala_oficial and status == Vistoria.Status.CONFERIDO:
        vistoria.status = Vistoria.Status.DIVERGENTE
        vistoria.save(update_fields=["status"])

    return JsonResponse({"ok": True, "vistoria_id": vistoria.id})
