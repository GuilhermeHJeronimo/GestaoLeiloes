from django.db import models
from django.utils import timezone

# Modelo Veiculo agora é um "catálogo" geral de veículos que podem existir.
class Veiculo(models.Model):
    placa = models.CharField(max_length=10, unique=True, primary_key=True)
    min_veiculo = models.CharField(max_length=255, verbose_name="Descrição do Veículo")
    # Podemos adicionar outros dados fixos do veículo aqui, como ano, modelo, cor, etc.

    def __str__(self):
        return f"{self.min_veiculo} ({self.placa})"

class Comitente(models.Model):
    nome = models.CharField(max_length=255, unique=True)
    def __str__(self): return self.nome

class Leilao(models.Model):
    nome_evento = models.CharField(max_length=255, verbose_name="Nome do Evento")
    data_leilao_principal = models.DateField(verbose_name="Data Leilão Principal")
    # ... (outros campos do leilão)

    def __str__(self): return self.nome_evento

# --- NOVO MODELO CENTRAL: LOTE ---
class Lote(models.Model):
    STATUS_CHOICES = [
        ('DISPONIVEL', 'Disponível'),
        ('ARREMATADO', 'Arrematado'),
        ('PAGAMENTO_CONFIRMADO', 'Pagamento Confirmado'),
        ('RETIRADO', 'Retirado'),
        ('RETORNADO', 'Retornado com Multa'),
    ]
    
    leilao = models.ForeignKey(Leilao, on_delete=models.CASCADE, related_name='lotes')
    veiculo = models.ForeignKey(Veiculo, on_delete=models.CASCADE, related_name='aparicoes_em_lote')
    comitente = models.ForeignKey(Comitente, on_delete=models.PROTECT, related_name='lotes')
    
    numero_lote = models.PositiveIntegerField(verbose_name="Número do Lote")
    lance_inicial = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    proporcao_fipe = models.CharField(max_length=20, verbose_name="Valor FIPE", blank=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='DISPONIVEL')

    class Meta:
        # Garante que um mesmo veículo não possa ter o mesmo número de lote no mesmo leilão.
        unique_together = ('leilao', 'numero_lote')
        ordering = ['numero_lote']

    def __str__(self):
        return f"Lote {self.numero_lote} ({self.veiculo.placa}) no Leilão '{self.leilao.nome_evento}'"


class Visita(models.Model):
    leilao = models.ForeignKey(Leilao, on_delete=models.CASCADE, related_name="visitas")
    cpf_cliente = models.CharField(max_length=18, verbose_name="CPF/CNPJ do Cliente")
    nome_cliente = models.CharField(max_length=255, verbose_name="Nome do Cliente", blank=True, null=True)
    data_visita = models.DateTimeField(auto_now_add=True, verbose_name="Data e Hora da Visita")
    def __str__(self): return f"Visita de {self.cpf_cliente} ao leilão '{self.leilao.nome_evento}'"

# --- MODELO ARREMATE ATUALIZADO ---
class Arremate(models.Model):
    # Agora um arremate está ligado a um LOTE específico, não a um VEÍCULO genérico.
    lote = models.OneToOneField(Lote, on_delete=models.CASCADE, related_name="arremate")
    cpf_cliente = models.CharField(max_length=18, verbose_name="CPF/CNPJ do Cliente")
    nome_cliente = models.CharField(max_length=255, verbose_name="Nome do Cliente", blank=True, null=True)
    valor_arremate = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor do Arremate")
    data_arremate = models.DateTimeField(verbose_name="Data do Arremate", default=timezone.now)

    def __str__(self):
        return f"Arremate do {self.lote} por {self.nome_cliente}"