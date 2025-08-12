from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('', views.dashboard, name='dashboard'),
    path('veiculos/', views.lista_completa_veiculos, name='lista_completa_veiculos'),
    path('upload/', views.upload_excel, name='upload_excel'),
    path('registrar-visita/', views.registrar_visita, name='registrar_visita'),
    path('arremates/', views.selecionar_leilao_arremate, name='selecionar_leilao_arremate'),
    path('leilao/<int:leilao_id>/', views.lista_veiculos_leilao, name='lista_veiculos_leilao'),
    path('leilao/<int:leilao_id>/arrematar/<str:placa_veiculo>/', views.registrar_arremate_final, name='registrar_arremate_final'),
]