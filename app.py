import streamlit as st
import pandas as pd
import time
from datetime import datetime, date
from database_sheets import (
    inicializar_banco, adicionar_aluguel, adicionar_transacao, buscar_dados_do_mes,
    atualizar_status_aluguel, deletar_registro, gerar_resumo_financeiro,
    obter_dias_semana, obter_meses_referencia, obter_status_aluguel, obter_tipos_transacao,
    validar_ano, formatar_mes_ano, obter_anos_disponiveis, buscar_dados_do_ano
)

def safe_numeric_conversion(series, fill_value=0):
    """Converte série para tipo numérico de forma segura."""
    try:
        return pd.to_numeric(series, errors='coerce').fillna(fill_value)
    except:
        return pd.Series([fill_value] * len(series))

def safe_datetime_conversion(series):
    """Converte série para datetime de forma segura."""
    try:
        return pd.to_datetime(series, errors='coerce')
    except:
        return pd.Series([pd.NaT] * len(series))

# Initialize database with error handling
try:
    inicializar_banco()
except Exception as e:
    st.error("❌ Erro ao inicializar o banco de dados. Verifique suas credenciais do Google Sheets.")
    st.stop()

st.set_page_config(
    page_title="Quadra Financeiro",
    page_icon="🏟️",
    layout="wide",
    initial_sidebar_state="expanded"
)


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

        # Garantir tipos de dados corretos para cálculos
        if not alugueis_df.empty:
            alugueis_df['valor'] = safe_numeric_conversion(alugueis_df['valor'])
            total_alugueis = alugueis_df[alugueis_df['status'] == 'Pago']['valor'].sum()
            total_alugueis_a_pagar = alugueis_df[alugueis_df['status'] != 'Pago']['valor'].sum()
        else:
            total_alugueis = 0
            total_alugueis_a_pagar = 0

        if not transacoes_df.empty:
            transacoes_df['valor'] = safe_numeric_conversion(transacoes_df['valor'])
            total_outras_entradas = transacoes_df[transacoes_df['tipo'] == 'Entrada']['valor'].sum()
            total_saidas = transacoes_df[transacoes_df['tipo'] == 'Saída']['valor'].sum()
        else:
            total_outras_entradas = 0
            total_saidas = 0

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
                # Reorganizar colunas: mostrar mes_referencia e dia_semana, remover data_criacao, mover id para o fim
                colunas_ordem = ['mes_referencia', 'dia_semana', 'horario_inicio', 'horas_alugadas', 'cliente_time', 'valor', 'status', 'id']
                colunas_disponiveis = [col for col in colunas_ordem if col in alugueis_display.columns]
                alugueis_display = alugueis_display[colunas_disponiveis]
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
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower() or "limite" in error_msg.lower():
            st.error("⚠️ Limite da API atingido. Tente novamente em alguns instantes.")
            if st.button("Tentar novamente"):
                st.rerun()
        else:
            st.error(f"Erro ao carregar dados: {error_msg}")
            if st.button("Tentar novamente"):
                st.rerun()

