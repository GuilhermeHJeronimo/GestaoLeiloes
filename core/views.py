import pandas as pd
from django.shortcuts import render, redirect
from django.utils import timezone
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import logout
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.core.cache import cache
from .models import Comitente, Veiculo, Leilao, Visita, Arremate
from .resources import VeiculoResource
import math
from datetime import timedelta
import requests

# --- FUNÇÕES AUXILIARES E DE PERMISSÃO ---

def _clean_decimal(value):
    if pd.isna(value) or not value: return 0.00
    cleaned_value = str(value).replace('R$', '').strip().replace('.', '').replace(',', '.')
    try: return float(cleaned_value)
    except (ValueError, TypeError): return 0.00

def is_admin(user): return user.is_superuser

@login_required
def redirect_apos_login(request):
    if request.user.is_superuser: return redirect('dashboard')
    else: return redirect('dashboard_recepcao')

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

# --- VIEW DE API ---
@login_required
def buscar_cliente_api(request):
    doc = request.GET.get('cpf')
    if not doc:
        return JsonResponse({'error': 'Documento não fornecido'}, status=400)

    token = cache.get('api_auth_token')
    if not token:
        base_url = settings.API_CLIENTES_BASE_URL.strip('/')
        auth_url = f"{base_url}/integration/api/Authenticate"
        auth_data = { "Client_ID": settings.API_CLIENTES_ID, "Client_Secret": settings.API_CLIENTES_SECRET }
        try:
            auth_response = requests.post(auth_url, json=auth_data, timeout=15)
            auth_response.raise_for_status()
            token_data = auth_response.json()
            token = token_data.get('token') or token_data.get('access_token') or token_data.get('accessToken')
            if not token:
                return JsonResponse({'error': 'Token não encontrado na resposta de autenticação.'}, status=500)
            cache.set('api_auth_token', token, 1800) # Salva por 30 min
        except requests.exceptions.RequestException:
            return JsonResponse({'error': 'Falha na autenticação com a API externa. Verifique as credenciais.'}, status=500)

    base_url = settings.API_CLIENTES_BASE_URL.strip('/')
    headers = {'Authorization': f'Bearer {token}'}
    doc_limpo = doc.replace('.', '').replace('-', '').replace('/', '')
    formatos_para_tentar = [doc_limpo]
    if len(doc_limpo) == 11:
        formatos_para_tentar.append(f"{doc_limpo[:3]}.{doc_limpo[3:6]}.{doc_limpo[6:9]}-{doc_limpo[9:]}")
    elif len(doc_limpo) == 14:
        formatos_para_tentar.append(f"{doc_limpo[:2]}.{doc_limpo[2:5]}.{doc_limpo[5:8]}/{doc_limpo[8:12]}-{doc_limpo[12:]}")
    
    if doc not in formatos_para_tentar:
        formatos_para_tentar.append(doc)

    for formato in formatos_para_tentar:
        try:
            cliente_url = f"{base_url}/integration/api/GetCliente/{formato}"
            cliente_response = requests.get(cliente_url, headers=headers, timeout=10)
            if cliente_response.status_code == 200:
                data = cliente_response.json()
                item_data = data.get("Item")
                if item_data and item_data.get("Nome"):
                    return JsonResponse({'nome': item_data.get("Nome")})
        except requests.exceptions.RequestException:
            continue

    cache.delete('api_auth_token')
    return JsonResponse({'error': 'Cliente não encontrado. Verifique o documento.'}, status=404)

