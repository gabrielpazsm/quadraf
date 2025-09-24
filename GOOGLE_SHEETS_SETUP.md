# Configuração do Google Sheets para Persistência de Dados

## Visão Geral
Este sistema agora utiliza Google Sheets como banco de dados, permitindo que os dados sobrevivam a deploys no Streamlit Cloud.

## Funcionamento
- **Modo Offline**: Para desenvolvimento local (dados em memória)
- **Modo Online**: Para produção (dados persistidos no Google Sheets)

## Configuração para Produção (Streamlit Cloud)

### 1. Criar Projeto no Google Cloud Console
1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um novo projeto (ex: "quadra-financeiro")
3. Ative a "Google Sheets API"

### 2. Criar Credenciais
1. No Google Cloud Console, vá para "APIs e Serviços" > "Credenciais"
2. Clique em "Criar credenciais" > "Conta de serviço"
3. Preencha os dados:
   - Nome: "streamlit-sheets-access"
   - Descrição: "Acesso ao Sheets para app Streamlit"
4. Clique em "Criar e continuar"
5. Pule a etapa "Opcional conceder a essa conta de serviço acesso ao projeto"
6. Clique em "Concluído"

### 3. Baixar Chave JSON
1. Na lista de contas de serviço, encontre a conta criada
2. Clique nos 3 pontos > "Gerenciar chaves"
3. Clique em "Adicionar chave" > "Criar nova chave"
4. Selecione "JSON" e clique em "Criar"
5. Baixe o arquivo JSON

### 4. Compartilhar Google Sheet
1. Crie uma nova planilha no Google Sheets
2. Nomeie-a como "Quadra Financeiro"
3. Copie o email da conta de serviço (ex: streamlit-sheets-access@...gserviceaccount.com)
4. Na planilha, clique em "Compartilhar"
5. Cole o email e dê permissão de "Editor"

### 5. Configurar Secrets no Streamlit Cloud
1. No seu app do Streamlit Cloud, vá para "Settings" > "Secrets"
2. Adicione o seguinte conteúdo:

```toml
[gcp_service_account]
type = "service_account"
project_id = "seu-projeto-id"
private_key_id = "sua-private-key-id"
private_key = """-----BEGIN PRIVATE KEY-----
SUA_CHAVE_PRIVADA_AQUI
-----END PRIVATE KEY-----"""
client_email = "seu-email@seu-projeto.iam.gserviceaccount.com"
client_id = "seu-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/seu-email%40seu-projeto.iam.gserviceaccount.com"

spreadsheet_name = "Quadra Financeiro"
```

## Configuração para Desenvolvimento Local

### Opção 1: Usar Modo Offline (Recomendado para testes)
O sistema já funciona em modo offline por padrão quando não há credenciais configuradas.

### Opção 2: Configurar Credenciais Locais
1. Crie o arquivo `.streamlit/secrets.toml` (já existe com template)
2. Substitua o conteúdo com suas credenciais reais

## Estrutura dos Dados

### Alugueis (aba "alugueis")
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | Número | ID único |
| dia_semana | Texto | Dia da semana |
| mes_referencia | Texto | Mês/ano (MM/YYYY) |
| horario_inicio | Texto | Horário (HH:MM) |
| horas_alugadas | Número | Duração em horas |
| cliente_time | Texto | Nome do cliente/time |
| valor | Número | Valor do aluguel |
| status | Texto | Status (A Vencer, Pago, Em Atraso) |
| data_criacao | Texto | Data de criação |

### Transações (aba "transacoes")
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | Número | ID único |
| data_transacao | Texto | Data da transação |
| tipo | Texto | Tipo (Entrada, Saída) |
| descricao | Texto | Descrição |
| valor | Número | Valor |
| observacao | Texto | Observações |
| data_criacao | Texto | Data de criação |

## Benefícios
✅ **Persistência real**: Dados sobrevivem a deploys
✅ **Acesso fácil**: Visualize/editar dados diretamente na planilha
✅ **Backup automático**: Google Sheets mantém histórico
✅ **Colaboração**: Multiple people can access the data
✅ **Segurança**: Autenticação via Google OAuth2

## Troubleshooting

### Erros Comuns
1. **"No secrets found"**: Configure as credenciais no Streamlit Cloud
2. **"Spreadsheet not found"**: Verifique o nome da planilha e permissões
3. **"Insufficient permissions"**: Compartilhe a planilha com o email da conta de serviço

### Testes
- Para testar localmente: use o modo offline
- Para testar em produção: configure as credenciais e faça deploy