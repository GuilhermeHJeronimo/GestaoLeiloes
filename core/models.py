from django.db import models

# Modelo para o Vendedor/Dono do Veículo
class Comitente(models.Model):
    nome = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.nome

# Modelo para o Veículo, com a estrutura simplificada
class Veiculo(models.Model):
    STATUS_CHOICES = [
        ('DISPONIVEL', 'Disponível'),
        ('ARREMATADO', 'Arrematado'),
        ('PAGO', 'Pagamento Confirmado'),
        ('RETIRADO', 'Retirado'),
        ('RETORNADO', 'Retornado com Multa'),
    ]

    lote = models.PositiveIntegerField()
    min_veiculo = models.CharField(max_length=255, verbose_name="Veículo")
    comitente = models.ForeignKey(Comitente, on_delete=models.PROTECT, related_name='veiculos')
    lance_inicial = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    proporcao_fipe = models.CharField(max_length=20, verbose_name="Valor FIPE", blank=True)
    placa = models.CharField(max_length=10, unique=True, primary_key=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DISPONIVEL')

    def __str__(self):
        return f"Lote {self.lote}: {self.min_veiculo} - Placa: {self.placa}"

    class Meta:
        ordering = ['lote']

# Modelo para o Evento de Leilão
class Leilao(models.Model):
    nome_evento = models.CharField(max_length=255, verbose_name="Nome do Evento")
    data_leilao_principal = models.DateField(verbose_name="Data Leilão Principal")
    id_leilao_principal = models.CharField(max_length=50, verbose_name="ID Leilão Principal")
    data_leilao_repasse = models.DateField(verbose_name="Data Leilão Repasse")
    id_leilao_repasse = models.CharField(max_length=50, verbose_name="ID Leilão Repasse")
    
    def __str__(self):
        return self.nome_evento

# Modelo para o Registro de Visita
class Visita(models.Model):
    leilao = models.ForeignKey(Leilao, on_delete=models.CASCADE, related_name="visitas")
    cpf_cliente = models.CharField(max_length=14, verbose_name="CPF do Cliente")
    nome_cliente = models.CharField(max_length=255, verbose_name="Nome do Cliente", blank=True, null=True)
    data_visita = models.DateTimeField(auto_now_add=True, verbose_name="Data e Hora da Visita")

    def __str__(self):
        return f"Visita de {self.cpf_cliente} ao leilão '{self.leilao.nome_evento}'"

# Modelo para o Registro de Arremate
class Arremate(models.Model):
    veiculo = models.OneToOneField(Veiculo, on_delete=models.CASCADE, related_name="arremate")
    leilao = models.ForeignKey(Leilao, on_delete=models.PROTECT, related_name="arremates")
    cpf_cliente = models.CharField(max_length=14, verbose_name="CPF do Cliente")
    nome_cliente = models.CharField(max_length=255, verbose_name="Nome do Cliente", blank=True, null=True)
    valor_arremate = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor do Arremate")
    data_arremate = models.DateTimeField(auto_now_add=True, verbose_name="Data do Arremate")

    def __str__(self):
        return f"Arremate de {self.veiculo.min_veiculo} por {self.nome_cliente}"