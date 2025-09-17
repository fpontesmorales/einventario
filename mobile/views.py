from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
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
    vqs = (Vistoria.objects.filter(inventario=inv, bem__in=bens_qs)
           .select_related("bem", "sala_encontrada")
           .order_by("bem_id", "-criado_em"))
    seen = set()
    for v in vqs:
        if v.bem_id in seen: 
            continue
        seen.add(v.bem_id)
        mapa[v.bem_id] = v
    return mapa

@login_required
@user_passes_test(is_visit_user)
def home(request):
    inv = _inventario_ativo()
    termo = (request.GET.get("s") or "").strip()
    salas_qs = Sala.objects.all()
    if termo:
        from django.db.models import Q
        salas_qs = salas_qs.filter(Q(nome__icontains=termo) | Q(bloco__icontains=termo))
    salas_info = []
    for sala in salas_qs:
        bens = Bem.objects.filter(sala_oficial=sala, tipo="BEM")
        total = bens.count()
        mapa = _status_corrente_por_bem(inv, bens)
        vist_ok = sum(1 for v in mapa.values() if v.status in (Vistoria.Status.CONFERIDO, Vistoria.Status.DIVERGENTE))
        salas_info.append({"sala": sala, "total": total, "vistoriados": vist_ok, "restantes": max(total - vist_ok, 0)})
    salas_info.sort(key=lambda x: x["restantes"], reverse=True)
    return render(request, "mobile/index.html", {"inventario": inv, "salas_info": salas_info, "termo": termo})

@login_required
@user_passes_test(is_visit_user)
def buscar_global(request):
    inv = _inventario_ativo()
    q = (request.POST.get("q") or request.GET.get("q") or "").strip()
    bem = None; msg = ""
    if q:
        try:
            bem = Bem.objects.get(tombamento=q)
        except Bem.DoesNotExist:
            msg = "Tombamento não encontrado."
    if request.method == "POST" and request.POST.get("acao") == "puxar" and bem:

        sala_id = request.POST.get("sala_id")
        sala_dest = get_object_or_404(Sala, id=sala_id)
        if bem.tipo != "LIVRO" and inv:
            Vistoria.objects.create(inventario=inv, bem=bem, sala_encontrada=sala_dest, vistoriador=request.user, status=Vistoria.Status.DIVERGENTE)
        return redirect("mobile_sala_detail", sala_id=sala_dest.id)
    salas = Sala.objects.all().order_by("nome")
    return render(request, "mobile/busca_global.html", {"inventario": inv, "q": q, "bem": bem, "msg": msg, "salas": salas})

@login_required
@user_passes_test(is_visit_user)
def sala_detail(request, sala_id):
    inv = _inventario_ativo()
    sala = get_object_or_404(Sala, id=sala_id)
    bens_oficiais = Bem.objects.filter(sala_oficial=sala, tipo="BEM").order_by("tombamento")
    mapa = _status_corrente_por_bem(inv, bens_oficiais)
    for b in bens_oficiais:
        setattr(b, "v_atual", mapa.get(b.id))
    from django.db.models import Q
    v_extras_qs = (Vistoria.objects.filter(inventario=inv, status=Vistoria.Status.DIVERGENTE, sala_encontrada=sala)
                   .select_related("bem", "bem__sala_oficial")
                   .order_by("bem_id", "-criado_em")) if inv else Vistoria.objects.none()
    extras_seen = set(); extras = []
    for v in v_extras_qs:
        if v.bem_id in extras_seen: continue
        extras_seen.add(v.bem_id)
        if v.bem.sala_oficial_id != sala.id and v.bem.tipo == "BEM":
            extras.append(v)
    return render(request, "mobile/sala_detail.html", {"inventario": inv, "sala": sala, "bens": bens_oficiais, "extras": extras})

@login_required
@user_passes_test(is_visit_user)
def buscar_tombamento(request, sala_id):
    inv = _inventario_ativo()
    sala = get_object_or_404(Sala, id=sala_id)
    q = (request.POST.get("q") or "").strip()
    bem = None; msg = ""
    if q:
        try:
            bem = Bem.objects.get(tombamento=q)
        except Bem.DoesNotExist:
            msg = "Tombamento não encontrado. Cadastre como 'Sem Registro'."
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
        Vistoria.objects.create(inventario=inv, bem=bem, sala_encontrada=sala, vistoriador=request.user, status=Vistoria.Status.DIVERGENTE)
    return redirect("mobile_sala_detail", sala_id=sala.id)

@login_required
@user_passes_test(is_visit_user)
def bem_acao(request, bem_id):
    inv = _inventario_ativo()
    bem = get_object_or_404(Bem, id=bem_id, tipo="BEM")
    sala_atual_id = request.GET.get("sala") or request.POST.get("sala")
    sala_atual = get_object_or_404(Sala, id=sala_atual_id) if sala_atual_id else bem.sala_oficial
    # última vistoria (para exibir no detalhe)
    v_last = None
    if inv:
        v_last = (Vistoria.objects.filter(inventario=inv, bem=bem)
                  .select_related("sala_encontrada","vistoriador")
                  .order_by("-criado_em").first())
    if request.method == "POST" and inv:
        status = request.POST.get("status")
        obs = (request.POST.get("observacao") or "").strip()
        foto = request.FILES.get("foto")
        sala_encontrada_id = request.POST.get("sala_encontrada") or sala_atual.id

        sala_encontrada = get_object_or_404(Sala, id=sala_encontrada_id)
        final = status
        if status == Vistoria.Status.CONFERIDO and sala_encontrada_id and int(sala_encontrada_id) != (bem.sala_oficial_id or 0):
            final = Vistoria.Status.DIVERGENTE
        Vistoria.objects.create(inventario=inv, bem=bem, sala_encontrada=sala_encontrada, vistoriador=request.user, status=final, observacao=obs, foto=foto)
        return redirect("mobile_sala_detail", sala_id=sala_atual.id)
    return render(request, "mobile/bem_detail.html", {"inventario": inv, "bem": bem, "sala_atual": sala_atual, "v_last": v_last})

@login_required
@user_passes_test(is_visit_user)
def marcar_restantes_nl(request, sala_id):
    inv = _inventario_ativo()
    sala = get_object_or_404(Sala, id=sala_id)
    bens = Bem.objects.filter(sala_oficial=sala, tipo="BEM")
    mapa = _status_corrente_por_bem(inv, bens)
    for b in bens:
        v = mapa.get(b.id)
        if not v or v.status not in (Vistoria.Status.CONFERIDO, Vistoria.Status.DIVERGENTE, Vistoria.Status.NAO_LOCALIZADO):
            Vistoria.objects.create(inventario=inv, bem=b, sala_encontrada=sala, vistoriador=request.user, status=Vistoria.Status.NAO_LOCALIZADO)
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
        SemRegistro.objects.create(inventario=inv, sala_encontrada=sala, vistoriador=request.user, tombamento_informado=tomb, descricao=desc, numero_serie=ns, foto=foto)
        return redirect("mobile_sala_detail", sala_id=sala.id)
    return render(request, "mobile/sem_registro.html", {"inventario": inv, "sala": sala})
