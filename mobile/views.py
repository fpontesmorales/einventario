# --- helpers (mobile) ---
def _inv_ativo():
    from inventarios.models import Inventario
    return Inventario.objects.filter(ativo=True).order_by("-ano").first()

def _estado_code_from_text(txt: str) -> str:
    t = (txt or "").strip().lower()
    if not t: return ""
    if t.startswith(("ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³t","ot")): return "OTIMO"
    if t.startswith("bo"):       return "BOM"
    if t.startswith("reg"):      return "REGULAR"
    if t.startswith("ru"):       return "RUIM"
    if t.startswith(("ins","inserv")): return "INSERVIVEL"
    return ""

def _estado_from_bem(bem) -> str:
    for attr in ("estado", "estado_bem", "estado_conservacao"):
        if hasattr(bem, attr):
            return _estado_code_from_text(getattr(bem, attr))
    return ""

def _resp_from_bem(bem) -> str:
    for attr in ("carga_atual","responsavel","responsavel_atual","servidor_carga","usuario"):
        if hasattr(bem, attr):
            v = getattr(bem, attr)
            if v:
                return str(v).strip()
    return ""
# --- fim helpers ---
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from patrimonio.models import Sala, Bem
from inventarios.models import Inventario, Vistoria, SemRegistro


def is_visit_user(user):
    perfil = getattr(user, "perfil", None)
    return (perfil in ("VISTORIADOR", "GESTOR")) or user.is_superuser


def _inventario_ativo():
    return Inventario.objects.filter(ativo=True).order_by("-ano").first()


def _status_corrente_por_bem(inv, bens_qs):
    mapa = {}
    if not inv:
        return mapa
    vqs = (
        Vistoria.objects.filter(inventario=inv, bem__in=bens_qs)
        .select_related("bem", "sala_encontrada")
        .order_by("bem_id", "-criado_em")
    )
    seen = set()
    for v in vqs:
        if v.bem_id in seen:
            continue
        seen.add(v.bem_id)
        mapa[v.bem_id] = v
    return mapa


def _sala_label(sala):
    if not sala:
        return ""
    return f"{sala.nome}{f' ({sala.bloco})' if getattr(sala, 'bloco', None) else ''}"


def _estado_code_from_text(txt: str) -> str:
    t = (txt or "").strip().lower()
    if not t:
        return ""
    if t.startswith(("ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³t", "ot")):
        return "OTIMO"
    if t.startswith("bo"):
        return "BOM"
    if t.startswith("reg"):
        return "REGULAR"
    if t.startswith("ru"):
        return "RUIM"
    if t.startswith(("ins", "inserv")):
        return "INSERVIVEL"
    return ""


def _estado_from_bem(bem) -> str:
    for attr in ("estado", "estado_bem", "estado_conservacao"):
        if hasattr(bem, attr):
            code = _estado_code_from_text(getattr(bem, attr))
            if code:
                return code
    return ""


def _resp_from_bem(bem) -> str:
    # prioriza campo pedido: carga_atual
    for attr in ("carga_atual", "responsavel", "responsavel_atual", "servidor_carga", "usuario"):
        if hasattr(bem, attr):
            val = getattr(bem, attr)
            if val is None:
                continue
            if isinstance(val, str):
                val = val.strip()
            else:
                val = str(val).strip()
            if val:
                return val
    return ""


@login_required
@user_passes_test(is_visit_user)
def home(request):
    inv = _inventario_ativo()
    termo = (request.GET.get("s") or "").strip()
    qs = Sala.objects.all()
    if termo:
        from django.db import models
        qs = qs.filter(models.Q(nome__icontains=termo) | models.Q(bloco__icontains=termo))
    salas_info = []
    for sala in qs:
        bens = Bem.objects.filter(sala_oficial=sala, tipo="BEM", ativo=True)
        total = bens.count()
        mapa = _status_corrente_por_bem(inv, bens)
        vist_ok = sum(
            1 for v in mapa.values()
            if v.status in (Vistoria.Status.CONFERIDO, Vistoria.Status.DIVERGENTE)
        )
        salas_info.append(
            {"sala": sala, "total": total, "vistoriados": vist_ok, "restantes": max(total - vist_ok, 0)}
        )
    salas_info.sort(key=lambda x: x["restantes"], reverse=True)
    return render(request, "mobile/index.html", {"inventario": inv, "salas_info": salas_info, "termo": termo})


