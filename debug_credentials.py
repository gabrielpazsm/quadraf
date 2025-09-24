#!/usr/bin/env python3
"""
Debug script to test credential parsing
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import streamlit as st
    from google.oauth2.service_account import Credentials
    print("✓ Dependências importadas com sucesso")
except ImportError as e:
    print(f"✗ Erro ao importar dependências: {e}")
    sys.exit(1)

def debug_credentials():
    """Debug credential parsing"""
    print("=== Debug Credenciais ===")

    if 'gcp_service_account' in st.secrets:
        creds_dict = st.secrets['gcp_service_account']
        print("✓ Credenciais encontradas")

        # Debug private key
        private_key = creds_dict['private_key']
        print(f"Tipo da private_key: {type(private_key)}")
        print(f"Tamanho da private_key: {len(private_key)}")
        print(f"Primeiros 50 chars: {private_key[:50]}")
        print(f"Últimos 50 chars: {private_key[-50:]}")

        # Check if it has proper newlines
        if '\n' in private_key:
            print(f"✓ Contém \\n caracteres")
            lines = private_key.split('\n')
            print(f"Número de linhas: {len(lines)}")
            print(f"Primeira linha: {lines[0][:50]}...")
            print(f"Última linha: {lines[-1][:50]}...")
        else:
            print("✗ Não contém \\n caracteres")

        # Try to create credentials
        try:
            credentials = Credentials.from_service_account_info(
                creds_dict,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            print("✓ Credenciais criadas com sucesso")
            return True
        except Exception as e:
            print(f"✗ Erro ao criar credenciais: {e}")
            return False
    else:
        print("✗ Credenciais não encontradas")
        return False

if __name__ == "__main__":
    success = debug_credentials()
    sys.exit(0 if success else 1)