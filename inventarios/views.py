ï»¿from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render
from django.db.models import Q
from django.contrib.auth import get_user_model
from urllib.parse import urlencode

from .models import Inventario, Vistoria, Importacao
from patrimonio.models import Bem, Sala

User = get_user_model()


# ---------- util ----------
def _inv_ativo():
    return Inventario.objects.filter(ativo=True).order_by("-ano").first()

def _is_staff_or_gestor(u):
    if not u.is_authenticated:
        return False
    perfil = getattr(u, "perfil", None)
    return u.is_staff or u.is_superuser or perfil in ("GESTOR", "VISTORIADOR")

def _estado_code_from_text(txt: str) -> str:
    t = (txt or "").strip().lower()
    if not t:
        return ""
    if t.startswith(("Ã³t", "ot")): return "OTIMO"
    if t.startswith("bo"):         return "BOM"
    if t.startswith("reg"):        return "REGULAR"
    if t.startswith("ru"):         return "RUIM"
    if t.startswith(("ins","inserv")): return "INSERVIVEL"
    return ""

def _estado_from_bem(bem) -> str:
    for attr in ("estado", "estado_bem", "estado_conservacao"):
        if hasattr(bem, attr):
            code = _estado_code_from_text(getattr(bem, attr))
            if code:
                return code
    return ""

def _resp_from_bem(bem) -> str:
    for attr in ("carga_atual", "responsavel", "responsavel_atual", "servidor_carga", "usuario"):
        if hasattr(bem, attr):
            val = getattr(bem, attr)
            if val is None:
                continue
            if not isinstance(val, str):
                val = str(val)
            val = val.strip()
            if val:
                return val
    return ""


# ---------- relatÃ³rio de divergÃªncias ----------
def _filtrar_divergencias(inv, params):
    qs = Vistoria.objects.none()
    if not inv:
        return qs
    qs = (
        Vistoria.objects
        .filter(inventario=inv, status=Vistoria.Status.DIVERGENTE)
        .select_related("bem", "sala_encontrada", "bem__sala_oficial")
        .order_by("bem__tombamento")
    )

    q = (params.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(bem__tombamento__icontains=q) |
            Q(bem__descricao__icontains=q) |
            Q(responsavel_encontrado__icontains=q)
        )

    sala_id = (params.get("sala") or "").strip()
    if sala_id.isdigit():
        qs = qs.filter(Q(bem__sala_oficial_id=int(sala_id)) | Q(sala_encontrada_id=int(sala_id)))

    bloco = (params.get("bloco") or "").strip()
    if bloco:
        qs = qs.filter(Q(bem__sala_oficial__bloco__icontains=bloco) | Q(sala_encontrada__bloco__icontains=bloco))

    vist = (params.get("vistoriador") or "").strip()
    if vist.isdigit():
        qs = qs.filter(vistoriador_id=int(vist))

    return qs

@login_required
@user_passes_test(_is_staff_or_gestor)
def relatorio_divergencias(request):
    inv = _inv_ativo()
    qs = _filtrar_divergencias(inv, request.GET)

    total = qs.count()
    por_sala = por_estado = ambos = 0
    itens = []

    p = int(request.GET.get("p", 1)) if request.GET.get("p", "1").isdigit() else 1
    paginator = Paginator(qs, 50)
    page = paginator.get_page(p)

    for v in page.object_list:
        b = v.bem
        est_cad = _estado_from_bem(b)
        sala_diff = (b.sala_oficial_id or 0) != (v.sala_encontrada_id or (b.sala_oficial_id or 0))
        est_diff  = bool(est_cad and v.estado_encontrado and est_cad != v.estado_encontrado)
        if sala_diff and est_diff: ambos += 1
        elif sala_diff:            por_sala += 1
        elif est_diff:             por_estado += 1

        itens.append({
            "tombamento": b.tombamento,
            "descricao": getattr(b, "descricao", ""),
            "sala_oficial": getattr(b.sala_oficial, "nome", None),
            "sala_encontrada": getattr(v.sala_encontrada, "nome", None),
            "estado_cadastro": est_cad,
            "estado_encontrado": v.estado_encontrado or "",
            "responsavel_cadastro": _resp_from_bem(b),
            "responsavel_encontrado": v.responsavel_encontrado or "",
            "vistoria_id": v.id,
        })

    salas = Sala.objects.all().order_by("nome")
    vists = User.objects.filter(id__in=qs.values_list("vistoriador_id", flat=True)).order_by("username")

    params = request.GET.copy(); params.pop("p", None)
    qs_base = urlencode(params, doseq=True)

    ctx = {
        "inventario": inv,
        "itens": itens,
        "total": total,
        "por_sala": por_sala,
        "por_estado": por_estado,
        "ambos": ambos,
        "salas": salas,
        "vistoriadores": vists,
        "page": page,
        "qs_base": qs_base,
        "params": request.GET,
    }
    return render(request, "inventarios/divergencias.html", ctx)

