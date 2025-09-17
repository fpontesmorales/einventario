from django.contrib import admin
from .models import Inventario, Vistoria, Importacao, ImportacaoItem

@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = ("ano", "inicio", "fim", "ativo")
    list_editable = ("ativo",)

@admin.register(Vistoria)
class VistoriaAdmin(admin.ModelAdmin):
    list_display = ("inventario", "bem", "sala_encontrada", "vistoriador", "status", "criado_em")
    list_filter = ("inventario", "status")
    search_fields = ("bem__tombamento", "bem__descricao", "vistoriador__username")

class ImportacaoItemInline(admin.TabularInline):
    model = ImportacaoItem
    extra = 0
    readonly_fields = ("tombamento", "acao", "mudancas")

@admin.register(Importacao)
class ImportacaoAdmin(admin.ModelAdmin):
    list_display = ("id", "criado_em", "usuario", "arquivo_nome", "novos", "atualizados", "movidos", "baixados", "reativados", "sem_mudanca", "ausentes", "aplicado")
    inlines = [ImportacaoItemInline]