def adicionar_aluguel_page():
    st.title("🏟️ Adicionar Aluguel")

    # Generate 30-minute intervals from 6 AM to 10 PM
    def gerar_intervalos_tempo():
        intervalos = []
        for hora in range(6, 23):  # 6 AM to 10 PM
            for minuto in [0, 30]:
                if hora == 22 and minuto == 30:  # Skip 22:30 (ends at 22:00)
                    continue
                intervalos.append(f"{hora:02d}:{minuto:02d}")
        return intervalos

    with st.form("form_aluguel"):
        col1, col2 = st.columns(2)

        with col1:
            dia_semana = st.selectbox("Dia da Semana", obter_dias_semana())

            # Separar mês e ano
            col_mes, col_ano = st.columns(2)

            with col_mes:
                mes_selecionado = st.selectbox("Mês", list(range(1, 13)), format_func=lambda x: f"{x:02d}", index=date.today().month - 1)

            with col_ano:
                ano_input = st.text_input("Ano", value=str(date.today().year), max_chars=4, key="ano_input")

            # Validação do ano em tempo real
            if ano_input and not validar_ano(ano_input):
                st.error("Ano inválido! Deve ter 4 dígitos e começar com 20 (ex: 2024)")

            intervalos = gerar_intervalos_tempo()
            horario_inicio = st.selectbox("Horário de Início", intervalos, index=12)  # Default to 12:00
            horas_alugadas = st.number_input("Horas Alugadas", min_value=0.5, max_value=12.0, value=1.0, step=0.5)

        with col2:
            cliente_time = st.text_input("Cliente/Time", value="")
            valor = st.number_input("Valor (R$)", min_value=0.0, value=50.0, step=10.0)
            status = st.selectbox("Status", obter_status_aluguel())

        submitted = st.form_submit_button("Salvar Aluguel")

        if submitted:
            # Validações
            if not cliente_time.strip():
                st.error("Por favor, informe o nome do cliente/time.")
            elif valor <= 0:
                st.error("O valor deve ser maior que zero.")
            elif not ano_input:
                st.error("Por favor, informe o ano.")
            elif not validar_ano(ano_input):
                st.error("Ano inválido! Deve ter 4 dígitos e começar com 20 (ex: 2024).")
            else:
                try:
                    # Formatar mês e ano no formato MM/YYYY
                    mes_referencia = formatar_mes_ano(mes_selecionado, ano_input)

                    adicionar_aluguel(
                        dia_semana=dia_semana,
                        mes_referencia=mes_referencia,
                        horario_inicio=horario_inicio,  # Already in HH:MM format
                        horas_alugadas=horas_alugadas,
                        cliente_time=cliente_time.strip(),
                        valor=valor,
                        status=status
                    )
                    st.success("✅ Aluguel registrado com sucesso!")
                    time.sleep(0.5)  # Pequeno delay para garantir que o Google Sheets processe
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar aluguel: {str(e)}")
                    # Adicionar botão para tentar novamente
                    if st.button("Tentar novamente"):
                        st.rerun()

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
                    time.sleep(0.5)  # Pequeno delay para garantir que o Google Sheets processe
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar transação: {str(e)}")
                    # Adicionar botão para tentar novamente
                    if st.button("Tentar novamente"):
                        st.rerun()

