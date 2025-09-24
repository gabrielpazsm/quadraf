import sqlite3
import pandas as pd
from datetime import datetime, date
from typing import Tuple, Optional

DB_FILE = 'gestao.db'

def inicializar_banco():
    """Inicializa o banco de dados criando as tabelas se não existirem."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alugueis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dia_semana TEXT NOT NULL,
            mes_referencia TEXT NOT NULL,
            horario_inicio TEXT NOT NULL,
            horas_alugadas REAL NOT NULL,
            cliente_time TEXT NOT NULL,
            valor REAL NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('A Vencer', 'Pago', 'Em Atraso')),
            data_criacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_transacao TEXT NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('Entrada', 'Saída')),
            descricao TEXT NOT NULL,
            valor REAL NOT NULL,
            observacao TEXT,
            data_criacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

def adicionar_aluguel(dia_semana: str, mes_referencia: str, horario_inicio: str,
                     horas_alugadas: float, cliente_time: str, valor: float, status: str) -> int:
    """Adiciona um novo registro de aluguel ao banco de dados."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO alugueis (dia_semana, mes_referencia, horario_inicio, horas_alugadas, cliente_time, valor, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (dia_semana, mes_referencia, horario_inicio, horas_alugadas, cliente_time, valor, status))

        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def adicionar_transacao(data_transacao: str, tipo: str, descricao: str, valor: float, observacao: str = None) -> int:
    """Adiciona uma nova transação financeira ao banco de dados."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO transacoes (data_transacao, tipo, descricao, valor, observacao)
            VALUES (?, ?, ?, ?, ?)
        ''', (data_transacao, tipo, descricao, valor, observacao))

        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def buscar_dados_do_mes(ano: int, mes: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Busca todos os dados de alugueis e transações para um mês/ano específico.

    Returns:
        Tuple contendo dois DataFrames: (alugueis_df, transacoes_df)
    """
    conn = sqlite3.connect(DB_FILE)

    try:
        alugueis_query = '''
            SELECT * FROM alugueis
            WHERE strftime('%Y', mes_referencia) = ? AND strftime('%m', mes_referencia) = ?
            ORDER BY mes_referencia, dia_semana, horario_inicio
        '''

        transacoes_query = '''
            SELECT * FROM transacoes
            WHERE strftime('%Y', data_transacao) = ? AND strftime('%m', data_transacao) = ?
            ORDER BY data_transacao
        '''

        alugueis_df = pd.read_sql_query(alugueis_query, conn, params=(str(ano), f"{mes:02d}"))
        transacoes_df = pd.read_sql_query(transacoes_query, conn, params=(str(ano), f"{mes:02d}"))

        return alugueis_df, transacoes_df
    finally:
        conn.close()

def atualizar_status_aluguel(id_aluguel: int, novo_status: str) -> bool:
    """Atualiza o status de um aluguel específico."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE alugueis SET status = ? WHERE id = ?
        ''', (novo_status, id_aluguel))

        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def deletar_registro(tabela: str, id_registro: int) -> bool:
    """Deleta um registro específico de uma tabela."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        cursor.execute(f'DELETE FROM {tabela} WHERE id = ?', (id_registro,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def gerar_resumo_financeiro(ano: int, mes: int) -> dict:
    """Gera um resumo financeiro para o mês/ano especificado."""
    conn = sqlite3.connect(DB_FILE)

    try:
        alugueis_query = '''
            SELECT
                SUM(CASE WHEN status = 'Pago' THEN valor ELSE 0 END) as total_pago,
                SUM(CASE WHEN status != 'Pago' THEN valor ELSE 0 END) as total_a_pagar,
                COUNT(*) as total_alugueis,
                SUM(horas_alugadas) as total_horas
            FROM alugueis
            WHERE strftime('%Y', mes_referencia) = ? AND strftime('%m', mes_referencia) = ?
        '''

        transacoes_query = '''
            SELECT
                SUM(CASE WHEN tipo = 'Entrada' THEN valor ELSE 0 END) as total_entradas,
                SUM(CASE WHEN tipo = 'Saída' THEN valor ELSE 0 END) as total_saidas,
                COUNT(*) as total_transacoes
            FROM transacoes
            WHERE strftime('%Y', data_transacao) = ? AND strftime('%m', data_transacao) = ?
        '''

        alugueis_resumo = pd.read_sql_query(alugueis_query, conn, params=(str(ano), f"{mes:02d}"))
        transacoes_resumo = pd.read_sql_query(transacoes_query, conn, params=(str(ano), f"{mes:02d}"))

        return {
            'alugueis': alugueis_resumo.iloc[0].to_dict(),
            'transacoes': transacoes_resumo.iloc[0].to_dict()
        }
    finally:
        conn.close()

def obter_dias_semana() -> list:
    """Retorna a lista de dias da semana para formulários."""
    return ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']

def obter_meses_referencia() -> list:
    """Retorna lista de meses de referência no formato YYYY-MM."""
    from datetime import datetime, timedelta

    meses = []
    data_atual = datetime.now()

    # Gera os últimos 12 meses e próximos 6 meses
    for i in range(-12, 7):
        data = data_atual.replace(day=1) + timedelta(days=32 * i)
        data = data.replace(day=1)
        meses.append(data.strftime('%Y-%m'))

    return meses

def obter_status_aluguel() -> list:
    """Retorna a lista de status possíveis para alugueis."""
    return ['A Vencer', 'Pago', 'Em Atraso']

def obter_tipos_transacao() -> list:
    """Retorna a lista de tipos de transação."""
    return ['Entrada', 'Saída']

if __name__ == "__main__":
    inicializar_banco()
    print("Banco de dados inicializado com sucesso!")