@login_required
@user_passes_test(is_visit_user)
def buscar_global(request):
    inv = _inventario_ativo()
    q = (request.POST.get("q") or request.GET.get("q") or "").strip()
    bem = None
    msg = ""
    if q:
        try:
            bem = Bem.objects.get(tombamento=q)
        except Bem.DoesNotExist:
            msg = "Tombamento nÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â£o encontrado."

    if request.method == "POST" and request.POST.get("acao") == "puxar" and bem:
        raw = (request.POST.get("sala_id") or "").strip()
        raw = raw.replace(".", "").replace(" ", "")
        sala_dest = get_object_or_404(Sala, id=int(raw))
        if bem.tipo != "LIVRO" and inv:
            # uma vistoria por bem no inventÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡rio vigente: cria se nÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â£o existe; senÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â£o atualiza p/ divergente
            v_last = (
                Vistoria.objects.filter(inventario=inv, bem=bem)
                .order_by("-criado_em").first()
            )
            if v_last:
                v_last.sala_encontrada = sala_dest
                v_last.vistoriador = request.user
                v_last.status = Vistoria.Status.DIVERGENTE
                v_last.save()
            else:
                v = Vistoria(
                    inventario=inv, bem=bem,
                    sala_encontrada=sala_dest, vistoriador=request.user,
                    status=Vistoria.Status.DIVERGENTE
                )
                v._new_foto_uploaded = False
                v.save()
        return redirect("mobile_sala_detail", sala_id=sala_dest.id)

    salas = Sala.objects.all().order_by("nome")
    salas_data = list(salas.values("id", "nome", "bloco"))
    return render(
        request,
        "mobile/busca_global.html",
        {"inventario": inv, "q": q, "bem": bem, "msg": msg, "salas": salas, "salas_data": salas_data},
    )


@login_required
@user_passes_test(is_visit_user)
def sala_detail(request, sala_id):
    inv = _inventario_ativo()
    sala = get_object_or_404(Sala, id=sala_id)

    bens_oficiais = Bem.objects.filter(sala_oficial=sala, tipo="BEM", ativo=True).order_by("tombamento")
    mapa = _status_corrente_por_bem(inv, bens_oficiais)
    for b in bens_oficiais:
        setattr(b, "v_atual", mapa.get(b.id))

    v_extras_qs = (
        Vistoria.objects.filter(inventario=inv, status=Vistoria.Status.DIVERGENTE, sala_encontrada=sala)
        .select_related("bem", "bem__sala_oficial")
        .order_by("bem_id", "-criado_em")
        if inv else Vistoria.objects.none()
    )
    extras_seen = set()
    extras = []
    for v in v_extras_qs:
        if v.bem_id in extras_seen:
            continue
        extras_seen.add(v.bem_id)
        if v.bem.sala_oficial_id != sala.id and v.bem.tipo == "BEM" and v.bem.ativo:
            extras.append(v)

    return render(
        request,
        "mobile/sala_detail.html",
        {"inventario": inv, "sala": sala, "bens": bens_oficiais, "extras": extras},
    )


@login_required
@user_passes_test(is_visit_user)
def buscar_tombamento(request, sala_id):
    inv = _inventario_ativo()
    sala = get_object_or_404(Sala, id=sala_id)
    q = (request.POST.get("q") or "").strip()
    bem = None
    msg = ""
    if q:
        try:
            bem = Bem.objects.get(tombamento=q)
        except Bem.DoesNotExist:
            msg = "Tombamento nÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â£o encontrado. Cadastre como 'Sem Registro'."
    return render(request, "mobile/busca.html", {"inventario": inv, "sala": sala, "q": q, "bem": bem, "msg": msg})


@login_required
@user_passes_test(is_visit_user)
def puxar_para_sala(request, sala_id):
    inv = _inventario_ativo()
    sala = get_object_or_404(Sala, id=sala_id)
    if request.method != "POST":
        return redirect("mobile_sala_detail", sala_id=sala.id)
    bem = get_object_or_404(Bem, id=request.POST.get("bem_id"))
    if bem.tipo != "LIVRO" and inv:
        v_last = (
            Vistoria.objects.filter(inventario=inv, bem=bem)
            .order_by("-criado_em").first()
        )
        if v_last:
            v_last.sala_encontrada = sala
            v_last.vistoriador = request.user
            v_last.status = Vistoria.Status.DIVERGENTE
            v_last.save()
        else:
            v = Vistoria(
                inventario=inv, bem=bem,
                sala_encontrada=sala, vistoriador=request.user,
                status=Vistoria.Status.DIVERGENTE
            )
            v._new_foto_uploaded = False
            v.save()
    return redirect("mobile_sala_detail", sala_id=sala.id)


