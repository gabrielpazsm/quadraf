#!/usr/bin/env python3
"""
Script para diagnosticar problemas de conexão com Google Sheets
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

def test_credentials():
    """Testa as credenciais do Google Sheets"""
    print("\n=== Testando Credenciais ===")

    try:
        # Testar se o secrets.toml está acessível
        if 'gcp_service_account' in st.secrets:
            print("✓ Credenciais encontradas no secrets.toml")
            creds_dict = st.secrets['gcp_service_account']

            # Verificar campos obrigatórios
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email', 'client_id']
            missing_fields = [field for field in required_fields if field not in creds_dict]

            if missing_fields:
                print(f"✗ Campos obrigatórios faltando: {missing_fields}")
                return False
            else:
                print("✓ Todos os campos obrigatórios presentes")

        else:
            print("✗ Credenciais não encontradas no secrets.toml")
            return False

    except Exception as e:
        print(f"✗ Erro ao acessar credenciais: {e}")
        return False

    return True

def test_authentication():
    """Testa a autenticação com Google Sheets API"""
    print("\n=== Testando Autenticação ===")

    try:
        creds_dict = st.secrets['gcp_service_account']
        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/drive.file'
            ]
        )
        client = gspread.authorize(credentials)
        print("✓ Autenticação com Google Sheets API bem sucedida")
        return client
    except Exception as e:
        print(f"✗ Erro na autenticação: {e}")
        return None

def test_spreadsheet_access(client):
    """Testa o acesso à spreadsheet"""
    print("\n=== Testando Acesso à Spreadsheet ===")

    try:
        spreadsheet_name = st.secrets.get('spreadsheet_name', 'Quadra Financeiro')
        print(f"Procurando spreadsheet: '{spreadsheet_name}'")

        spreadsheet = client.open(spreadsheet_name)
        print(f"✓ Spreadsheet '{spreadsheet.title}' encontrada")
        print(f"  URL: {spreadsheet.url}")
        return spreadsheet
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"✗ Spreadsheet '{spreadsheet_name}' não encontrada")
        return None
    except Exception as e:
        print(f"✗ Erro ao acessar spreadsheet: {e}")
        return None

def test_worksheet_access(spreadsheet):
    """Testa o acesso às worksheets"""
    print("\n=== Testando Acesso às Worksheets ===")

    try:
        # Listar todas as worksheets
        worksheets = spreadsheet.worksheets()
        print(f"✓ Encontradas {len(worksheets)} worksheets:")
        for ws in worksheets:
            print(f"  - {ws.title}")

        # Testar worksheet específica 'alugueis'
        try:
            alugueis_ws = spreadsheet.worksheet("alugueis")
            print("✓ Worksheet 'alugueis' encontrada")

            # Verificar estrutura
            data = alugueis_ws.get_all_values()
            print(f"  - Total de linhas: {len(data)}")
            if len(data) > 0:
                print(f"  - Cabeçalhos: {data[0]}")

            return True
        except gspread.exceptions.WorksheetNotFound:
            print("✗ Worksheet 'alugueis' não encontrada")
            return False

    except Exception as e:
        print(f"✗ Erro ao acessar worksheets: {e}")
        return False

def main():
    """Função principal de diagnóstico"""
    print("=== Diagnóstico de Conexão Google Sheets ===")

    # Testar credenciais
    if not test_credentials():
        print("\n❌ Problema nas credenciais. Verifique o arquivo .streamlit/secrets.toml")
        return False

    # Testar autenticação
    client = test_authentication()
    if not client:
        print("\n❌ Problema na autenticação. Verifique as credenciais e permissões.")
        return False

    # Testar acesso à spreadsheet
    spreadsheet = test_spreadsheet_access(client)
    if not spreadsheet:
        print("\n❌ Spreadsheet não encontrada. Verifique:")
        print("  - O nome da spreadsheet está correto?")
        print("  - A conta de serviço tem acesso à spreadsheet?")
        print("  - A spreadsheet existe?")
        return False

    # Testar acesso às worksheets
    if not test_worksheet_access(spreadsheet):
        print("\n❌ Problema ao acessar worksheet 'alugueis'")
        return False

    print("\n✅ Todos os testes passaram! A conexão com Google Sheets está funcionando.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)