# --- VIEWS DE ADMIN (Apenas Superusuários) ---
@login_required
@user_passes_test(is_admin)
def dashboard(request):
    periodo = request.GET.get('periodo', 'hoje'); hoje = timezone.localtime().date()
    if periodo == 'semana':
        inicio_periodo_dt = hoje - timedelta(days=6); titulo_periodo = "nos Últimos 7 dias"
    elif periodo == 'mes':
        inicio_periodo_dt = hoje.replace(day=1); titulo_periodo = "neste Mês"
    elif periodo == 'total':
        inicio_periodo_dt = None; titulo_periodo = "Desde o Início"
    else:
        inicio_periodo_dt = hoje; titulo_periodo = "Hoje"
    
    visitas_filtradas = Visita.objects.all(); arremates_filtrados = Arremate.objects.all()
    if inicio_periodo_dt:
        inicio_periodo = timezone.make_aware(timezone.datetime.combine(inicio_periodo_dt, timezone.datetime.min.time()))
        if periodo == 'hoje':
            fim_periodo = inicio_periodo + timezone.timedelta(days=1)
            visitas_filtradas = visitas_filtradas.filter(data_visita__gte=inicio_periodo, data_visita__lt=fim_periodo)
            arremates_filtrados = arremates_filtrados.filter(data_arremate__gte=inicio_periodo, data_arremate__lt=fim_periodo)
        else:
            visitas_filtradas = visitas_filtradas.filter(data_visita__gte=inicio_periodo)
            arremates_filtrados = arremates_filtrados.filter(data_arremate__gte=inicio_periodo)
    
    # CÁLCULOS DE RELAÇÃO
    # Pega os conjuntos de CPFs/CNPJs únicos para o período
    cpfs_visitantes = set(visitas_filtradas.values_list('cpf_cliente', flat=True))
    cpfs_arrematantes = set(arremates_filtrados.values_list('cpf_cliente', flat=True))
    # 1. Visitantes que arremataram (interseção dos dois conjuntos)
    visitantes_que_arremataram = len(cpfs_visitantes.intersection(cpfs_arrematantes))
    # 2. Visitantes que NÃO arremataram (diferença: nos visitantes, mas não nos arrematantes)
    visitantes_nao_arremataram = len(cpfs_visitantes.difference(cpfs_arrematantes))
    # 3. Arrematantes que NÃO visitaram (diferença: nos arrematantes, mas não nos visitantes)
    arrematantes_nao_visitaram = len(cpfs_arrematantes.difference(cpfs_visitantes))
    # (Cálculos antigos que continuam necessários)
    todos_os_leiloes = Leilao.objects.all().order_by('-data_leilao_principal')
    taxa_conversao = (visitantes_que_arremataram / len(cpfs_visitantes) * 100) if len(cpfs_visitantes) > 0 else 0
    data_inicial_grafico = timezone.localtime().date() - timedelta(days=6)
    vendas_por_dia = Arremate.objects.filter(data_arremate__date__gte=data_inicial_grafico).annotate(dia=TruncDate('data_arremate')).values('dia').annotate(total=Sum('valor_arremate')).order_by('dia')
    labels_grafico = [v['dia'].strftime('%d/%m') for v in vendas_por_dia]; data_grafico = [float(v['total']) for v in vendas_por_dia]
    leiloes_com_visitas_total = Leilao.objects.annotate(num_visitas=Count('visitas')).filter(num_visitas__gt=0).order_by('-data_leilao_principal')
    total_veiculos_disponiveis = Veiculo.objects.filter(status='DISPONIVEL').count()
    visitas_periodo = visitas_filtradas.count()
    total_arrematado_periodo = arremates_filtrados.aggregate(total=Sum('valor_arremate'))['total'] or 0.00
    top_arrematantes_query = arremates_filtrados.values('cpf_cliente', 'nome_cliente').annotate(total_gasto=Sum('valor_arremate')).order_by('-total_gasto')[:5]
    top_arrematantes_formatado = []
    for arrematante in top_arrematantes_query:
        valor_formatado = f"{arrematante['total_gasto']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        top_arrematantes_formatado.append({'cpf_cliente': arrematante['cpf_cliente'], 'nome_cliente': arrematante['nome_cliente'], 'total_gasto_formatado': valor_formatado})
    veiculos_disponiveis = Veiculo.objects.filter(status='DISPONIVEL').order_by('lote')
    veiculos_arrematados_periodo = Veiculo.objects.filter(status='ARREMATADO', arremate__in=arremates_filtrados).distinct().order_by('lote')
    
    contexto = {
        'total_veiculos_disponiveis': total_veiculos_disponiveis, 'visitas_periodo': visitas_periodo,
        'total_arrematado_periodo': f"{total_arrematado_periodo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        'top_arrematantes': top_arrematantes_formatado, 'veiculos_disponiveis': veiculos_disponiveis,
        'veiculos_arrematados_periodo': veiculos_arrematados_periodo, 'titulo_periodo': titulo_periodo,
        'periodo_selecionado': periodo, 'leiloes_com_visitas_total': leiloes_com_visitas_total,
        'taxa_conversao': taxa_conversao, 'labels_grafico': labels_grafico, 'data_grafico': data_grafico,
        'visitantes_que_arremataram': visitantes_que_arremataram,
        'visitantes_nao_arremataram': visitantes_nao_arremataram,
        'arrematantes_nao_visitaram': arrematantes_nao_visitaram,
        'todos_os_leiloes': todos_os_leiloes,
    }
    return render(request, 'core/dashboard.html', contexto)

