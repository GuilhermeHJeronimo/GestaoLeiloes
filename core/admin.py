from django.contrib import admin, messages
from django.shortcuts import redirect
from .models import Comitente, Veiculo, Leilao, Visita, Arremate

# --- FUNÇÃO AUXILIAR REUTILIZÁVEL ---
def formatar_moeda(valor):
    """Formata um valor (seja número ou texto) para o padrão de moeda brasileiro R$."""
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

# --- AÇÕES CUSTOMIZADAS PARA O ADMIN ---

@admin.action(description="Reverter status para 'Aguardando Pagamento (Arrematado)'")
def reverter_para_arrematado(modeladmin, request, queryset):
    # Ação permitida apenas para veículos que já passaram deste status
    queryset = queryset.filter(status__in=['PAGAMENTO_CONFIRMADO', 'RETIRADO'])
    updated_count = queryset.update(status='ARREMATADO')
    messages.success(request, f"{updated_count} veículo(s) teve(iveram) seu status revertido para 'Arrematado'.")

@admin.action(description="Reverter status para 'Pagamento Confirmado'")
def reverter_para_pago(modeladmin, request, queryset):
    # Ação permitida apenas para veículos que já passaram deste status
    queryset = queryset.filter(status__in=['RETIRADO'])
    updated_count = queryset.update(status='PAGAMENTO_CONFIRMADO')
    messages.success(request, f"{updated_count} veículo(s) teve(iveram) seu status revertido para 'Pagamento Confirmado'.")


# --- CONFIGURAÇÕES DE EXIBIÇÃO PARA CADA MODELO ---

class ComitenteAdmin(admin.ModelAdmin):
    search_fields = ('nome',)

    def response_add(self, request, obj, post_url_continue=None):
        messages.success(request, f"O comitente '{obj.nome}' foi adicionado com sucesso.")
        return redirect('dashboard')

class LeilaoAdmin(admin.ModelAdmin):
    list_display = ('nome_evento', 'data_leilao_principal', 'id_leilao_principal')
    search_fields = ('nome_evento', 'id_leilao_principal')

    def response_add(self, request, obj, post_url_continue=None):
        messages.success(request, f"O leilão '{obj.nome_evento}' foi adicionado com sucesso.")
        return redirect('dashboard')

class VisitaAdmin(admin.ModelAdmin):
    list_display = ('leilao', 'cpf_cliente', 'nome_cliente', 'data_visita')
    search_fields = ('cpf_cliente', 'nome_cliente', 'leilao__nome_evento')
    list_filter = ('leilao',)

    def response_add(self, request, obj, post_url_continue=None):
        messages.success(request, "A visita foi registrada com sucesso.")
        return redirect('dashboard')

class ArremateAdmin(admin.ModelAdmin):
    list_display = ('veiculo', 'leilao', 'nome_cliente', 'cpf_cliente', 'valor_arremate_formatado', 'data_arremate')
    search_fields = ('veiculo__placa', 'veiculo__min_veiculo', 'nome_cliente', 'cpf_cliente')
    list_filter = ('leilao',)
    
    @admin.display(description='Valor do Arremate', ordering='valor_arremate')
    def valor_arremate_formatado(self, obj):
        return formatar_moeda(obj.valor_arremate)

    def response_add(self, request, obj, post_url_continue=None):
        messages.success(request, f"O arremate para o veículo '{obj.veiculo.placa}' foi adicionado com sucesso.")
        return redirect('dashboard')

class VeiculoAdmin(admin.ModelAdmin):
    list_display = ('lote', 'min_veiculo', 'placa', 'fipe_formatado', 'comitente', 'status', 'lance_inicial_formatado')
    search_fields = ('placa', 'min_veiculo', 'lote')
    list_filter = ('status', 'comitente')
    ordering = ('lote',)
    actions = [reverter_para_arrematado, reverter_para_pago]

    @admin.display(description='Lance Inicial', ordering='lance_inicial')
    def lance_inicial_formatado(self, obj):
        return formatar_moeda(obj.lance_inicial)

    @admin.display(description='Valor FIPE', ordering='proporcao_fipe')
    def fipe_formatado(self, obj):
        return formatar_moeda(obj.proporcao_fipe)

# --- REGISTROS FINAIS ---
admin.site.register(Comitente, ComitenteAdmin)
admin.site.register(Veiculo, VeiculoAdmin)
admin.site.register(Leilao, LeilaoAdmin)
admin.site.register(Visita, VisitaAdmin)
admin.site.register(Arremate, ArremateAdmin)