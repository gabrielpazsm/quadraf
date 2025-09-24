# Solução para Erro de Conexão Google Sheets

## Problema Identificado

Erro: "Worksheet de alugueis não disponível. Verifique a conexão com Google Sheets."

## Análise Realizada

### 1. Credenciais
- ✅ Arquivo `.streamlit/secrets.toml` existe e contém todos os campos necessários
- ✅ Formato da chave privada foi corrigido (multi-line string TOML)
- ❌ Autenticação falha com erro: "No key could be detected"

### 2. Possíveis Causas
- **Problema mais provável**: Chave privada inválida ou expirada
- **Credenciais incorretas**: Service account credentials podem estar incorretas
- **Permissões**: Service account não tem acesso ao Google Sheets API
- **Formato**: Ainda pode haver problema de formatação da chave privada

## Arquivos Modificados

### 1. `.streamlit/secrets.toml`
- Corrigido formato da chave privada para multi-line string TOML

### 2. `database_sheets.py`
- Adicionado logging detalhado para diagnóstico
- Melhorado tratamento de erros
- Debug information para rastrear falhas de conexão

### 3. Scripts de Diagnóstico Criados
- `test_google_sheets.py`: Teste completo da conexão
- `debug_credentials.py`: Debug específico de credenciais

## Próximos Passos para Resolver

### 1. Verificar Credenciais
```bash
# Rodar script de diagnóstico
python3 debug_credentials.py
```

### 2. Se as credenciais estiverem inválidas:
- **Gerar novas credenciais** no Google Cloud Console:
  1. Ir para https://console.cloud.google.com/
  2. Selecionar projeto "quadra-financeiro"
  3. IAM & Admin → Service Accounts
  4. Criar novo service account ou usar existente
  5. Gerar nova chave JSON
  6. Atualizar `.streamlit/secrets.toml` com as novas credenciais

### 3. Verificar Permissões
- Certifique-se que o service account tem permissão "Google Sheets API"
- Compartilhe a spreadsheet "Quadra Financeiro" com o email do service account

### 4. Testar Aplicação
```bash
# Rodar aplicação e verificar logs de DEBUG
streamlit run app.py
```

## Logs de DEBUG Ativados

A aplicação agora mostrará logs detalhados:
- Tentativas de autenticação
- Status das worksheets
- Erros específicos com detalhes

## Solução Temporária

Enquanto o problema não for resolvido, a aplicação entra em modo offline automaticamente, mantendo os dados em memória.

## Contato

Se precisar de ajuda para gerar novas credenciais:
1. Verifique o projeto "quadra-financeiro" no Google Cloud Console
2. Certifique-se que a API Google Sheets está ativada
3. Gere novas credenciais de service account