@login_required
@user_passes_test(is_admin)
def upload_excel(request):
    contexto = {}
    if request.method == 'POST':
        excel_file = request.FILES.get('excel_file')
        if not excel_file:
            contexto['error'] = 'Nenhum arquivo foi enviado.'
            return render(request, 'core/upload_excel.html', contexto)
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
                    Veiculo.objects.update_or_create(placa=placa, defaults={'lote': int(row.get('LOTES', 0)), 'min_veiculo': str(row.get('VEICULOS', '')), 'comitente': comitente, 'lance_inicial': lance_inicial_limpo, 'proporcao_fipe': str(row.get('FIPE', '')), 'status': 'DISPONIVEL',})
                    sucesso_count += 1
                except Exception as e:
                    erros.append(f"Linha {index+2}: Erro inesperado. {e}")
            contexto['success'] = f'{sucesso_count} veículos importados/atualizados com sucesso.'
            contexto['errors'] = erros
            return render(request, 'core/upload_excel.html', contexto)
        except Exception as e:
            contexto['error'] = f'Erro ao processar a planilha: {e}'
            return render(request, 'core/upload_excel.html', contexto)
    return render(request, 'core/upload_excel.html', contexto)

@login_required
@user_passes_test(is_admin)
def criar_leilao(request):
    if request.method == 'POST':
        nome_evento = request.POST.get('nome_evento'); data_principal = request.POST.get('data_principal'); id_principal = request.POST.get('id_principal'); data_repasse = request.POST.get('data_repasse'); id_repasse = request.POST.get('id_repasse')
        Leilao.objects.create(nome_evento=nome_evento, data_leilao_principal=data_principal, id_leilao_principal=id_principal, data_leilao_repasse=data_repasse, id_leilao_repasse=id_repasse)
        messages.success(request, f"Leilão '{nome_evento}' criado com sucesso!")
        return redirect('dashboard')
    return render(request, 'core/criar_leilao.html')

# --- VIEWS DA RECEPÇÃO E GERAIS ---
@login_required
def dashboard_recepcao(request):
    leiloes_com_visitas_total = Leilao.objects.annotate(num_visitas=Count('visitas')).filter(num_visitas__gt=0).order_by('-data_leilao_principal')
    contexto = {'leiloes_com_visitas_total': leiloes_com_visitas_total}
    return render(request, 'core/dashboard_recepcao.html', contexto)

@login_required
def registrar_visita(request):
    if request.method == 'POST':
        leilao_id = request.POST.get('leilao'); cpf_cliente = request.POST.get('cpf'); nome_cliente = request.POST.get('nome')
        if leilao_id and cpf_cliente and nome_cliente:
            leilao_selecionado = Leilao.objects.get(id=leilao_id)
            Visita.objects.create(leilao=leilao_selecionado, cpf_cliente=cpf_cliente.replace('.', '').replace('-', '').replace('/', ''), nome_cliente=nome_cliente)
            messages.success(request, f"Visita de {nome_cliente} registrada com sucesso!")
        else:
            messages.error(request, "Todos os campos são obrigatórios.")
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
    leilao = Leilao.objects.get(id=leilao_id); veiculo = Veiculo.objects.get(placa=placa_veiculo)
    if request.method == 'POST':
        cpf_cliente = request.POST.get('cpf'); nome_cliente = request.POST.get('nome')
        valor_arremate = _clean_decimal(request.POST.get('valor_arremate'))
        data_arremate = request.POST.get('data_arremate')

        Arremate.objects.create(
            veiculo=veiculo, leilao=leilao, cpf_cliente=cpf_cliente.replace('.', '').replace('-', '').replace('/', ''), 
            nome_cliente=nome_cliente, valor_arremate=valor_arremate, 
            data_arremate=data_arremate
        )
        veiculo.status = 'ARREMATADO'; veiculo.save()
        messages.success(request, f"Arremate do veículo {veiculo.placa} registrado com sucesso!")
        return redirect('lista_veiculos_leilao', leilao_id=leilao.id)
    contexto = { 'leilao': leilao, 'veiculo': veiculo }
    return render(request, 'core/registrar_arremate_form.html', contexto)
    