def ver_lancamentos_page():
    st.title("📋 Todos os Lançamentos")

    tipo_visualizacao = st.radio("Visualizar:", ["Aluguéis", "Transações"], horizontal=True)

    ano_atual = date.today().year
    ano_selecionado = st.selectbox("Filtrar por ano:", [ano_atual - 1, ano_atual, ano_atual + 1], index=1)

    if tipo_visualizacao == "Aluguéis":
        try:
            # Use optimized single API call for yearly data
            dados_ano = buscar_dados_do_ano(ano_selecionado)

            todos_alugueis = []
            for mes in range(1, 13):
                df_aluguel_mes, _ = dados_ano[mes]
                if not df_aluguel_mes.empty:
                    todos_alugueis.append(df_aluguel_mes)

            if todos_alugueis:
                alugueis_completos = pd.concat(todos_alugueis, ignore_index=True)

                # Garantir que mes_referencia seja string para ordenação correta
                alugueis_completos['mes_referencia'] = alugueis_completos['mes_referencia'].astype(str)

                # Ordenação segura
                try:
                    alugueis_completos = alugueis_completos.sort_values('mes_referencia')
                except Exception as sort_error:
                    st.warning(f"⚠️ Erro ao ordenar dados: {sort_error}")

                # Formatar para display APÓS todas as operações de dados
                alugueis_completos['valor'] = alugueis_completos['valor'].map(lambda x: f"R$ {x:,.2f}")

                # Reorganizar colunas: mostrar mes_referencia e dia_semana, remover data_criacao, mover id para o fim
                colunas_ordem = ['mes_referencia', 'dia_semana', 'horario_inicio', 'horas_alugadas', 'cliente_time', 'valor', 'status', 'id']
                colunas_disponiveis = [col for col in colunas_ordem if col in alugueis_completos.columns]
                alugueis_completos = alugueis_completos[colunas_disponiveis]
                st.dataframe(alugueis_completos, use_container_width=True)
            else:
                st.info(f"Nenhum aluguel registrado no ano {ano_selecionado}.")

        except Exception as e:
            st.error(f"Erro ao carregar aluguéis: {str(e)}")

    else:
        try:
            # Use optimized single API call for yearly data
            dados_ano = buscar_dados_do_ano(ano_selecionado)

            todas_transacoes = []
            for mes in range(1, 13):
                _, df_transacao_mes = dados_ano[mes]
                if not df_transacao_mes.empty:
                    todas_transacoes.append(df_transacao_mes)

            if todas_transacoes:
                transacoes_completas = pd.concat(todas_transacoes, ignore_index=True)

                # Garantir que data_transacao seja datetime para ordenação correta
                transacoes_completas['data_transacao'] = safe_datetime_conversion(transacoes_completas['data_transacao'])

                # Ordenação segura - remover datas inválidas antes de ordenar
                try:
                    transacoes_validas = transacoes_completas[transacoes_completas['data_transacao'].notna()]
                    if not transacoes_validas.empty:
                        transacoes_completas = transacoes_validas.sort_values('data_transacao')
                except Exception as sort_error:
                    st.warning(f"⚠️ Erro ao ordenar transações: {sort_error}")

                # Formatar para display APÓS todas as operações de dados
                transacoes_completas['valor'] = transacoes_completas['valor'].map(lambda x: f"R$ {x:,.2f}")
                st.dataframe(transacoes_completas, use_container_width=True)
            else:
                st.info(f"Nenhuma transação registrada no ano {ano_selecionado}.")

        except Exception as e:
            st.error(f"Erro ao carregar transações: {str(e)}")

