from django.contrib import admin
from django.utils.html import format_html
from .models import Inventario, Importacao, ImportacaoItem, Vistoria, SemRegistro

@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = ("ano", "ativo")
    list_filter = ("ativo",)
    search_fields = ("ano",)

class ImportacaoItemInline(admin.TabularInline):
    model = ImportacaoItem
    extra = 0
    can_delete = False
    readonly_fields = ("tombamento", "acao", "diff")
    fields = ("tombamento", "acao", "diff")

@admin.register(Importacao)
class ImportacaoAdmin(admin.ModelAdmin):
    list_display = ("id","criado_em","usuario","aplicado","novos","atualizados","movidos","baixados","reativados","sem_mudanca","ausentes")
    list_filter = ("aplicado","criado_em","usuario")
    date_hierarchy = "criado_em"
    inlines = [ImportacaoItemInline]
    readonly_fields = ("criado_em","usuario","arquivo_nome","aplicado","novos","atualizados","movidos","baixados","reativados","sem_mudanca","ausentes")

@admin.register(Vistoria)
class VistoriaAdmin(admin.ModelAdmin):
    list_display = ("id","bem_tomb","bem_desc","inventario","status","sala_encontrada","mini","criado_em")
    list_filter = ("inventario","status","sala_encontrada","vistoriador")
    search_fields = ("bem__tombamento","bem__descricao","responsavel_encontrado","observacao")
    readonly_fields = ("mini",)
    autocomplete_fields = ("bem","sala_encontrada","vistoriador")
    ordering = ("bem__tombamento","-criado_em")
    list_per_page = 50
    date_hierarchy = "criado_em"

    def mini(self, obj):
        if obj.foto:
            return format_html('<img src="{}" style="max-width:240px;border-radius:6px;">', obj.foto.url)
        return "-"
    mini.short_description = "Foto"

    def bem_tomb(self, obj):
        return getattr(obj.bem, "tombamento", "")
    bem_tomb.short_description = "Tombamento"
    bem_tomb.admin_order_field = "bem__tombamento"

    def bem_desc(self, obj):
        return getattr(obj.bem, "descricao", "")
    bem_desc.short_description = "Descrição"
    bem_desc.admin_order_field = "bem__descricao"

@admin.register(SemRegistro)
class SemRegistroAdmin(admin.ModelAdmin):
    list_display = ("id","inventario","sala_encontrada","descricao","mini","criado_em")
    list_filter = ("inventario","sala_encontrada")
    search_fields = ("descricao","tombamento_informado","numero_serie")
    readonly_fields = ("mini",)
    def mini(self, obj):
        if obj.foto:
            return format_html('<img src="{}" style="max-width:240px;border-radius:6px;">', obj.foto.url)
        return "-"
    mini.short_description = "Foto"