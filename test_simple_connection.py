#!/usr/bin/env python3
"""
Simple test to verify Google Sheets authentication works
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

def test_simple_connection():
    """Test basic authentication without creating spreadsheets"""
    print("\n=== Teste Simples de Autenticação ===")

    try:
        creds_dict = st.secrets['gcp_service_account']
        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        client = gspread.authorize(credentials)
        print("✓ Autenticação com Google Sheets API bem sucedida")

        # Try to list spreadsheets (this should work with just spreadsheets scope)
        try:
            spreadsheets = client.openall()
            print(f"✓ Encontradas {len(spreadsheets)} planilhas")
            for sheet in spreadsheets:
                print(f"  - {sheet.title}")
        except Exception as e:
            print(f"ℹ️ Não foi possível listar planilhas: {e}")

        return True

    except Exception as e:
        print(f"✗ Erro na autenticação: {e}")
        return False

if __name__ == "__main__":
    success = test_simple_connection()
    if success:
        print("\n✅ Autenticação básica funcionando!")
        print("Crie uma planilha manualmente chamada 'Quadra Financeiro' e compartilhe com:")
        print(f"Email: {st.secrets['gcp_service_account']['client_email']}")
        print("Permissão: Editor")
    else:
        print("\n❌ Falha na autenticação.")
    sys.exit(0 if success else 1)