@login_required
def lista_completa_veiculos(request):
    status_filtro = request.GET.get('status'); comitente_filtro_id = request.GET.get('comitente')
    lista_veiculos_completa = Veiculo.objects.select_related('comitente').all()
    titulo_pagina = "Todos os Veículos"
    if status_filtro:
        lista_veiculos_completa = lista_veiculos_completa.filter(status=status_filtro)
        try: titulo_pagina = f"Veículos com Status '{dict(Veiculo.STATUS_CHOICES)[status_filtro]}'"
        except KeyError: pass
    if comitente_filtro_id:
        lista_veiculos_completa = lista_veiculos_completa.filter(comitente__id=comitente_filtro_id)
        comitente_nome = Comitente.objects.get(id=comitente_filtro_id).nome
        titulo_pagina += f" (Comitente: {comitente_nome})"
    paginator = Paginator(lista_veiculos_completa.order_by('lote'), 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    todos_os_comitentes = Comitente.objects.all()
    contexto = {'page_obj': page_obj, 'titulo_pagina': titulo_pagina, 'status_filtro': status_filtro, 'comitente_filtro_id': comitente_filtro_id, 'todos_os_comitentes': todos_os_comitentes, 'todos_os_status': Veiculo.STATUS_CHOICES, }
    return render(request, 'core/lista_completa_veiculos.html', contexto)

@login_required
def lista_visitantes_leilao(request, leilao_id):
    leilao = Leilao.objects.get(id=leilao_id)
    visitas = Visita.objects.filter(leilao=leilao).order_by('-data_visita')
    contexto = {'leilao': leilao, 'visitas': visitas}
    return render(request, 'core/lista_visitantes.html', contexto)

@login_required
def gerenciar_lotes(request):
    if request.method == 'POST':
        veiculo_placa = request.POST.get('veiculo_placa')
        acao = request.POST.get('acao')
        veiculo = Veiculo.objects.get(placa=veiculo_placa)

        if acao == 'cancelar':
            if hasattr(veiculo, 'arremate'):
                veiculo.arremate.delete()
            messages.success(request, f"Arremate do veículo {veiculo.placa} foi cancelado.")
        else:
            novo_status = request.POST.get('novo_status')
            veiculo.status = novo_status; veiculo.save()
            messages.success(request, f"Status do veículo {veiculo.placa} atualizado para '{veiculo.get_status_display()}'.")

        return redirect('gerenciar_lotes')

    veiculos_aguardando_pagamento = Veiculo.objects.filter(status='ARREMATADO')
    veiculos_aguardando_retirada = Veiculo.objects.filter(status='PAGAMENTO_CONFIRMADO')
    contexto = {'aguardando_pagamento': veiculos_aguardando_pagamento, 'aguardando_retirada': veiculos_aguardando_retirada}
    return render(request, 'core/gerenciar_lotes.html', contexto)

@login_required
def exportar_veiculos_xls(request):
    status_filtro = request.GET.get('status'); comitente_filtro_id = request.GET.get('comitente')
    queryset = Veiculo.objects.select_related('comitente').all()
    if status_filtro: queryset = queryset.filter(status=status_filtro)
    if comitente_filtro_id: queryset = queryset.filter(comitente__id=comitente_filtro_id)
    veiculo_resource = VeiculoResource()
    dataset = veiculo_resource.export(queryset.order_by('lote'))
    response = HttpResponse(dataset.xlsx, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="relatorio_veiculos.xlsx"'
    return response

@login_required
@user_passes_test(is_admin)
def dashboard_leilao(request, leilao_id):
    # Pega o objeto do leilão específico
    leilao = Leilao.objects.get(id=leilao_id)

    # Filtra as visitas e arremates APENAS deste leilão
    visitas_do_leilao = Visita.objects.filter(leilao=leilao)
    arremates_do_leilao = Arremate.objects.filter(leilao=leilao)

    # Calcula os KPIs específicos para este leilão
    total_visitas = visitas_do_leilao.count()
    total_arremates = arremates_do_leilao.count()
    total_valor_arrematado = arremates_do_leilao.aggregate(total=Sum('valor_arremate'))['total'] or 0.00
    
    # Pega a lista detalhada de visitantes e arrematantes deste leilão
    lista_visitantes = visitas_do_leilao.order_by('-data_visita')
    lista_arremates = arremates_do_leilao.select_related('veiculo').order_by('-data_arremate')

    contexto = {
        'leilao': leilao,
        'total_visitas': total_visitas,
        'total_arremates': total_arremates,
        'total_valor_arrematado': f"{total_valor_arrematado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        'lista_visitantes': lista_visitantes,
        'lista_arremates': lista_arremates,
    }
    
    return render(request, 'core/dashboard_leilao.html', contexto)