Sistema de Gestão de Leilões

<img width="92" height="20" alt="image" src="https://github.com/user-attachments/assets/41fa770c-6aa3-4575-b197-1d2a47ab0bf6" />
<img width="86" height="20" alt="image" src="https://github.com/user-attachments/assets/ee331bb7-e3d1-4fab-ad4d-22d52f0a516e" />
<img width="172" height="20" alt="image" src="https://github.com/user-attachments/assets/bacb5092-7cc6-4d04-9bd7-31e1f3ffa5f5" />

Plataforma web desenvolvida em Django para gestão completa de leilões de veículos, integrando operações do dia a dia com análise estratégica de dados.

Funcionalidades Principais
📊 Dashboard Analítico
Exibição de indicadores em tempo real, como:

Veículos disponíveis

Total arrematado no dia

Visitas registradas

Ranking de maiores compradores

📥 Importação Automática de Lotes
Upload de planilhas Excel (.xlsx) para alimentar o banco de dados com validação e tratamento automático das informações.

📝 Registro Operacional
Interfaces dedicadas para:

Registro de visitas de clientes

Registro e controle de arremates durante o leilão

⚙️ Administração Completa
Painel do Django configurado para gerenciar veículos, comitentes, leilões, visitas e arremates.

🔄 Lógica de Negócio Automatizada
Alteração automática do status de um veículo quando há registro ou cancelamento de arremate.

🔐 Controle de Acesso
Sistema de autenticação com login obrigatório para áreas operacionais.

Tecnologias Utilizadas
Backend: Python + Django

Manipulação de Dados: Pandas

Banco de Dados (Dev): SQLite

Frontend: HTML + CSS (Template Inheritance do Django)

Possíveis Melhorias Futuras
Implementação de grupos e permissões específicas

Filtros por data no dashboard

Paginação para grandes listagens

Exportação de dados para Excel

Deploy em ambiente de produção
