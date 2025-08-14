# Arquivo: core/urls.py (Versão Definitiva)

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Rotas de Autenticação
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('redirect/', views.redirect_apos_login, name='redirect_apos_login'),

    # Rota da nossa API interna para buscar clientes
    path('api/buscar-cliente/', views.buscar_cliente_api, name='buscar_cliente_api'),

    # Dashboards
    path('', views.dashboard, name='dashboard'),
    path('recepcao/', views.dashboard_recepcao, name='dashboard_recepcao'),
    
    # Ferramentas e Listagens
    path('leilao/novo/', views.criar_leilao, name='criar_leilao'),
    path('veiculos/', views.lista_completa_veiculos, name='lista_completa_veiculos'),
    path('upload/', views.upload_excel, name='upload_excel'),
    path('registrar-visita/', views.registrar_visita, name='registrar_visita'),
    path('leilao/<int:leilao_id>/visitantes/', views.lista_visitantes_leilao, name='lista_visitantes_leilao'),
    path('gerenciar-lotes/', views.gerenciar_lotes, name='gerenciar_lotes'),
    path('veiculos/exportar/', views.exportar_veiculos_xls, name='exportar_veiculos'),

    # Fluxo de Arremate
    path('arremates/', views.selecionar_leilao_arremate, name='selecionar_leilao_arremate'),
    path('leilao/<int:leilao_id>/', views.lista_veiculos_leilao, name='lista_veiculos_leilao'),
    path('leilao/<int:leilao_id>/arrematar/<str:placa_veiculo>/', views.registrar_arremate_final, name='registrar_arremate_final'),
    
    #Rota Dashboard Especifico
    path('dashboard/leilao/<int:leilao_id>/', views.dashboard_leilao, name='dashboard_leilao'),
]
