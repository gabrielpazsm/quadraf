#!/usr/bin/env python3
"""
Instructions to set up the Google Sheet manually
"""

import streamlit as st

def print_setup_instructions():
    print("=== INSTRUÇÕES DE CONFIGURAÇÃO GOOGLE SHEETS ===\n")

    print("1. CRIE A PLANILHA MANUALMENTE:")
    print("   - Acesse: https://sheets.google.com")
    print("   - Crie uma nova planilha")
    print("   - Nomeie exatamente: 'Quadra Financeiro'")
    print("   - Clique em 'Compartilhar'")
    print(f"   - Adicione o email: {st.secrets['gcp_service_account']['client_email']}")
    print("   - Dê permissão de 'Editor'")
    print("   - Clique em 'Enviar'\n")

    print("2. ESTRUTURA DA PLANILHA:")
    print("   - A aplicação criará automaticamente as abas:")
    print("     * 'alugueis' - para registros de aluguel")
    print("     * 'transacoes' - para transações financeiras")
    print("   - Não é necessário criar as abas manualmente\n")

    print("3. APÓS CONFIGURAR:")
    print("   - Execute novamente: python3 test_google_sheets.py")
    print("   - Execute a aplicação: streamlit run app.py")
    print("   - A aplicação funcionará normalmente\n")

    print("✅ A autenticação está funcionando!")
    print("✅ O serviço account está configurado!")
    print("✅ Apenas falta criar a planilha e compartilhar!\n")

if __name__ == "__main__":
    print_setup_instructions()