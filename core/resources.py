# Arquivo: core/resources.py
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import Veiculo, Comitente

class VeiculoResource(resources.ModelResource):
    comitente = fields.Field(column_name='Comitente', attribute='comitente', widget=ForeignKeyWidget(Comitente, 'nome'))
    status = fields.Field(column_name='Status', attribute='get_status_display')
    lance_inicial = fields.Field(column_name='Lance Inicial (R$)', attribute='lance_inicial')
    proporcao_fipe = fields.Field(column_name='Valor FIPE (R$)', attribute='proporcao_fipe')
    class Meta:
        model = Veiculo
        fields = ('lote', 'min_veiculo', 'placa', 'comitente', 'status', 'lance_inicial', 'proporcao_fipe')
        export_order = fields
        sheet_name = 'Veículos'