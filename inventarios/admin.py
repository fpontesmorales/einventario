from django.contrib import admin
from django.utils.html import format_html
from .models import Inventario, Vistoria, Importacao, ImportacaoItem, SemRegistro

@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = ("ano", "ativo")
    list_filter = ("ativo",)

@admin.register(Vistoria)
class VistoriaAdmin(admin.ModelAdmin):
    list_display = ("id","bem","inventario","status","sala_encontrada","vistoriador","criado_em","foto_thumb")
    list_filter = ("inventario","status","sala_encontrada","vistoriador")
    search_fields = ("bem__tombamento","bem__descricao")
    readonly_fields = ("criado_em","foto_preview")
    fields = ("bem","inventario","status","estado_encontrado","responsavel_encontrado","sala_encontrada","vistoriador","observacao","foto","foto_preview","criado_em")
    date_hierarchy = "criado_em"

    def foto_thumb(self, obj):
        if obj.foto:
            return format_html('<img src="{}" style="height:48px;border-radius:4px;">', obj.foto.url)
        return "-"
    foto_thumb.short_description = "Foto"

    def foto_preview(self, obj):
        if obj and obj.foto:
            return format_html('<img src="{}" style="max-width:480px;border-radius:6px;">', obj.foto.url)
        return "—"
    foto_preview.short_description = "Prévia da foto"

@admin.register(SemRegistro)
class SemRegistroAdmin(admin.ModelAdmin):
    list_display = ("inventario","sala_encontrada","tombamento_informado","descricao","vistoriador","criado_em","foto_thumb")
    list_filter = ("inventario","sala_encontrada","vistoriador")
    search_fields = ("tombamento_informado","descricao")
    readonly_fields = ("criado_em","foto_preview")
    fields = ("inventario","sala_encontrada","tombamento_informado","descricao","numero_serie","foto","foto_preview","vistoriador","criado_em")

    def foto_thumb(self, obj):
        if obj.foto:
            return format_html('<img src="{}" style="height:48px;border-radius:4px;">', obj.foto.url)
        return "-"
    def foto_preview(self, obj):
        if obj and obj.foto:
            return format_html('<img src="{}" style="max-width:480px;border-radius:6px;">', obj.foto.url)
        return "—"

@admin.register(Importacao)
class ImportacaoAdmin(admin.ModelAdmin):
    list_display = ("id","criado_em","usuario","arquivo_nome","aplicado","novos","atualizados","movidos","baixados","reativados","sem_mudanca","ausentes")
    readonly_fields = ("criado_em",)
    date_hierarchy = "criado_em"

@admin.register(ImportacaoItem)
class ImportacaoItemAdmin(admin.ModelAdmin):
    list_display = ("importacao","tombamento","acao")
    list_filter = ("acao",)
    search_fields = ("tombamento",)