def editar_status_aluguel_page():
    st.title("💳 Editar Status de Aluguel")
    st.markdown("Marque aluguéis como pagos ou atualize seu status.")

    try:
        # Use optimized single API call for yearly data
        todos_alugueis = []
        ano_atual = date.today().year
        dados_ano = buscar_dados_do_ano(ano_atual)

        for mes in range(1, 13):
            df_aluguel_mes, _ = dados_ano[mes]
            if not df_aluguel_mes.empty:
                todos_alugueis.append(df_aluguel_mes)

        if todos_alugueis:
            alugueis_df = pd.concat(todos_alugueis, ignore_index=True)
            alugueis_pendentes = alugueis_df[alugueis_df['status'] != 'Pago'].copy()

            if not alugueis_pendentes.empty:
                st.subheader(f"📋 Aluguéis Pendentes ({len(alugueis_pendentes)})")

                # Criar cópia para display para não afetar os dados originais
                display_df = alugueis_pendentes.copy()
                display_df['display_text'] = (
                    display_df['mes_referencia'] + ' - ' +
                    display_df['dia_semana'] + ' - ' +
                    display_df['cliente_time'] + ' - ' +
                    'R$ ' + display_df['valor'].astype(str) + ' - ' +
                    display_df['status']
                )

                aluguel_selecionado = st.selectbox(
                    "Selecione o aluguel para editar:",
                    display_df['display_text'].tolist()
                )

                if aluguel_selecionado:
                    aluguel_info = alugueis_pendentes[
                        display_df['display_text'] == aluguel_selecionado
                    ].iloc[0]

                    st.markdown("### 📝 Detalhes do Aluguel")
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**Mês de Referência:** {aluguel_info['mes_referencia']}")
                        st.write(f"**Dia da Semana:** {aluguel_info['dia_semana']}")
                        st.write(f"**Cliente/Time:** {aluguel_info['cliente_time']}")

                    with col2:
                        st.write(f"**Horário:** {aluguel_info['horario_inicio']}")
                        st.write(f"**Valor:** R$ {aluguel_info['valor']:,.2f}")
                        st.write(f"**Status Atual:** {aluguel_info['status']}")
                        st.write(f"**Duração:** {aluguel_info['horas_alugadas']}h")

                    st.markdown("---")

                    with st.form("form_editar_status"):
                        col1, col2 = st.columns(2)

                        with col1:
                            novo_status = st.selectbox(
                                "Novo Status",
                                obter_status_aluguel(),
                                index=1
                            )

                        with col2:
                            st.write("**Confirmação**")
                            st.markdown("Deseja atualizar o status deste aluguel?")

                        submitted = st.form_submit_button("✅ Atualizar Status")

                        if submitted:
                            try:
                                sucesso = atualizar_status_aluguel(
                                    int(aluguel_info['id']),
                                    novo_status
                                )

                                if sucesso:
                                    st.success(f"✅ Status do aluguel atualizado para '{novo_status}' com sucesso!")
                                    time.sleep(0.5)  # Pequeno delay para garantir que o Google Sheets processe
                                    st.rerun()
                                else:
                                    st.error("❌ Erro ao atualizar o status do aluguel.")

                            except Exception as e:
                                st.error(f"❌ Erro ao atualizar: {str(e)}")
            else:
                st.success("🎉 Todos os aluguéis estão pagos!")
        else:
            st.info("Nenhum aluguel registrado no sistema.")

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower() or "limite" in error_msg.lower():
            st.error("⚠️ Limite da API atingido. Tente novamente em alguns instantes.")
            if st.button("Tentar novamente"):
                st.rerun()
        else:
            st.error(f"Erro ao carregar dados: {error_msg}")
            if st.button("Tentar novamente"):
                st.rerun()

def main():
    with st.sidebar:
        st.title("🏟️ Quadra Financeiro")
        st.markdown("---")

        pagina = st.radio(
            "Navegação",
            ["Dashboard", "Adicionar Aluguel", "Adicionar Transação", "Editar Status de Aluguel", "Ver Todos os Lançamentos"],
            index=0
        )

        st.markdown("---")
        st.markdown("### 📊 Resumo Rápido")

        try:
            hoje = date.today()
            # Usar gerar_resumo_financeiro para melhor performance e cache
            resumo = gerar_resumo_financeiro(hoje.year, hoje.month)

            total_alugueis_mes = resumo['alugueis']['total_pago']
            total_outras_entradas_mes = resumo['transacoes']['total_entradas']
            total_saidas_mes = resumo['transacoes']['total_saidas']

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Aluguéis esse mês", f"R$ {total_alugueis_mes:,.0f}")

            with col2:
                st.metric("Outras Entradas", f"R$ {total_outras_entradas_mes:,.0f}")

            with col3:
                st.metric("Despesas", f"R$ {total_saidas_mes:,.0f}")

            # Mostrar último update
            st.caption(f"📅 Atualizado: {datetime.now().strftime('%H:%M:%S')}")

        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower() or "limite" in str(e).lower():
                st.warning("⚠️ Limite da API atingido. Tente novamente em alguns instantes.")
            else:
                st.write("Dados não disponíveis")

    if pagina == "Dashboard":
        dashboard_page()
    elif pagina == "Adicionar Aluguel":
        adicionar_aluguel_page()
    elif pagina == "Adicionar Transação":
        adicionar_transacao_page()
    elif pagina == "Editar Status de Aluguel":
        editar_status_aluguel_page()
    elif pagina == "Ver Todos os Lançamentos":
        ver_lancamentos_page()

if __name__ == "__main__":
    main()