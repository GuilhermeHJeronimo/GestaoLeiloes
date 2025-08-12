import pandas as pd
from django.shortcuts import render, redirect
from django.utils import timezone
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from .models import Comitente, Veiculo, Leilao, Visita, Arremate
import math

@login_required
def upload_excel(request):
    if request.method == 'POST':
        excel_file = request.FILES.get('excel_file')
        if not excel_file:
            return render(request, 'core/upload_excel.html', {'error': 'Nenhum arquivo foi enviado.'})
        try:
            df = pd.read_excel(excel_file)
            df.columns = df.columns.str.strip()
            sucesso_count = 0
            erros = []
            for index, row in df.iterrows():
                try:
                    placa = row.get('PLACA')
                    if not placa:
                        erros.append(f"Linha {index+2}: Placa está vazia. Linha ignorada.")
                        continue
                    def clean_decimal(value):
                        if pd.isna(value): return 0.00
                        cleaned_value = str(value).replace('R$', '').strip().replace('.', '').replace(',', '.')
                        try: return float(cleaned_value)
                        except (ValueError, TypeError): return 0.00
                    lance_inicial_limpo = clean_decimal(row.get('LANCE INICIAL'))
                    comitente_nome = row.get('COMITENTES')
                    comitente, _ = Comitente.objects.get_or_create(nome=comitente_nome)
                    Veiculo.objects.update_or_create(
                        placa=placa,
                        defaults={'lote': int(row.get('LOTES', 0)), 'min_veiculo': str(row.get('VEICULOS', '')), 'comitente': comitente, 'lance_inicial': lance_inicial_limpo, 'proporcao_fipe': str(row.get('FIPE', '')), 'status': 'DISPONIVEL',})
                    sucesso_count += 1
                except Exception as e:
                    erros.append(f"Linha {index+2}: Erro inesperado. {e}")
            context = { 'success': f'{sucesso_count} veículos importados/atualizados com sucesso.', 'errors': erros }
            return render(request, 'core/upload_excel.html', context)
        except Exception as e:
            return render(request, 'core/upload_excel.html', {'error': f'Erro ao processar a planilha: {e}'})
    return render(request, 'core/upload_excel.html')

@login_required
def registrar_visita(request):
    success_message = None
    if request.method == 'POST':
        leilao_id = request.POST.get('leilao')
        cpf_cliente = request.POST.get('cpf')
        nome_cliente = request.POST.get('nome')
        leilao_selecionado = Leilao.objects.get(id=leilao_id)
        Visita.objects.create(leilao=leilao_selecionado, cpf_cliente=cpf_cliente, nome_cliente=nome_cliente)
        success_message = f"Visita de {nome_cliente} registrada com sucesso!"
    todos_os_leiloes = Leilao.objects.all().order_by('-data_leilao_principal')
    contexto = { 'leiloes': todos_os_leiloes, 'success_message': success_message }
    return render(request, 'core/registrar_visita.html', contexto)

@login_required
def selecionar_leilao_arremate(request):
    todos_os_leiloes = Leilao.objects.all().order_by('-data_leilao_principal')
    contexto = { 'leiloes': todos_os_leiloes }
    return render(request, 'core/selecionar_leilao.html', contexto)

@login_required
def lista_veiculos_leilao(request, leilao_id):
    leilao = Leilao.objects.get(id=leilao_id)
    veiculos_disponiveis = Veiculo.objects.filter(status='DISPONIVEL').order_by('lote')
    contexto = { 'leilao': leilao, 'veiculos': veiculos_disponiveis }
    return render(request, 'core/lista_veiculos.html', contexto)

@login_required
def registrar_arremate_final(request, leilao_id, placa_veiculo):
    leilao = Leilao.objects.get(id=leilao_id)
    veiculo = Veiculo.objects.get(placa=placa_veiculo)
    if request.method == 'POST':
        cpf_cliente = request.POST.get('cpf')
        nome_cliente = request.POST.get('nome')
        def clean_decimal(value):
            if pd.isna(value) or not value: return 0.00
            cleaned_value = str(value).replace('R$', '').strip().replace('.', '').replace(',', '.')
            try: return float(cleaned_value)
            except (ValueError, TypeError): return 0.00
        valor_arremate = clean_decimal(request.POST.get('valor_arremate'))
        Arremate.objects.create(veiculo=veiculo, leilao=leilao, cpf_cliente=cpf_cliente, nome_cliente=nome_cliente, valor_arremate=valor_arremate)
        veiculo.status = 'ARREMATADO'
        veiculo.save()
        return redirect('lista_veiculos_leilao', leilao_id=leilao.id)
    contexto = { 'leilao': leilao, 'veiculo': veiculo }
    return render(request, 'core/registrar_arremate_form.html', contexto)

@login_required
def dashboard(request):
    hoje = timezone.localtime().date()
    inicio_hoje = timezone.make_aware(timezone.datetime.combine(hoje, timezone.datetime.min.time()))
    fim_hoje = inicio_hoje + timezone.timedelta(days=1)
    total_veiculos_disponiveis = Veiculo.objects.filter(status='DISPONIVEL').count()
    visitas_hoje = Visita.objects.filter(data_visita__gte=inicio_hoje, data_visita__lt=fim_hoje).count()
    total_arrematado_hoje = Arremate.objects.filter(data_arremate__gte=inicio_hoje, data_arremate__lt=fim_hoje).aggregate(total=Sum('valor_arremate'))['total'] or 0.00
    top_arrematantes_query = Arremate.objects.values('cpf_cliente', 'nome_cliente').annotate(total_gasto=Sum('valor_arremate')).order_by('-total_gasto')[:5]
    top_arrematantes_formatado = []
    for arrematante in top_arrematantes_query:
        valor_formatado = f"{arrematante['total_gasto']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        top_arrematantes_formatado.append({'cpf_cliente': arrematante['cpf_cliente'], 'nome_cliente': arrematante['nome_cliente'], 'total_gasto_formatado': valor_formatado,})
    veiculos_disponiveis = Veiculo.objects.filter(status='DISPONIVEL').order_by('lote')
    veiculos_arrematados_hoje = Veiculo.objects.filter(status='ARREMATADO', arremate__data_arremate__gte=inicio_hoje).order_by('lote')
    contexto = { 'total_veiculos_disponiveis': total_veiculos_disponiveis, 'visitas_hoje': visitas_hoje, 'total_arrematado_hoje': f"{total_arrematado_hoje:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), 'top_arrematantes': top_arrematantes_formatado, 'veiculos_disponiveis': veiculos_disponiveis, 'veiculos_arrematados_hoje': veiculos_arrematados_hoje, }
    return render(request, 'core/dashboard.html', contexto)

@login_required
def lista_completa_veiculos(request):
    status_filtro = request.GET.get('status')
    lista_veiculos = Veiculo.objects.all()
    titulo_pagina = "Todos os Veículos"
    if status_filtro == 'DISPONIVEL':
        lista_veiculos = lista_veiculos.filter(status='DISPONIVEL')
        titulo_pagina = "Veículos Disponíveis"
    elif status_filtro == 'ARREMATADO':
        lista_veiculos = lista_veiculos.filter(status='ARREMATADO')
        titulo_pagina = "Veículos Arrematados"
    contexto = { 'veiculos': lista_veiculos.order_by('lote'), 'titulo_pagina': titulo_pagina, }
    return render(request, 'core/lista_completa_veiculos.html', contexto)