@login_required
@user_passes_test(_is_staff_or_gestor)
def relatorio_divergencias_csv(request):
    inv = _inv_ativo()
    qs = _filtrar_divergencias(inv, request.GET)

    rows = [["tombamento","descricao","sala_oficial","sala_encontrada","estado_cadastro","estado_encontrado","responsavel_cadastro","responsavel_encontrado","vistoria_id"]]
    for v in qs:
        b = v.bem
        rows.append([
            b.tombamento,
            getattr(b, "descricao", ""),
            getattr(b.sala_oficial, "nome", ""),
            getattr(v.sala_encontrada, "nome", ""),
            _estado_from_bem(b),
            v.estado_encontrado or "",
            _resp_from_bem(b),
            v.responsavel_encontrado or "",
            str(v.id),
        ])

    out = "\r\n".join(";".join((str(c) if c is not None else "")) for c in rows)
    resp = HttpResponse(out, content_type="text/csv; charset=utf-8")
    nome = f"divergencias_{inv.ano if inv else 'sem_inv'}.csv"
    resp["Content-Disposition"] = f'attachment; filename="{nome}"'
    return resp


# ---------- prÃ©via de importaÃ§Ã£o ----------
def _get_importacao_para_previa(request):
    escopo = (request.GET.get("escopo") or "pendente").strip().lower()
    imp = None
    pendente = None
    if escopo == "pendente":
        pendente = Importacao.objects.filter(aplicado=False).order_by("-criado_em").first()
        imp = pendente or Importacao.objects.order_by("-criado_em").first()
    else:
        imp = Importacao.objects.order_by("-criado_em").first()
    return imp, (pendente is not None)

@staff_member_required
def importacao_previa(request):
    imp, tem_pendente = _get_importacao_para_previa(request)
    itens = list(imp.itens.all().order_by("tombamento")) if imp else []
    ctx = {
        "importacao": imp,
        "itens": itens,
        "tem_pendente": tem_pendente,
        "escopo": (request.GET.get("escopo") or "pendente"),
    }
    return render(request, "inventarios/importacao_previa.html", ctx)

@staff_member_required
def importacao_previa_csv(request):
    imp, _ = _get_importacao_para_previa(request)
    rows = [["tombamento","acao","diff","importacao_id","data","aplicado"]]
    if imp:
        for it in imp.itens.all().order_by("tombamento"):
            rows.append([
                it.tombamento,
                it.get_acao_display() if hasattr(it, "get_acao_display") else it.acao,
                (it.diff or "").replace("\r"," ").replace("\n"," "),
                str(imp.id),
                imp.criado_em.strftime("%d/%m/%Y %H:%M"),
                "Sim" if imp.aplicado else "NÃ£o",
            ])
    out = "\r\n".join(";".join((str(c) if c is not None else "")) for c in rows)
    resp = HttpResponse(out, content_type="text/csv; charset=utf-8")
    name = f"previa_importacao_{imp.id if imp else 'none'}.csv"
    resp["Content-Disposition"] = f'attachment; filename="{name}"'
    return resp
