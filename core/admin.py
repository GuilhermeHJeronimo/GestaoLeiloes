from django.contrib import admin, messages
from .models import Comitente, Veiculo, Leilao, Visita, Arremate, Lote

# --- FUNÇÕES AUXILIARES ---

def formatar_moeda(valor):
    if not valor: return "R$ 0,00"
    try:
        valor_str = str(valor)
        if ',' in valor_str: valor_str = valor_str.replace('.', '').replace(',', '.')
        valor_numerico = float(valor_str)
        return f"R$ {valor_numerico:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError): return valor

@admin.action(description="Reverter status para 'Disponível'")
def reverter_para_disponivel(modeladmin, request, queryset):
    updated_count = queryset.update(status='DISPONIVEL')
    # Também deleta o arremate associado, se houver
    for lote in queryset:
        if hasattr(lote, 'arremate'):
            lote.arremate.delete() # O sinal de delete do arremate não é mais necessário com esta abordagem
    messages.success(request, f"{updated_count} lote(s) teve(iveram) seu status revertido para 'Disponível'.")

# --- CONFIGURAÇÕES DO ADMIN ---

class ComitenteAdmin(admin.ModelAdmin):
    search_fields = ('nome',)

class VeiculoAdmin(admin.ModelAdmin):
    search_fields = ('placa', 'min_veiculo')
    list_display = ('placa', 'min_veiculo')

class LeilaoAdmin(admin.ModelAdmin):
    list_display = ('nome_evento', 'data_leilao_principal')
    search_fields = ('nome_evento',)

class VisitaAdmin(admin.ModelAdmin):
    list_display = ('leilao', 'cpf_cliente', 'nome_cliente', 'data_visita')
    search_fields = ('cpf_cliente', 'nome_cliente', 'leilao__nome_evento')
    list_filter = ('leilao',)

class LoteAdmin(admin.ModelAdmin):
    list_display = ('numero_lote', 'veiculo', 'leilao', 'comitente', 'status', 'lance_inicial_formatado')
    search_fields = ('numero_lote', 'veiculo__placa', 'veiculo__min_veiculo', 'leilao__nome_evento')
    list_filter = ('status', 'leilao', 'comitente')
    ordering = ('-leilao__data_leilao_principal', 'numero_lote')
    actions = [reverter_para_disponivel]

    @admin.display(description='Lance Inicial', ordering='lance_inicial')
    def lance_inicial_formatado(self, obj):
        return formatar_moeda(obj.lance_inicial)

class ArremateAdmin(admin.ModelAdmin):
    list_display = ('lote_info', 'nome_cliente', 'cpf_cliente', 'valor_arremate_formatado', 'data_arremate')
    search_fields = ('lote__veiculo__placa', 'lote__numero_lote', 'nome_cliente', 'cpf_cliente')
    list_filter = ('lote__leilao',)

    @admin.display(description='Lote', ordering='lote__numero_lote')
    def lote_info(self, obj):
        return str(obj.lote)

    @admin.display(description='Valor do Arremate', ordering='valor_arremate')
    def valor_arremate_formatado(self, obj):
        return formatar_moeda(obj.valor_arremate)

# --- REGISTROS FINAIS ---
admin.site.register(Comitente, ComitenteAdmin)
admin.site.register(Veiculo, VeiculoAdmin)
admin.site.register(Leilao, LeilaoAdmin)
admin.site.register(Visita, VisitaAdmin)
admin.site.register(Lote, LoteAdmin)
admin.site.register(Arremate, ArremateAdmin)