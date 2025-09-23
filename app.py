import streamlit as st
import pandas as pd
from datetime import datetime, date
from database import (
    inicializar_banco, adicionar_aluguel, adicionar_transacao, buscar_dados_do_mes,
    atualizar_status_aluguel, deletar_registro, gerar_resumo_financeiro,
    obter_dias_semana, obter_status_aluguel, obter_tipos_transacao
)

inicializar_banco()

st.set_page_config(
    page_title="Quadra Financeiro",
    page_icon="🏟️",
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_dia_semana_from_data(data):
    dias_semana = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
    return dias_semana[data.weekday()]

def dashboard_page():
    st.title("🏟️ Dashboard Financeiro")

    col1, col2 = st.columns(2)

    with col1:
        ano_atual = date.today().year
        anos_disponiveis = list(range(ano_atual - 2, ano_atual + 2))
        ano_selecionado = st.selectbox("Ano", anos_disponiveis, index=anos_disponiveis.index(ano_atual))

    with col2:
        mes_atual = date.today().month
        meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        mes_nome_selecionado = st.selectbox("Mês", meses, index=mes_atual - 1)
        mes_selecionado = meses.index(mes_nome_selecionado) + 1

    try:
        alugueis_df, transacoes_df = buscar_dados_do_mes(ano_selecionado, mes_selecionado)

        total_alugueis = alugueis_df[alugueis_df['status'] == 'Pago']['valor'].sum()
        total_alugueis_a_pagar = alugueis_df[alugueis_df['status'] != 'Pago']['valor'].sum()
        total_outras_entradas = transacoes_df[transacoes_df['tipo'] == 'Entrada']['valor'].sum()
        total_saidas = transacoes_df[transacoes_df['tipo'] == 'Saída']['valor'].sum()

        total_entradas = total_alugueis + total_outras_entradas
        saldo_final = total_entradas - total_saidas

        st.subheader("📊 Resumo Financeiro")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Recebido (Aluguéis)", f"R$ {total_alugueis:,.2f}")

        with col2:
            st.metric("Outras Entradas", f"R$ {total_outras_entradas:,.2f}")

        with col3:
            st.metric("Total Saídas", f"R$ {total_saidas:,.2f}")

        with col4:
            st.metric("Saldo Final", f"R$ {saldo_final:,.2f}",
                     delta=None if saldo_final == 0 else (f"R$ {saldo_final:,.2f}"))

        if total_alugueis_a_pagar > 0:
            st.warning(f"⚠️ Existem aluguéis a receber no valor de R$ {total_alugueis_a_pagar:,.2f}")

        st.subheader("📈 Gráfico Comparativo")

        dados_grafico = pd.DataFrame({
            'Categoria': ['Entradas', 'Saídas'],
            'Valor': [total_entradas, total_saidas]
        })

        st.bar_chart(dados_grafico.set_index('Categoria'))

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🏟️ Detalhes dos Aluguéis")
            if not alugueis_df.empty:
                alugueis_display = alugueis_df.copy()
                alugueis_display['valor'] = alugueis_display['valor'].map(lambda x: f"R$ {x:,.2f}")
                st.dataframe(alugueis_display, use_container_width=True)
            else:
                st.info("Nenhum aluguel registrado neste mês.")

        with col2:
            st.subheader("💰 Outras Transações")
            if not transacoes_df.empty:
                transacoes_display = transacoes_df.copy()
                transacoes_display['valor'] = transacoes_display['valor'].map(lambda x: f"R$ {x:,.2f}")
                st.dataframe(transacoes_display, use_container_width=True)
            else:
                st.info("Nenhuma transação registrada neste mês.")

    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")

def adicionar_aluguel_page():
    st.title("🏟️ Adicionar Aluguel")

    with st.form("form_aluguel"):
        col1, col2 = st.columns(2)

        with col1:
            data_evento = st.date_input("Data do Evento", value=date.today())
            horario_inicio = st.time_input("Horário de Início", value=datetime.now().time())
            horas_alugadas = st.number_input("Horas Alugadas", min_value=0.5, max_value=12.0, value=1.0, step=0.5)

        with col2:
            cliente_time = st.text_input("Cliente/Time", value="")
            valor = st.number_input("Valor (R$)", min_value=0.0, value=50.0, step=10.0)
            status = st.selectbox("Status", obter_status_aluguel())

        dia_semana = get_dia_semana_from_data(data_evento)

        submitted = st.form_submit_button("Salvar Aluguel")

        if submitted:
            if not cliente_time.strip():
                st.error("Por favor, informe o nome do cliente/time.")
            elif valor <= 0:
                st.error("O valor deve ser maior que zero.")
            else:
                try:
                    adicionar_aluguel(
                        data_evento=data_evento.strftime('%Y-%m-%d'),
                        dia_semana=dia_semana,
                        horario_inicio=horario_inicio.strftime('%H:%M'),
                        horas_alugadas=horas_alugadas,
                        cliente_time=cliente_time.strip(),
                        valor=valor,
                        status=status
                    )
                    st.success("✅ Aluguel registrado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao salvar aluguel: {str(e)}")

def adicionar_transacao_page():
    st.title("💰 Adicionar Transação")

    with st.form("form_transacao"):
        col1, col2 = st.columns(2)

        with col1:
            data_transacao = st.date_input("Data da Transação", value=date.today())
            tipo = st.selectbox("Tipo", obter_tipos_transacao())
            descricao = st.text_input("Descrição", value="")

        with col2:
            valor = st.number_input("Valor (R$)", min_value=0.0, value=100.0, step=10.0)
            observacao = st.text_area("Observações (opcional)", value="")

        submitted = st.form_submit_button("Salvar Transação")

        if submitted:
            if not descricao.strip():
                st.error("Por favor, informe uma descrição para a transação.")
            elif valor <= 0:
                st.error("O valor deve ser maior que zero.")
            else:
                try:
                    adicionar_transacao(
                        data_transacao=data_transacao.strftime('%Y-%m-%d'),
                        tipo=tipo,
                        descricao=descricao.strip(),
                        valor=valor,
                        observacao=observacao.strip() if observacao.strip() else None
                    )
                    st.success("✅ Transação registrada com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao salvar transação: {str(e)}")

def ver_lancamentos_page():
    st.title("📋 Todos os Lançamentos")

    tipo_visualizacao = st.radio("Visualizar:", ["Aluguéis", "Transações"], horizontal=True)

    ano_atual = date.today().year
    ano_selecionado = st.selectbox("Filtrar por ano:", [ano_atual - 1, ano_atual, ano_atual + 1], index=1)

    if tipo_visualizacao == "Aluguéis":
        try:
            alugueis_df, _ = buscar_dados_do_mes(ano_selecionado, 1)

            todos_alugueis = []
            for mes in range(1, 13):
                df_aluguel_mes, _ = buscar_dados_do_mes(ano_selecionado, mes)
                if not df_aluguel_mes.empty:
                    todos_alugueis.append(df_aluguel_mes)

            if todos_alugueis:
                alugueis_completos = pd.concat(todos_alugueis, ignore_index=True)
                alugueis_completos = alugueis_completos.sort_values('data_evento')
                alugueis_completos['valor'] = alugueis_completos['valor'].map(lambda x: f"R$ {x:,.2f}")
                st.dataframe(alugueis_completos, use_container_width=True)
            else:
                st.info(f"Nenhum aluguel registrado no ano {ano_selecionado}.")

        except Exception as e:
            st.error(f"Erro ao carregar aluguéis: {str(e)}")

    else:
        try:
            _, transacoes_df = buscar_dados_do_mes(ano_selecionado, 1)

            todas_transacoes = []
            for mes in range(1, 13):
                _, df_transacao_mes = buscar_dados_do_mes(ano_selecionado, mes)
                if not df_transacao_mes.empty:
                    todas_transacoes.append(df_transacao_mes)

            if todas_transacoes:
                transacoes_completas = pd.concat(todas_transacoes, ignore_index=True)
                transacoes_completas = transacoes_completas.sort_values('data_transacao')
                transacoes_completas['valor'] = transacoes_completas['valor'].map(lambda x: f"R$ {x:,.2f}")
                st.dataframe(transacoes_completas, use_container_width=True)
            else:
                st.info(f"Nenhuma transação registrada no ano {ano_selecionado}.")

        except Exception as e:
            st.error(f"Erro ao carregar transações: {str(e)}")

def main():
    with st.sidebar:
        st.title("🏟️ Quadra Financeiro")
        st.markdown("---")

        pagina = st.radio(
            "Navegação",
            ["Dashboard", "Adicionar Aluguel", "Adicionar Transação", "Ver Todos os Lançamentos"],
            index=0
        )

        st.markdown("---")
        st.markdown("### 📊 Resumo Rápido")

        try:
            hoje = date.today()
            alugueis_df, transacoes_df = buscar_dados_do_mes(hoje.year, hoje.month)

            total_alugueis_mes = alugueis_df[alugueis_df['status'] == 'Pago']['valor'].sum()
            total_saidas_mes = transacoes_df[transacoes_df['tipo'] == 'Saída']['valor'].sum()

            st.metric("Aluguéis esse mês", f"R$ {total_alugueis_mes:,.0f}")
            st.metric("Despesas esse mês", f"R$ {total_saidas_mes:,.0f}")

        except:
            st.write("Dados não disponíveis")

    if pagina == "Dashboard":
        dashboard_page()
    elif pagina == "Adicionar Aluguel":
        adicionar_aluguel_page()
    elif pagina == "Adicionar Transação":
        adicionar_transacao_page()
    elif pagina == "Ver Todos os Lançamentos":
        ver_lancamentos_page()

if __name__ == "__main__":
    main()