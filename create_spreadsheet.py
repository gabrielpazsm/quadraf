#!/usr/bin/env python3
"""
Test script to create the Google Sheets spreadsheet
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import streamlit as st
    from google.oauth2.service_account import Credentials
    import gspread
    print("✓ Dependências importadas com sucesso")
except ImportError as e:
    print(f"✗ Erro ao importar dependências: {e}")
    sys.exit(1)

def create_spreadsheet():
    """Create the Google Sheets spreadsheet"""
    print("\n=== Criando Spreadsheet ===")

    try:
        creds_dict = st.secrets['gcp_service_account']
        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        )
        client = gspread.authorize(credentials)
        print("✓ Autenticação com Google Sheets API bem sucedida")

        spreadsheet_name = st.secrets.get('spreadsheet_name', 'Quadra Financeiro')
        print(f"Criando spreadsheet: '{spreadsheet_name}'")

        # Create the spreadsheet
        spreadsheet = client.create(spreadsheet_name)
        print(f"✓ Spreadsheet '{spreadsheet.title}' criada com sucesso")
        print(f"  URL: {spreadsheet.url}")

        # Share with the service account email
        service_account_email = creds_dict['client_email']
        spreadsheet.share(service_account_email, perm_type='user', role='writer')
        print(f"✓ Spreadsheet compartilhada com: {service_account_email}")

        # Create the worksheets
        print("\n=== Criando Worksheets ===")

        # Create alugueis worksheet
        alugueis_ws = spreadsheet.add_worksheet("alugueis", 1, 9)
        headers_alugueis = [
            'id', 'dia_semana', 'mes_referencia', 'horario_inicio',
            'horas_alugadas', 'cliente_time', 'valor', 'status', 'data_criacao'
        ]
        alugueis_ws.append_row(headers_alugueis)
        print("✓ Worksheet 'alugueis' criada com cabeçalhos")

        # Create transacoes worksheet
        transacoes_ws = spreadsheet.add_worksheet("transacoes", 1, 7)
        headers_transacoes = [
            'id', 'data_transacao', 'tipo', 'descricao', 'valor', 'observacao', 'data_criacao'
        ]
        transacoes_ws.append_row(headers_transacoes)
        print("✓ Worksheet 'transacoes' criada com cabeçalhos")

        # Remove the default worksheet
        default_ws = spreadsheet.worksheet("Sheet1")
        spreadsheet.del_worksheet(default_ws)
        print("✓ Worksheet padrão 'Sheet1' removida")

        return True

    except Exception as e:
        print(f"✗ Erro ao criar spreadsheet: {e}")
        return False

if __name__ == "__main__":
    success = create_spreadsheet()
    if success:
        print("\n✅ Spreadsheet criada com sucesso!")
        print("Agora você pode executar a aplicação normalmente.")
    else:
        print("\n❌ Falha ao criar spreadsheet.")
    sys.exit(0 if success else 1)