@login_required
@user_passes_test(is_visit_user)
def bem_acao(request, bem_id):
    from inventarios.models import Vistoria
    from patrimonio.models import Bem, Sala

    inv = _inv_ativo()
    bem = get_object_or_404(Bem, id=bem_id)
    sala_padrao = getattr(bem, "sala_oficial", None)
    estado_padrao = _estado_from_bem(bem)
    resp_padrao = _resp_from_bem(bem)

    vistoria = Vistoria.objects.filter(inventario=inv, bem=bem).first()

    if request.method == "POST":
        sala_id = request.POST.get("sala_encontrada_id") or request.POST.get("sala_encontrada") or ""
        sala_id = int(sala_id) if str(sala_id).isdigit() else None
        sala_obj = Sala.objects.filter(id=sala_id).first() if sala_id else (vistoria.sala_encontrada if vistoria else sala_padrao)

        estado = (request.POST.get("estado_encontrado") or "").strip() or (vistoria.estado_encontrado if vistoria else "")
        resp   = (request.POST.get("responsavel_encontrado") or "").strip() or (vistoria.responsavel_encontrado if vistoria else "")
        obs    = (request.POST.get("observacao") or "").strip()

        btn = request.POST.get("acao") or "salvar"
        if btn == "nao_localizado":
            status = Vistoria.Status.NAO_LOCALIZADO
        elif btn == "conferido":
            if sala_obj is None: sala_obj = sala_padrao
            if not estado: estado = estado_padrao
            if not resp: resp = resp_padrao
            status = Vistoria.Status.CONFERIDO
        else:
            divergente = False
            if sala_obj and getattr(bem, "sala_oficial_id", None) and sala_obj.id != bem.sala_oficial_id:
                divergente = True
            if (estado and estado_padrao and estado != estado_padrao):
                divergente = True
            if (resp and resp_padrao and resp != resp_padrao):
                divergente = True
            status = Vistoria.Status.DIVERGENTE if divergente else Vistoria.Status.CONFERIDO

        foto = request.FILES.get("foto")
        if vistoria:
            vistoria.sala_encontrada = sala_obj
            vistoria.estado_encontrado = estado
            vistoria.responsavel_encontrado = resp
            vistoria.observacao = obs
            vistoria.status = status
            if foto:
                vistoria.foto = foto
                setattr(vistoria, "_new_foto_uploaded", True)
            vistoria.save()
        else:
            vistoria = Vistoria(
                inventario=inv, bem=bem, sala_encontrada=sala_obj,
                estado_encontrado=estado, responsavel_encontrado=resp,
                observacao=obs, status=status
            )
            if foto:
                vistoria.foto = foto
                setattr(vistoria, "_new_foto_uploaded", True)
            vistoria.save()

        destino = request.POST.get("redir") or ""
        if destino == "sala" and (sala_obj or sala_padrao):
            return redirect("mobile_sala_detail", sala_id=(sala_obj.id if sala_obj else sala_padrao.id))
        return redirect("mobile_bem_detail", bem_id=bem.id)

    sala_ini = (vistoria.sala_encontrada if vistoria else sala_padrao)
    estado_ini = (vistoria.estado_encontrado if vistoria else estado_padrao)
    resp_ini = (vistoria.responsavel_encontrado if vistoria else resp_padrao)
    foto_obrigatoria = not (vistoria and vistoria.foto)

    return render(request, "mobile/bem_detail.html", {
        "inventario": inv, "bem": bem, "vistoria": vistoria,
        "sala_padrao": sala_padrao, "estado_padrao": estado_padrao, "resp_padrao": resp_padrao,
        "sala_ini": sala_ini, "estado_ini": estado_ini, "resp_ini": resp_ini,
        "foto_obrigatoria": foto_obrigatoria,
        "ESTADO_CHOICES": Vistoria._meta.get_field("estado_encontrado").choices,
    })
@login_required
@user_passes_test(is_visit_user)
def marcar_restantes_nl(request, sala_id):
    inv = _inventario_ativo()
    sala = get_object_or_404(Sala, id=sala_id)
    bens = Bem.objects.filter(sala_oficial=sala, tipo="BEM", ativo=True)
    mapa = _status_corrente_por_bem(inv, bens)
    for b in bens:
        v = mapa.get(b.id)
        if not v or v.status not in (
            Vistoria.Status.CONFERIDO, Vistoria.Status.DIVERGENTE, Vistoria.Status.NAO_LOCALIZADO
        ):
            # cria apenas se nÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â£o existe vigente
            if not v:
                Vistoria.objects.create(
                    inventario=inv, bem=b, sala_encontrada=sala, vistoriador=request.user,
                    status=Vistoria.Status.NAO_LOCALIZADO
                )
    return redirect("mobile_sala_detail", sala_id=sala.id)


@login_required
@user_passes_test(is_visit_user)
def sem_registro(request, sala_id):
    inv = _inventario_ativo()
    sala = get_object_or_404(Sala, id=sala_id)
    if request.method == "POST" and inv:
        tomb = (request.POST.get("tombamento") or "").strip()
        desc = (request.POST.get("descricao") or "").strip()
        ns = (request.POST.get("numero_serie") or "").strip()
        foto = request.FILES.get("foto")
        SemRegistro.objects.create(
            inventario=inv, sala_encontrada=sala, vistoriador=request.user,
            tombamento_informado=tomb, descricao=desc, numero_serie=ns, foto=foto
        )
        return redirect("mobile_sala_detail", sala_id=sala.id)
    return render(request, "mobile/sem_registro.html", {"inventario": inv, "sala": sala})
@login_required
def api_salas(request):
    from patrimonio.models import Sala
    q = (request.GET.get("q") or "").strip()
    qs = Sala.objects.all()
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(nome__icontains=q) | Q(bloco__icontains=q))
    qs = qs.order_by("nome")[:20]
    data = [{"id": s.id, "label": f"{s.nome} ({s.bloco})" if s.bloco else s.nome} for s in qs]
    return JsonResponse({"results": data})