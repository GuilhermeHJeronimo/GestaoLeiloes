from django.contrib import admin
from .models import Comitente, Veiculo, Leilao, Visita, Arremate
def formatar_moeda(valor):
    """Formata um valor para o padrão de moeda brasileiro R$."""
    if not valor:
        return "R$ 0,00"
    try:
        valor_str = str(valor)
        if ',' in valor_str:
            valor_str = valor_str.replace('.', '').replace(',', '.')
        valor_numerico = float(valor_str)
        return f"R$ {valor_numerico:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return valor

# --- Configurações de exibição para cada modelo ---

class ArremateAdmin(admin.ModelAdmin):
    list_display = ('veiculo', 'leilao', 'nome_cliente', 'cpf_cliente', 'valor_arremate_formatado', 'data_arremate')
    search_fields = ('veiculo__placa', 'veiculo__min_veiculo', 'nome_cliente', 'cpf_cliente')
    list_filter = ('leilao',)
    
    @admin.display(description='Valor do Arremate', ordering='valor_arremate')
    def valor_arremate_formatado(self, obj):
        return formatar_moeda(obj.valor_arremate)

class LeilaoAdmin(admin.ModelAdmin):
    list_display = ('nome_evento', 'data_leilao_principal', 'id_leilao_principal')
    search_fields = ('nome_evento', 'id_leilao_principal')

class VisitaAdmin(admin.ModelAdmin):
    list_display = ('leilao', 'cpf_cliente', 'nome_cliente', 'data_visita')
    search_fields = ('cpf_cliente', 'nome_cliente', 'leilao__nome_evento')
    list_filter = ('leilao',)

class VeiculoAdmin(admin.ModelAdmin):
    list_display = ('lote', 'min_veiculo', 'placa', 'fipe_formatado', 'comitente', 'status', 'lance_inicial_formatado')
    search_fields = ('placa', 'min_veiculo', 'lote')
    list_filter = ('status', 'comitente')
    ordering = ('lote',)

    @admin.display(description='Lance Inicial', ordering='lance_inicial')
    def lance_inicial_formatado(self, obj):
        return formatar_moeda(obj.lance_inicial)

    @admin.display(description='Valor FIPE', ordering='proporcao_fipe')
    def fipe_formatado(self, obj):
        return formatar_moeda(obj.proporcao_fipe)

# --- Registros ---
admin.site.register(Comitente)
admin.site.register(Veiculo, VeiculoAdmin)
admin.site.register(Leilao, LeilaoAdmin)
admin.site.register(Visita, VisitaAdmin)
admin.site.register(Arremate, ArremateAdmin)