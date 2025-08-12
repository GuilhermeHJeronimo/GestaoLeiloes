import pandas as pd
from django.shortcuts import render, redirect
from django.utils import timezone
from django.db.models import Sum
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import logout
from .models import Comitente, Veiculo, Leilao, Visita, Arremate
import math
from datetime import timedelta

# --- FUNÇÕES AUXILIARES E DE PERMISSÃO ---

def _clean_decimal(value):
    """Função auxiliar para limpar e converter valores monetários."""
    if pd.isna(value) or not value:
        return 0.00
    cleaned_value = str(value).replace('R$', '').strip().replace('.', '').replace(',', '.')
    try:
        return float(cleaned_value)
    except (ValueError, TypeError):
        return 0.00

def is_admin(user):
    return user.is_superuser

@login_required
def redirect_apos_login(request):
    if request.user.is_superuser:
        return redirect('dashboard')
    else:
        return redirect('dashboard_recepcao')

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

# --- VIEWS DE ADMIN (Apenas Superusuários) ---

@login_required
@user_passes_test(is_admin)
def dashboard(request):
    periodo = request.GET.get('periodo', 'hoje')
    hoje = timezone.localtime().date()
    if periodo == 'semana':
        inicio_periodo_dt = hoje - timedelta(days=6); titulo_periodo = "nos Últimos 7 dias"
    elif periodo == 'mes':
        inicio_periodo_dt = hoje.replace(day=1); titulo_periodo = "neste Mês"
    elif periodo == 'total':
        inicio_periodo_dt = None; titulo_periodo = "Desde o Início"
    else:
        inicio_periodo_dt = hoje; titulo_periodo = "Hoje"
    visitas = Visita.objects.all(); arremates = Arremate.objects.all()
    if inicio_periodo_dt:
        inicio_periodo = timezone.make_aware(timezone.datetime.combine(inicio_periodo_dt, timezone.datetime.min.time()))
        if periodo == 'hoje':
            fim_periodo = inicio_periodo + timezone.timedelta(days=1)
            visitas = visitas.filter(data_visita__gte=inicio_periodo, data_visita__lt=fim_periodo)
            arremates = arremates.filter(data_arremate__gte=inicio_periodo, data_arremate__lt=fim_periodo)
        else:
            visitas = visitas.filter(data_visita__gte=inicio_periodo); arremates = arremates.filter(data_arremate__gte=inicio_periodo)
    total_veiculos_disponiveis = Veiculo.objects.filter(status='DISPONIVEL').count()
    visitas_periodo = visitas.count()
    total_arrematado_periodo = arremates.aggregate(total=Sum('valor_arremate'))['total'] or 0.00
    top_arrematantes_query = arremates.values('cpf_cliente', 'nome_cliente').annotate(total_gasto=Sum('valor_arremate')).order_by('-total_gasto')[:5]
    top_arrematantes_formatado = []
    for arrematante in top_arrematantes_query:
        valor_formatado = f"{arrematante['total_gasto']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        top_arrematantes_formatado.append({'cpf_cliente': arrematante['cpf_cliente'], 'nome_cliente': arrematante['nome_cliente'], 'total_gasto_formatado': valor_formatado})
    veiculos_disponiveis = Veiculo.objects.filter(status='DISPONIVEL').order_by('lote')
    veiculos_arrematados_periodo = Veiculo.objects.filter(status='ARREMATADO', arremate__in=arremates).distinct().order_by('lote')
    contexto = {'total_veiculos_disponiveis': total_veiculos_disponiveis, 'visitas_periodo': visitas_periodo, 'total_arrematado_periodo': f"{total_arrematado_periodo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), 'top_arrematantes': top_arrematantes_formatado, 'veiculos_disponiveis': veiculos_disponiveis, 'veiculos_arrematados_periodo': veiculos_arrematados_periodo, 'titulo_periodo': titulo_periodo, 'periodo_selecionado': periodo, 'visitas': visitas.order_by('-data_visita'),}
    return render(request, 'core/dashboard.html', contexto)

@login_required
@user_passes_test(is_admin)
def upload_excel(request):
    if request.method == 'POST':
        excel_file = request.FILES.get('excel_file')
        if not excel_file:
            return render(request, 'core/upload_excel.html', {'error': 'Nenhum arquivo foi enviado.'})
        try:
            df = pd.read_excel(excel_file); df.columns = df.columns.str.strip()
            sucesso_count = 0; erros = []
            for index, row in df.iterrows():
                try:
                    placa = row.get('PLACA')
                    if not placa:
                        erros.append(f"Linha {index+2}: Placa está vazia. Linha ignorada."); continue
                    lance_inicial_limpo = _clean_decimal(row.get('LANCE INICIAL'))
                    comitente_nome = row.get('COMITENTES')
                    comitente, _ = Comitente.objects.get_or_create(nome=comitente_nome)
                    Veiculo.objects.update_or_create(
                        placa=placa,
                        defaults={'lote': int(row.get('LOTES', 0)), 'min_veiculo': str(row.get('VEICULOS', '')), 'comitente': comitente, 'lance_inicial': lance_inicial_limpo, 'proporcao_fipe': str(row.get('FIPE', '')), 'status': 'DISPONIVEL',})
                    sucesso_count += 1
                except Exception as e:
                    erros.append(f"Linha {index+2}: Erro inesperado. {e}")
            contexto = { 'success': f'{sucesso_count} veículos importados/atualizados com sucesso.', 'errors': erros }
            return render(request, 'core/upload_excel.html', contexto)
        except Exception as e:
            return render(request, 'core/upload_excel.html', {'error': f'Erro ao processar a planilha: {e}'})
    return render(request, 'core/upload_excel.html')

@login_required
@user_passes_test(is_admin)
def criar_leilao(request):
    if request.method == 'POST':
        nome_evento = request.POST.get('nome_evento')
        data_principal = request.POST.get('data_principal'); id_principal = request.POST.get('id_principal')
        data_repasse = request.POST.get('data_repasse'); id_repasse = request.POST.get('id_repasse')
        Leilao.objects.create(nome_evento=nome_evento, data_leilao_principal=data_principal, id_leilao_principal=id_principal, data_leilao_repasse=data_repasse, id_leilao_repasse=id_repasse)
        messages.success(request, f"Leilão '{nome_evento}' criado com sucesso!")
        return redirect('dashboard')
    return render(request, 'core/criar_leilao.html')

# --- VIEWS DA RECEPÇÃO (Qualquer usuário logado) ---

@login_required
def dashboard_recepcao(request):
    hoje = timezone.localtime().date()
    inicio_hoje = timezone.make_aware(timezone.datetime.combine(hoje, timezone.datetime.min.time()))
    fim_hoje = inicio_hoje + timezone.timedelta(days=1)
    visitantes_hoje = Visita.objects.filter(data_visita__gte=inicio_hoje, data_visita__lt=fim_hoje).order_by('-data_visita')
    contexto = {'visitantes_hoje': visitantes_hoje}
    return render(request, 'core/dashboard_recepcao.html', contexto)

@login_required
def registrar_visita(request):
    if request.method == 'POST':
        leilao_id = request.POST.get('leilao')
        cpf_cliente = request.POST.get('cpf')
        nome_cliente = request.POST.get('nome')
        leilao_selecionado = Leilao.objects.get(id=leilao_id)
        Visita.objects.create(leilao=leilao_selecionado, cpf_cliente=cpf_cliente, nome_cliente=nome_cliente)
        messages.success(request, f"Visita de {nome_cliente} registrada com sucesso!")
        return redirect('registrar_visita')
    todos_os_leiloes = Leilao.objects.all().order_by('-data_leilao_principal')
    contexto = { 'leiloes': todos_os_leiloes }
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
        cpf_cliente = request.POST.get('cpf'); nome_cliente = request.POST.get('nome')
        valor_arremate = _clean_decimal(request.POST.get('valor_arremate'))
        Arremate.objects.create(veiculo=veiculo, leilao=leilao, cpf_cliente=cpf_cliente, nome_cliente=nome_cliente, valor_arremate=valor_arremate)
        veiculo.status = 'ARREMATADO'; veiculo.save()
        return redirect('lista_veiculos_leilao', leilao_id=leilao.id)
    contexto = { 'leilao': leilao, 'veiculo': veiculo }
    return render(request, 'core/registrar_arremate_form.html', contexto)
    
@login_required
def lista_completa_veiculos(request):
    status_filtro = request.GET.get('status')
    lista_veiculos = Veiculo.objects.all()
    titulo_pagina = "Todos os Veículos"
    if status_filtro == 'DISPONIVEL':
        lista_veiculos = lista_veiculos.filter(status='DISPONIVEL'); titulo_pagina = "Veículos Disponíveis"
    elif status_filtro == 'ARREMATADO':
        lista_veiculos = lista_veiculos.filter(status='ARREMATADO'); titulo_pagina = "Veículos Arrematados"
    contexto = { 'veiculos': lista_veiculos.order_by('lote'), 'titulo_pagina': titulo_pagina, }
    return render(request, 'core/lista_completa_veiculos.html', contexto)