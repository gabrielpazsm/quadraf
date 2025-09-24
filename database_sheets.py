import gspread
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Tuple, Optional, List, Dict, Any
import json
import streamlit as st
import time
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import GoogleAuthError

class GoogleSheetsDatabase:
    def __init__(self):
        self.client = None
        self.spreadsheet = None
        self.alugueis_worksheet = None
        self.transacoes_worksheet = None
        self.offline_mode = False
        self.local_data = {
            'alugueis': [],
            'transacoes': []
        }

        # Cache system to reduce API calls
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes cache TTL
        self.last_api_call = 0
        self.min_api_interval = 1.0  # Minimum seconds between API calls

        self._authenticate()

    def _authenticate(self):
        """Autentica com Google Sheets API usando service account credentials."""
        try:
            # Tentar usar secrets do Streamlit primeiro
            if 'gcp_service_account' in st.secrets:
                creds_dict = st.secrets['gcp_service_account']

                # Enhanced logging for debugging
                print(f"DEBUG: Tentando autenticar com email: {creds_dict.get('client_email', 'N/A')}")
                print(f"DEBUG: Project ID: {creds_dict.get('project_id', 'N/A')}")

                try:
                    credentials = Credentials.from_service_account_info(
                        creds_dict,
                        scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
                    )
                    print("DEBUG: Credenciais criadas com sucesso")
                    self.client = gspread.authorize(credentials)
                    print("DEBUG: Cliente gspread autorizado com sucesso")
                except Exception as cred_error:
                    print(f"DEBUG ERRO: Falha ao criar credenciais: {cred_error}")
                    raise Exception(f"Falha na autenticação: {cred_error}")
            else:
                # Fallback para autenticação local (desenvolvimento)
                try:
                    credentials = Credentials.from_service_account_file(
                        'credentials.json',
                        scopes=['https://www.googleapis.com/auth/spreadsheets']
                    )
                    self.client = gspread.authorize(credentials)
                except FileNotFoundError:
                    raise Exception(
                        "Credenciais não encontradas. Para desenvolvimento, crie um arquivo 'credentials.json'. "
                        "Para produção, configure 'gcp_service_account' nos secrets do Streamlit."
                    )

            # Nome da spreadsheet - pode ser configurado via secrets
            spreadsheet_name = st.secrets.get('spreadsheet_name', 'Quadra Financeiro')
            print(f"DEBUG: Procurando spreadsheet: '{spreadsheet_name}'")

            try:
                self.spreadsheet = self.client.open(spreadsheet_name)
                print(f"DEBUG: Spreadsheet '{spreadsheet_name}' encontrada com sucesso")
            except gspread.exceptions.SpreadsheetNotFound:
                print(f"DEBUG: Spreadsheet '{spreadsheet_name}' não encontrada, criando nova...")
                # Criar nova spreadsheet se não existir
                self.spreadsheet = self.client.create(spreadsheet_name)
                self.spreadsheet.share(None, perm_type='anyone', role='reader')
                print(f"DEBUG: Nova spreadsheet '{spreadsheet_name}' criada com sucesso")

            # Configurar worksheets
            self._setup_worksheets()
            print("DEBUG: Worksheets configuradas com sucesso")

        except Exception as e:
            # Enhanced error logging
            print(f"DEBUG ERRO: Falha na autenticação: {str(e)}")
            print(f"DEBUG ERRO: Tipo de erro: {type(e).__name__}")
            # Modo offline para desenvolvimento
            print(f"Modo offline ativado: {str(e)}")
            self.offline_mode = True

    def _rate_limit(self):
        """Implement rate limiting to avoid API quota exceeded errors."""
        current_time = time.time()
        time_since_last_call = current_time - self.last_api_call

        if time_since_last_call < self.min_api_interval:
            sleep_time = self.min_api_interval - time_since_last_call
            time.sleep(sleep_time)

        self.last_api_call = time.time()

    def _get_cache_key(self, prefix: str, *args) -> str:
        """Generate a cache key."""
        return f"{prefix}_{'_'.join(str(arg) for arg in args)}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid."""
        if cache_key not in self.cache:
            return False

        cache_time, _ = self.cache[cache_key]
        return (time.time() - cache_time) < self.cache_ttl

    def _get_cached_data(self, cache_key: str):
        """Get data from cache if valid."""
        if self._is_cache_valid(cache_key):
            _, data = self.cache[cache_key]
            return data
        return None

    def _cache_data(self, cache_key: str, data):
        """Store data in cache."""
        self.cache[cache_key] = (time.time(), data)

    def _invalidate_cache(self, pattern: str = None):
        """Invalidate cache entries."""
        if pattern:
            keys_to_remove = [key for key in self.cache.keys() if pattern in key]
            for key in keys_to_remove:
                self.cache.pop(key, None)
        else:
            self.cache.clear()

    def _retry_with_backoff(self, func, *args, max_retries=3, **kwargs):
        """Retry function call with exponential backoff."""
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                return func(*args, **kwargs)
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    if attempt == max_retries - 1:
                        raise

                    wait_time = (2 ** attempt) * self.min_api_interval
                    print(f"Rate limit hit, waiting {wait_time:.1f}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                else:
                    raise

    def _setup_worksheets(self):
        """Configura as worksheets necessárias."""
        try:
            print("DEBUG: Configurando worksheets...")

            # Worksheet de alugueis
            try:
                self.alugueis_worksheet = self.spreadsheet.worksheet("alugueis")
                print("DEBUG: Worksheet 'alugueis' encontrada")
            except gspread.exceptions.WorksheetNotFound:
                print("DEBUG: Worksheet 'alugueis' não encontrada, criando...")
                self.alugueis_worksheet = self.spreadsheet.add_worksheet("alugueis", 1, 9)
                # Cabeçalhos para alugueis
                headers_alugueis = [
                    'id', 'dia_semana', 'mes_referencia', 'horario_inicio',
                    'horas_alugadas', 'cliente_time', 'valor', 'status', 'data_criacao'
                ]
                self.alugueis_worksheet.append_row(headers_alugueis)
                print("DEBUG: Worksheet 'alugueis' criada com cabeçalhos")

            # Worksheet de transacoes
            try:
                self.transacoes_worksheet = self.spreadsheet.worksheet("transacoes")
                print("DEBUG: Worksheet 'transacoes' encontrada")
            except gspread.exceptions.WorksheetNotFound:
                print("DEBUG: Worksheet 'transacoes' não encontrada, criando...")
                self.transacoes_worksheet = self.spreadsheet.add_worksheet("transacoes", 1, 6)
                # Cabeçalhos para transacoes
                headers_transacoes = [
                    'id', 'data_transacao', 'tipo', 'descricao', 'valor', 'observacao', 'data_criacao'
                ]
                self.transacoes_worksheet.append_row(headers_transacoes)
                print("DEBUG: Worksheet 'transacoes' criada com cabeçalhos")

            print("DEBUG: Worksheets configuradas com sucesso")

        except Exception as e:
            print(f"DEBUG ERRO: Falha ao configurar worksheets: {str(e)}")
            print(f"DEBUG ERRO: Tipo de erro: {type(e).__name__}")
            raise Exception(f"Erro ao configurar worksheets: {str(e)}")

    def _get_next_id(self, worksheet) -> int:
        """Gera próximo ID para uma worksheet."""
        try:
            if worksheet is None:
                return 1

            # Use cached data if available
            cache_key = self._get_cache_key("next_id", id(worksheet))
            cached_id = self._get_cached_data(cache_key)
            if cached_id:
                return cached_id

            # Get data with retry logic
            data = self._retry_with_backoff(worksheet.get_all_values)
            if len(data) <= 1:  # Apenas cabeçalho
                next_id = 1
            else:
                # Encontrar maior ID existente
                max_id = 0
                for row in data[1:]:  # Pular cabeçalho
                    if row and row[0].isdigit():
                        max_id = max(max_id, int(row[0]))
                next_id = max_id + 1

            # Cache the result
            self._cache_data(cache_key, next_id)
            return next_id
        except:
            return 1

    def adicionar_aluguel(self, dia_semana: str, mes_referencia: str, horario_inicio: str,
                         horas_alugadas: float, cliente_time: str, valor: float, status: str) -> int:
        """Adiciona um novo registro de aluguel ao Google Sheets."""
        try:
            if self.offline_mode:
                # Modo offline - salvar em memória
                next_id = len(self.local_data['alugueis']) + 1
                data_criacao = datetime.now().isoformat()

                aluguel = {
                    'id': next_id,
                    'dia_semana': dia_semana,
                    'mes_referencia': mes_referencia,
                    'horario_inicio': horario_inicio,
                    'horas_alugadas': horas_alugadas,
                    'cliente_time': cliente_time,
                    'valor': valor,
                    'status': status,
                    'data_criacao': data_criacao
                }

                self.local_data['alugueis'].append(aluguel)
                return next_id
            else:
                # Modo online - Google Sheets
                next_id = self._get_next_id(self.alugueis_worksheet)
                data_criacao = datetime.now().isoformat()

                row = [
                    next_id, dia_semana, mes_referencia, horario_inicio,
                    horas_alugadas, cliente_time, valor, status, data_criacao
                ]

                # Use retry logic for append operation
                self._retry_with_backoff(self.alugueis_worksheet.append_row, row)

                # Invalidate cache when adding new data
                self._invalidate_cache("alugueis")
                self._invalidate_cache("next_id")
                self._invalidate_cache("resumo")

                return next_id
        except Exception as e:
            raise Exception(f"Erro ao adicionar aluguel: {str(e)}")

    def adicionar_transacao(self, data_transacao: str, tipo: str, descricao: str,
                           valor: float, observacao: str = None) -> int:
        """Adiciona uma nova transação financeira ao Google Sheets."""
        try:
            if self.offline_mode:
                # Modo offline - salvar em memória
                next_id = len(self.local_data['transacoes']) + 1
                data_criacao = datetime.now().isoformat()

                transacao = {
                    'id': next_id,
                    'data_transacao': data_transacao,
                    'tipo': tipo,
                    'descricao': descricao,
                    'valor': valor,
                    'observacao': observacao or '',
                    'data_criacao': data_criacao
                }

                self.local_data['transacoes'].append(transacao)
                return next_id
            else:
                # Modo online - Google Sheets
                next_id = self._get_next_id(self.transacoes_worksheet)
                data_criacao = datetime.now().isoformat()

                row = [next_id, data_transacao, tipo, descricao, valor, observacao or '', data_criacao]

                # Use retry logic for append operation
                self._retry_with_backoff(self.transacoes_worksheet.append_row, row)

                # Invalidate cache when adding new data
                self._invalidate_cache("transacoes")
                self._invalidate_cache("next_id")
                self._invalidate_cache("resumo")

                return next_id
        except Exception as e:
            raise Exception(f"Erro ao adicionar transação: {str(e)}")

    def buscar_dados_do_mes(self, ano: int, mes: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Busca todos os dados de alugueis e transações para um mês/ano específico."""
        try:
            if self.offline_mode:
                # Modo offline - usar dados locais
                mes_ano_str = f"{mes:02d}/{ano}"

                # Filtrar alugueis
                alugueis_filtrados = [a for a in self.local_data['alugueis'] if a.get('mes_referencia') == mes_ano_str]
                alugueis_df = pd.DataFrame(alugueis_filtrados)

                if alugueis_df.empty:
                    alugueis_df = pd.DataFrame(columns=[
                        'id', 'dia_semana', 'mes_referencia', 'horario_inicio',
                        'horas_alugadas', 'cliente_time', 'valor', 'status', 'data_criacao'
                    ])

                # Filtrar transações
                transacoes_filtradas = [t for t in self.local_data['transacoes']]
                transacoes_df = pd.DataFrame(transacoes_filtradas)

                if not transacoes_df.empty:
                    transacoes_df['data_transacao'] = pd.to_datetime(transacoes_df['data_transacao'], errors='coerce')
                    mask = (transacoes_df['data_transacao'].dt.year == ano) & \
                           (transacoes_df['data_transacao'].dt.month == mes)
                    transacoes_df = transacoes_df[mask]
                else:
                    transacoes_df = pd.DataFrame(columns=[
                        'id', 'data_transacao', 'tipo', 'descricao', 'valor', 'observacao', 'data_criacao'
                    ])

                return alugueis_df, transacoes_df
            else:
                # Check cache first
                cache_key = self._get_cache_key("dados_mes", ano, mes)
                cached_result = self._get_cached_data(cache_key)
                if cached_result:
                    return cached_result

                # Modo online - Google Sheets com otimização
                if self.alugueis_worksheet is None or self.transacoes_worksheet is None:
                    raise Exception("Worksheets não disponíveis. Verifique a conexão com Google Sheets.")

                # Buscar dados com retry logic e rate limiting
                alugueis_data = self._retry_with_backoff(self.alugueis_worksheet.get_all_values)
                transacoes_data = self._retry_with_backoff(self.transacoes_worksheet.get_all_values)

                # Converter para DataFrame
                if len(alugueis_data) > 1:
                    alugueis_df = pd.DataFrame(alugueis_data[1:], columns=alugueis_data[0])
                    # Filtrar por mês/ano (usando mes_referencia para alugueis)
                    mes_ano_str = f"{mes:02d}/{ano}"
                    alugueis_df = alugueis_df[alugueis_df['mes_referencia'] == mes_ano_str]

                    # Converter colunas numéricas para tipos corretos
                    alugueis_df['valor'] = pd.to_numeric(alugueis_df['valor'], errors='coerce').fillna(0)
                    alugueis_df['horas_alugadas'] = pd.to_numeric(alugueis_df['horas_alugadas'], errors='coerce').fillna(0)
                    alugueis_df['id'] = pd.to_numeric(alugueis_df['id'], errors='coerce').fillna(0).astype(int)
                else:
                    alugueis_df = pd.DataFrame(columns=[
                        'id', 'dia_semana', 'mes_referencia', 'horario_inicio',
                        'horas_alugadas', 'cliente_time', 'valor', 'status', 'data_criacao'
                    ])

                if len(transacoes_data) > 1:
                    transacoes_df = pd.DataFrame(transacoes_data[1:], columns=transacoes_data[0])
                    # Filtrar por mês/ano
                    transacoes_df['data_transacao'] = pd.to_datetime(transacoes_df['data_transacao'], errors='coerce')
                    mask = (transacoes_df['data_transacao'].dt.year == ano) & \
                           (transacoes_df['data_transacao'].dt.month == mes)
                    transacoes_df = transacoes_df[mask]

                    # Converter colunas numéricas para tipos corretos
                    transacoes_df['valor'] = pd.to_numeric(transacoes_df['valor'], errors='coerce').fillna(0)
                    transacoes_df['id'] = pd.to_numeric(transacoes_df['id'], errors='coerce').fillna(0).astype(int)
                else:
                    transacoes_df = pd.DataFrame(columns=[
                        'id', 'data_transacao', 'tipo', 'descricao', 'valor', 'observacao', 'data_criacao'
                    ])

                # Cache the result
                result = (alugueis_df, transacoes_df)
                self._cache_data(cache_key, result)

                return result

        except Exception as e:
            # Check for quota/429 errors and provide better error message
            if "429" in str(e) or "quota" in str(e).lower():
                raise Exception(f"Limite da API atingido. Tente novamente em alguns instantes. Erro: {str(e)}")
            raise Exception(f"Erro ao buscar dados do mês: {str(e)}")

    def atualizar_status_aluguel(self, id_aluguel: int, novo_status: str) -> bool:
        """Atualiza o status de um aluguel específico."""
        try:
            if self.alugueis_worksheet is None:
                print("DEBUG ERRO: Worksheet 'alugueis' é None - não foi inicializada corretamente")
                print(f"DEBUG ERRO: Modo offline: {self.offline_mode}")
                raise Exception("Worksheet de alugueis não disponível. Verifique a conexão com Google Sheets.")
            print(f"DEBUG: Atualizando status do aluguel {id_aluguel} para '{novo_status}'")

            # Get data with retry logic
            data = self._retry_with_backoff(self.alugueis_worksheet.get_all_values)
            if len(data) <= 1:
                return False

            headers = data[0]
            id_col = headers.index('id')
            status_col = headers.index('status')

            for i, row in enumerate(data[1:], start=2):  # Começar da linha 2
                if row[id_col] == str(id_aluguel):
                    # Use retry logic for update operation
                    self._retry_with_backoff(self.alugueis_worksheet.update_cell, i, status_col + 1, novo_status)

                    # Invalidate cache when updating data
                    self._invalidate_cache("alugueis")
                    self._invalidate_cache("dados_mes")
                    self._invalidate_cache("resumo")

                    return True

            return False
        except Exception as e:
            # Check for quota/429 errors and provide better error message
            if "429" in str(e) or "quota" in str(e).lower():
                raise Exception(f"Limite da API atingido. Tente novamente em alguns instantes. Erro: {str(e)}")
            raise Exception(f"Erro ao atualizar status: {str(e)}")

    def deletar_registro(self, tabela: str, id_registro: int) -> bool:
        """Deleta um registro específico de uma tabela."""
        try:
            if tabela == 'alugueis':
                worksheet = self.alugueis_worksheet
                cache_pattern = "alugueis"
            elif tabela == 'transacoes':
                worksheet = self.transacoes_worksheet
                cache_pattern = "transacoes"
            else:
                return False

            if worksheet is None:
                raise Exception("Worksheet não disponível. Verifique a conexão com Google Sheets.")

            # Get data with retry logic
            data = self._retry_with_backoff(worksheet.get_all_values)
            if len(data) <= 1:
                return False

            headers = data[0]
            id_col = headers.index('id')

            for i, row in enumerate(data[1:], start=2):
                if row[id_col] == str(id_registro):
                    # Use retry logic for delete operation
                    self._retry_with_backoff(worksheet.delete_rows, i)

                    # Invalidate cache when deleting data
                    self._invalidate_cache(cache_pattern)
                    self._invalidate_cache("dados_mes")
                    self._invalidate_cache("resumo")
                    self._invalidate_cache("next_id")

                    return True

            return False
        except Exception as e:
            # Check for quota/429 errors and provide better error message
            if "429" in str(e) or "quota" in str(e).lower():
                raise Exception(f"Limite da API atingido. Tente novamente em alguns instantes. Erro: {str(e)}")
            raise Exception(f"Erro ao deletar registro: {str(e)}")

    def gerar_resumo_financeiro(self, ano: int, mes: int) -> dict:
        """Gera um resumo financeiro para o mês/ano especificado."""
        try:
            # Check cache first
            cache_key = self._get_cache_key("resumo", ano, mes)
            cached_result = self._get_cached_data(cache_key)
            if cached_result:
                return cached_result

            alugueis_df, transacoes_df = self.buscar_dados_do_mes(ano, mes)

            # Converter colunas numéricas
            alugueis_df['valor'] = pd.to_numeric(alugueis_df['valor'], errors='coerce').fillna(0)
            transacoes_df['valor'] = pd.to_numeric(transacoes_df['valor'], errors='coerce').fillna(0)

            # Resumo de alugueis
            alugueis_pago = alugueis_df[alugueis_df['status'] == 'Pago']['valor'].sum()
            alugueis_a_pagar = alugueis_df[alugueis_df['status'] != 'Pago']['valor'].sum()
            total_alugueis = len(alugueis_df)
            total_horas = pd.to_numeric(alugueis_df['horas_alugadas'], errors='coerce').fillna(0).sum()

            # Resumo de transações
            transacoes_entradas = transacoes_df[transacoes_df['tipo'] == 'Entrada']['valor'].sum()
            transacoes_saidas = transacoes_df[transacoes_df['tipo'] == 'Saída']['valor'].sum()
            total_transacoes = len(transacoes_df)

            result = {
                'alugueis': {
                    'total_pago': alugueis_pago,
                    'total_a_pagar': alugueis_a_pagar,
                    'total_alugueis': total_alugueis,
                    'total_horas': total_horas
                },
                'transacoes': {
                    'total_entradas': transacoes_entradas,
                    'total_saidas': transacoes_saidas,
                    'total_transacoes': total_transacoes
                }
            }

            # Cache the result
            self._cache_data(cache_key, result)

            return result
        except Exception as e:
            # Check for quota/429 errors and provide better error message
            if "429" in str(e) or "quota" in str(e).lower():
                raise Exception(f"Limite da API atingido. Tente novamente em alguns instantes. Erro: {str(e)}")
            raise Exception(f"Erro ao gerar resumo financeiro: {str(e)}")

    def obter_dias_semana(self) -> list:
        """Retorna a lista de dias da semana para formulários."""
        return ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']

    def buscar_todos_os_dados(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Busca todos os dados de uma só vez para evitar múltiplas chamadas API."""
        try:
            if self.offline_mode:
                # Modo offline - usar dados locais
                alugueis_df = pd.DataFrame(self.local_data['alugueis'])
                transacoes_df = pd.DataFrame(self.local_data['transacoes'])

                if alugueis_df.empty:
                    alugueis_df = pd.DataFrame(columns=[
                        'id', 'dia_semana', 'mes_referencia', 'horario_inicio',
                        'horas_alugadas', 'cliente_time', 'valor', 'status', 'data_criacao'
                    ])

                if transacoes_df.empty:
                    transacoes_df = pd.DataFrame(columns=[
                        'id', 'data_transacao', 'tipo', 'descricao', 'valor', 'observacao', 'data_criacao'
                    ])

                return alugueis_df, transacoes_df
            else:
                # Check cache first
                cache_key = self._get_cache_key("todos_dados")
                cached_result = self._get_cached_data(cache_key)
                if cached_result:
                    return cached_result

                # Modo online - Google Sheets com uma única chamada
                if self.alugueis_worksheet is None or self.transacoes_worksheet is None:
                    raise Exception("Worksheets não disponíveis. Verifique a conexão com Google Sheets.")

                # Buscar todos os dados de uma vez
                alugueis_data = self._retry_with_backoff(self.alugueis_worksheet.get_all_values)
                transacoes_data = self._retry_with_backoff(self.transacoes_worksheet.get_all_values)

                # Converter para DataFrame
                if len(alugueis_data) > 1:
                    alugueis_df = pd.DataFrame(alugueis_data[1:], columns=alugueis_data[0])

                    # Converter colunas numéricas para tipos corretos
                    alugueis_df['valor'] = pd.to_numeric(alugueis_df['valor'], errors='coerce').fillna(0)
                    alugueis_df['horas_alugadas'] = pd.to_numeric(alugueis_df['horas_alugadas'], errors='coerce').fillna(0)
                    alugueis_df['id'] = pd.to_numeric(alugueis_df['id'], errors='coerce').fillna(0).astype(int)
                else:
                    alugueis_df = pd.DataFrame(columns=[
                        'id', 'dia_semana', 'mes_referencia', 'horario_inicio',
                        'horas_alugadas', 'cliente_time', 'valor', 'status', 'data_criacao'
                    ])

                if len(transacoes_data) > 1:
                    transacoes_df = pd.DataFrame(transacoes_data[1:], columns=transacoes_data[0])

                    # Converter colunas de data e numéricas para tipos corretos
                    transacoes_df['data_transacao'] = pd.to_datetime(transacoes_df['data_transacao'], errors='coerce')
                    transacoes_df['valor'] = pd.to_numeric(transacoes_df['valor'], errors='coerce').fillna(0)
                    transacoes_df['id'] = pd.to_numeric(transacoes_df['id'], errors='coerce').fillna(0).astype(int)
                else:
                    transacoes_df = pd.DataFrame(columns=[
                        'id', 'data_transacao', 'tipo', 'descricao', 'valor', 'observacao', 'data_criacao'
                    ])

                # Cache the result
                result = (alugueis_df, transacoes_df)
                self._cache_data(cache_key, result)

                return result

        except Exception as e:
            # Check for quota/429 errors and provide better error message
            if "429" in str(e) or "quota" in str(e).lower():
                raise Exception(f"Limite da API atingido. Tente novamente em alguns instantes. Erro: {str(e)}")
            raise Exception(f"Erro ao buscar todos os dados: {str(e)}")

    def buscar_dados_do_ano(self, ano: int) -> Dict[int, Tuple[pd.DataFrame, pd.DataFrame]]:
        """Busca todos os dados de um ano inteiro com uma única chamada API."""
        try:
            # Buscar todos os dados de uma vez
            alugueis_df, transacoes_df = self.buscar_todos_os_dados()

            # Converter colunas de data
            if not transacoes_df.empty:
                transacoes_df['data_transacao'] = pd.to_datetime(transacoes_df['data_transacao'], errors='coerce')

            # Dicionário para armazenar dados de cada mês
            dados_ano = {}

            for mes in range(1, 13):
                # Filtrar alugueis por mês
                mes_ano_str = f"{mes:02d}/{ano}"
                alugueis_mes = alugueis_df[alugueis_df['mes_referencia'] == mes_ano_str].copy()

                # Filtrar transações por mês
                if not transacoes_df.empty:
                    mask = (transacoes_df['data_transacao'].dt.year == ano) & \
                           (transacoes_df['data_transacao'].dt.month == mes)
                    transacoes_mes = transacoes_df[mask].copy()
                else:
                    transacoes_mes = pd.DataFrame(columns=[
                        'id', 'data_transacao', 'tipo', 'descricao', 'valor', 'observacao', 'data_criacao'
                    ])

                dados_ano[mes] = (alugueis_mes, transacoes_mes)

            return dados_ano

        except Exception as e:
            raise Exception(f"Erro ao buscar dados do ano: {str(e)}")

    def obter_status_aluguel(self) -> list:
        """Retorna a lista de status possíveis para alugueis."""
        return ['A Vencer', 'Pago', 'Em Atraso']

    def obter_tipos_transacao(self) -> list:
        """Retorna a lista de tipos de transação."""
        return ['Entrada', 'Saída']

# Instância global do banco de dados
db = GoogleSheetsDatabase()

# Funções de compatibilidade com a interface antiga
def inicializar_banco():
    """Função de compatibilidade - não necessária para Google Sheets."""
    pass

def adicionar_aluguel(dia_semana: str, mes_referencia: str, horario_inicio: str,
                     horas_alugadas: float, cliente_time: str, valor: float, status: str) -> int:
    """Função de compatibilidade para adicionar aluguel."""
    return db.adicionar_aluguel(dia_semana, mes_referencia, horario_inicio, horas_alugadas, cliente_time, valor, status)

def adicionar_transacao(data_transacao: str, tipo: str, descricao: str, valor: float, observacao: str = None) -> int:
    """Função de compatibilidade para adicionar transação."""
    return db.adicionar_transacao(data_transacao, tipo, descricao, valor, observacao)

def buscar_dados_do_mes(ano: int, mes: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Função de compatibilidade para buscar dados do mês."""
    return db.buscar_dados_do_mes(ano, mes)

def atualizar_status_aluguel(id_aluguel: int, novo_status: str) -> bool:
    """Função de compatibilidade para atualizar status."""
    return db.atualizar_status_aluguel(id_aluguel, novo_status)

def deletar_registro(tabela: str, id_registro: int) -> bool:
    """Função de compatibilidade para deletar registro."""
    return db.deletar_registro(tabela, id_registro)

def gerar_resumo_financeiro(ano: int, mes: int) -> dict:
    """Função de compatibilidade para gerar resumo."""
    return db.gerar_resumo_financeiro(ano, mes)

def obter_dias_semana() -> list:
    """Função de compatibilidade para obter dias da semana."""
    return db.obter_dias_semana()

def obter_status_aluguel() -> list:
    """Função de compatibilidade para obter status."""
    return db.obter_status_aluguel()

def obter_tipos_transacao() -> list:
    """Função de compatibilidade para obter tipos de transação."""
    return db.obter_tipos_transacao()

def buscar_todos_os_dados() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Função de compatibilidade para buscar todos os dados."""
    return db.buscar_todos_os_dados()

def buscar_dados_do_ano(ano: int) -> Dict[int, Tuple[pd.DataFrame, pd.DataFrame]]:
    """Função de compatibilidade para buscar dados do ano."""
    return db.buscar_dados_do_ano(ano)

def obter_meses_referencia() -> list:
    """Retorna lista de meses de referência no formato MM/YYYY, ordenados do mais recente para o mais antigo."""
    from datetime import datetime, timedelta

    meses = []
    data_atual = datetime.now()

    # Gera os últimos 12 meses e próximos 6 meses
    for i in range(-12, 7):
        data = data_atual.replace(day=1) + timedelta(days=32 * i)
        data = data.replace(day=1)
        mes_formatado = data.strftime('%m/%Y')
        meses.append((data, mes_formatado))

    # Ordenar do mais recente para o mais antigo usando o objeto datetime
    meses.sort(reverse=True, key=lambda x: x[0])

    # Retornar apenas as strings formatadas
    return [mes[1] for mes in meses]

def validar_ano(ano: str) -> bool:
    """Valida se o ano está no formato correto (4 dígitos, começando com 20)."""
    if not ano:
        return False
    return len(ano) == 4 and ano.isdigit() and ano.startswith('20')

def formatar_mes_ano(mes: int, ano: str) -> str:
    """Formata mês e ano no formato MM/YYYY."""
    if not validar_ano(ano):
        raise ValueError("Ano inválido")
    if not 1 <= mes <= 12:
        raise ValueError("Mês inválido")

    return f"{mes:02d}/{ano}"

def obter_anos_disponiveis() -> list:
    """Retorna lista de anos disponíveis (atual -2 até atual +2)."""
    from datetime import datetime
    ano_atual = datetime.now().year
    return list(range(ano_atual - 2, ano_atual + 3))

if __name__ == "__main__":
    print("Banco de dados Google Sheets inicializado com sucesso!")