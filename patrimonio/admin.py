from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import uuid

from .models import Sala, Bem
from inventarios.forms import CSVUploadForm
from inventarios.models import Vistoria, Inventario
from patrimonio.utils_csv import importar_bens_csv, simular_bens_csv

def user_is_gestor(user):
    return getattr(user, "perfil", "") in ("GESTOR","VISTORIADOR") or user.is_superuser

class VistoriaInline(admin.TabularInline):
    model = Vistoria
    extra = 0
    fields = ("inventario","status","estado_encontrado","responsavel_encontrado","sala_encontrada","vistoriador","criado_em")
    readonly_fields = ("inventario","status","estado_encontrado","responsavel_encontrado","sala_encontrada","vistoriador","criado_em")

@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    search_fields = ("nome","bloco")
    list_display = ("nome","bloco")

@admin.register(Bem)
class BemAdmin(admin.ModelAdmin):
    inlines = [VistoriaInline]
    search_fields = ("tombamento","descricao","numero_serie","conta_contabil","fornecedor")
    list_display = ("tombamento","descricao","sala_oficial","tipo","status_original","ativo","valor_aquisicao")
    list_filter = ("tipo","ativo","sala_oficial","estado_conservacao","campus_carga")
    readonly_fields = ("info_extra",)
    change_list_template = "admin/patrimonio/bem/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("importar/", self.admin_site.admin_view(self.importar_csv_view), name="patrimonio_bem_importar"),
            path("divergencias/", self.admin_site.admin_view(self.divergencias_view), name="patrimonio_bem_divergencias"),
            path("divergencias/conciliar/", self.admin_site.admin_view(self.conciliar_view), name="patrimonio_bem_conciliar"),
        ]
        return custom + urls

    def importar_csv_view(self, request):
        if not user_is_gestor(request.user):
            return HttpResponseForbidden("Acesso restrito.")
        if request.method == "POST":
            acao = request.POST.get("acao")
            temp_path = request.POST.get("temp_path", "").strip()
            if acao == "importar" and temp_path:
                with default_storage.open(temp_path, "rb") as fh:
                    res = importar_bens_csv(fh, usuario=request.user, arquivo_nome=temp_path.split("/")[-1])
                try: default_storage.delete(temp_path)
                except Exception: pass
                messages.success(request, f"Importação aplicada. Novos: {res['novos']} | Atualizados: {res['atualizados']} | Movidos: {res['movidos']} | Baixados: {res['baixados']} | Reativados: {res['reativados']} | Sem mudança: {res['sem_mudanca']} | Ausentes: {res['ausentes']}")
                return redirect("admin:patrimonio_bem_changelist")
            form = CSVUploadForm(request.POST, request.FILES)
            if form.is_valid():
                f = form.cleaned_data["arquivo"]
                if acao == "simular":
                    nome_tmp = f"tmp_imports/{uuid.uuid4()}.csv"
                    default_storage.save(nome_tmp, ContentFile(f.read()))
                    with default_storage.open(nome_tmp, "rb") as fh:
                        res, exemplos = simular_bens_csv(fh)
                    ctx = dict(self.admin_site.each_context(request), res=res, exemplos=exemplos, temp_path=nome_tmp)
                    return render(request, "inventarios/simulacao_resultado.html", ctx)
                else:
                    res = importar_bens_csv(f, usuario=request.user, arquivo_nome=getattr(f, "name", ""))
                    messages.success(request, f"Importação aplicada. Novos: {res['novos']} | Atualizados: {res['atualizados']} | Movidos: {res['movidos']} | Baixados: {res['baixados']} | Reativados: {res['reativados']} | Sem mudança: {res['sem_mudanca']} | Ausentes: {res['ausentes']}")
                    return redirect("admin:patrimonio_bem_changelist")
        else:
            form = CSVUploadForm()
        ctx = dict(self.admin_site.each_context(request), title="Importar Bens (CSV ;)", form=form)
        return render(request, "inventarios/importar_csv.html", ctx)

    def divergencias_view(self, request):
        if not user_is_gestor(request.user):
            return HttpResponseForbidden("Acesso restrito.")
        inv = Inventario.objects.filter(ativo=True).order_by("-ano").first()
        vqs = Vistoria.objects.filter(inventario=inv, status=Vistoria.Status.DIVERGENTE).select_related("bem","sala_encontrada","bem__sala_oficial").order_by("bem_id","-criado_em")
        vistos = set(); itens = []
        for v in vqs:
            if v.bem_id in vistos: 
                continue
            vistos.add(v.bem_id)
            if v.sala_encontrada_id and v.bem.sala_oficial_id != v.sala_encontrada_id:
                itens.append(v)
        ctx = dict(self.admin_site.each_context(request), itens=itens, inventario=inv)
        return render(request, "inventarios/divergencias.html", ctx)

    def conciliar_view(self, request):
        if request.method != "POST" or not user_is_gestor(request.user):
            return HttpResponseForbidden("Acesso restrito.")
        bem_id = request.POST.get("bem_id")
        sala_id = request.POST.get("sala_id")
        b = get_object_or_404(Bem, id=bem_id)
        s = get_object_or_404(Sala, id=sala_id)
        b.sala_oficial = s
        b.save(update_fields=["sala_oficial"])
        messages.success(request, "Sala oficial atualizada.")
        return redirect("admin:patrimonio_bem_divergencias")
