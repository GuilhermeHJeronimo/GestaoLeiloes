from django.db.models.signals import pre_delete
from django.dispatch import receiver
from .models import Arremate, Veiculo

@receiver(pre_delete, sender=Arremate)
def reverter_status_veiculo_on_arremate_delete(sender, instance, **kwargs):

    try:
        # Pega o veículo associado ao arremate que está sendo deletado
        veiculo = instance.veiculo
        # Muda o status de volta para 'Disponível'
        veiculo.status = 'DISPONIVEL'
        veiculo.save()
        print(f"Status do veículo {veiculo.placa} revertido para DISPONIVEL.")
    except Veiculo.DoesNotExist:
        pass