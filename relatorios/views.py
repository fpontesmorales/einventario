from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from patrimonio.models import Bem, Sala, Bloco
from inventarios.models import Inventario, Vistoria

def _parse_dt(s):
    if not s:
        return None
    try:
        # aceita "YYYY-MM-DD" ou "YYYY-MM-DDTHH:MM"
        return datetime.fromisoformat(s)
    except ValueError:
        return None

def _filtra_base(request):
    inventario_id = request.GET.get("inventario")
    bloco_id = request.GET.get("bloco")
    sala_id = request.GET.get("sala")
    dt_ini = _parse_dt(request.GET.get("de"))
    dt_fim = _parse_dt(request.GET.get("ate"))

    qs = Vistoria.objects.select_related(
        "bem", "bem__sala", "bem__sala__bloco", "inventario", "usuario"
    )

    # Ajuste o valor abaixo para o status usado no seu model (ex.: "NAO_LOCALIZADO")
    qs = qs.filter(status__iexact="NAO_LOCALIZADO")

    if inventario_id:
        qs = qs.filter(inventario_id=inventario_id)
    if bloco_id:
        qs = qs.filter(bem__sala__bloco_id=bloco_id)
    if sala_id:
        qs = qs.filter(bem__sala_id=sala_id)
    if dt_ini:
        qs = qs.filter(created_at__gte=dt_ini)
    if dt_fim:
        qs = qs.filter(created_at__lte=dt_fim)

    return qs, dict(
        inventarios=Inventario.objects.order_by("-ano"),
        blocos=Bloco.objects.order_by("nome"),
        salas=Sala.objects.order_by("nome"),
    )

@login_required
def nao_localizados_view(request):
    qs, ctx_lists = _filtra_base(request)
    ctx = {"rows": qs.order_by("bem__tombamento"), **ctx_lists}
    return render(request, "relatorios/nao_localizados.html", ctx)

@login_required
def nao_localizados_csv(request):
    qs, _ = _filtra_base(request)
    headers = [
        "tombamento",
        "descricao",
        "sala_cadastro",
        "sala_prevista_ou_achada",
        "ultima_vistoria",
        "vistoriador",
    ]
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="nao_localizados.csv"'
    resp.write(",".join(headers) + "\n")
    for v in qs.iterator():
        bem = v.bem
        row = [
            str(getattr(bem, "tombamento", "")),
            (getattr(bem, "descricao", "") or "").replace("\n", " ").replace(",", " "),
            getattr(bem.sala, "nome", "") if (bem and bem.sala) else "",
            getattr(v, "sala_encontrada_nome", "") or getattr(v, "sala_encontrada", "") or "",
            v.created_at.strftime("%Y-%m-%d %H:%M") if getattr(v, "created_at", None) else "",
            (getattr(v.usuario, "get_full_name", None)() if getattr(v, "usuario", None) and hasattr(v.usuario, "get_full_name") else getattr(getattr(v, "usuario", None), "username", "")),
        ]
        resp.write(",".join([str(x) for x in row]) + "\n")
    return resp
