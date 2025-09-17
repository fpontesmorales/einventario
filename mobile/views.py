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
    if t.startswith(("ót", "ot")):
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
            msg = "Tombamento não encontrado."

    if request.method == "POST" and request.POST.get("acao") == "puxar" and bem:
        raw = (request.POST.get("sala_id") or "").strip()
        raw = raw.replace(".", "").replace(" ", "")
        sala_dest = get_object_or_404(Sala, id=int(raw))
        if bem.tipo != "LIVRO" and inv:
            # uma vistoria por bem no inventário vigente: cria se não existe; senão atualiza p/ divergente
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
    inv = _inventario_ativo()
    bem = get_object_or_404(Bem, id=bem_id, tipo="BEM", ativo=True)
    sala_atual_id = request.GET.get("sala") or request.POST.get("sala")
    sala_atual = get_object_or_404(Sala, id=sala_atual_id) if sala_atual_id else bem.sala_oficial

    # vistoria vigente (se existir)
    v_last = None
    if inv:
        v_last = (
            Vistoria.objects.filter(inventario=inv, bem=bem)
            .select_related("sala_encontrada", "vistoriador")
            .order_by("-criado_em")
            .first()
        )

    if request.method == "POST" and inv:
        status = request.POST.get("status")  # "CONFERIDO" ou "NAO_LOCALIZADO"
        obs = (request.POST.get("observacao") or "").strip()

        sala_raw = (request.POST.get("sala_encontrada") or str(sala_atual.id)).replace(".", "").replace(" ", "")
        sala_encontrada = get_object_or_404(Sala, id=int(sala_raw))

        foto = request.FILES.get("foto")
        estado = (request.POST.get("estado_encontrado") or "").strip()
        resp = (request.POST.get("responsavel_encontrado") or "").strip()

        estado_cadastro = _estado_from_bem(bem)

        # Foto obrigatória para CONFERIDO apenas se NÃO há foto na vistoria vigente
        if status == Vistoria.Status.CONFERIDO:
            tem_foto_previa = bool(v_last and v_last.foto)
            if not tem_foto_previa and not foto:
                salas = Sala.objects.all().order_by("nome")
                return render(
                    request, "mobile/bem_detail.html",
                    {
                        "inventario": inv, "bem": bem, "sala_atual": sala_atual, "v_last": v_last,
                        "salas": salas, "sala_sel": sala_encontrada, "sala_sel_label": _sala_label(sala_encontrada),
                        "estado_init": estado or estado_cadastro, "resp_init": resp or _resp_from_bem(bem),
                        "salas_data": list(salas.values("id", "nome", "bloco")),
                        "erro": "A foto é obrigatória para Conferido (não há foto anterior neste inventário).",
                    },
                )
            if not estado:
                salas = Sala.objects.all().order_by("nome")
                return render(
                    request, "mobile/bem_detail.html",
                    {
                        "inventario": inv, "bem": bem, "sala_atual": sala_atual, "v_last": v_last,
                        "salas": salas, "sala_sel": sala_encontrada, "sala_sel_label": _sala_label(sala_encontrada),
                        "estado_init": estado or estado_cadastro, "resp_init": resp or _resp_from_bem(bem),
                        "salas_data": list(salas.values("id", "nome", "bloco")),
                        "erro": "Selecione o estado do bem.",
                    },
                )

        # Divergência automática por sala/estado quando Conferido
        final = status
        if status == Vistoria.Status.CONFERIDO:
            if sala_encontrada.id != (bem.sala_oficial_id or 0):
                final = Vistoria.Status.DIVERGENTE
            elif estado and estado_cadastro and estado != estado_cadastro:
                final = Vistoria.Status.DIVERGENTE

        # ==== ATUALIZA A VISTORIA VIGENTE (ou cria se não existir) ====
        if v_last:
            v_last.sala_encontrada = sala_encontrada
            v_last.vistoriador = request.user
            v_last.status = final
            v_last.estado_encontrado = estado
            v_last.responsavel_encontrado = resp
            v_last.observacao = obs
            if foto:
                v_last.foto = foto
                v_last._new_foto_uploaded = True  # dica para o model salvar a marca d'água
            v_last.save()
        else:
            v = Vistoria(
                inventario=inv, bem=bem, sala_encontrada=sala_encontrada,
                vistoriador=request.user, status=final,
                estado_encontrado=estado, responsavel_encontrado=resp, observacao=obs,
            )
            if foto:
                v.foto = foto
                v._new_foto_uploaded = True
            v.save()

        return redirect("mobile_sala_detail", sala_id=sala_atual.id)

    # GET: defaults (sem vistoria vigente → puxa do Bem)
    salas = Sala.objects.all().order_by("nome")
    sala_sel = v_last.sala_encontrada if (v_last and v_last.sala_encontrada) else sala_atual
    estado_init = v_last.estado_encontrado if v_last else _estado_from_bem(bem)
    resp_init = v_last.responsavel_encontrado if v_last else _resp_from_bem(bem)
    salas_data = list(salas.values("id", "nome", "bloco"))
    sala_sel_label = _sala_label(sala_sel)

    return render(
        request, "mobile/bem_detail.html",
        {
            "inventario": inv, "bem": bem, "sala_atual": sala_atual, "v_last": v_last,
            "salas": salas, "sala_sel": sala_sel, "sala_sel_label": sala_sel_label,
            "estado_init": estado_init, "resp_init": resp_init, "salas_data": salas_data,
        },
    )


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
            # cria apenas se não existe vigente
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