import streamlit as st
import pandas as pd
import psycopg2
import bcrypt
import uuid
from datetime import datetime, timedelta

# Função para conectar ao Supabase usando st.secrets
def get_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # 1. Usuários
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT
        )
    ''')

    # 2. Sessões
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
    ''')

    # 3. Lançamentos (Caixa / Débito)
    c.execute('''
        CREATE TABLE IF NOT EXISTS lancamentos (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            data DATE,
            tipo TEXT,
            categoria TEXT,
            subcategoria TEXT,
            descricao TEXT,
            valor NUMERIC,
            conta TEXT,
            forma_pagamento TEXT,
            status TEXT
        )
    ''')

    # 4. Investimentos
    c.execute('''
        CREATE TABLE IF NOT EXISTS investimentos (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            data DATE,
            ticker TEXT,
            tipo_operacao TEXT,
            classe TEXT,
            quantidade NUMERIC,
            preco_unitario NUMERIC,
            taxas NUMERIC,
            total_operacao NUMERIC,
            notas TEXT
        )
    ''')

    # 5. Metas
    c.execute('''
        CREATE TABLE IF NOT EXISTS metas (
            user_id INTEGER REFERENCES users(id),
            categoria TEXT,
            valor_meta NUMERIC,
            PRIMARY KEY (user_id, categoria)
        )
    ''')

    # --- NOVAS TABELAS ---

    # 6. Cartões de Crédito (Cadastros)
    c.execute('''
        CREATE TABLE IF NOT EXISTS cartoes_credito (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            nome_cartao TEXT,
            dia_fechamento INTEGER,
            dia_vencimento INTEGER
        )
    ''')

    # 7. Lançamentos de Cartão (Compras Parceladas)
    c.execute('''
        CREATE TABLE IF NOT EXISTS lancamentos_cartao (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            cartao_id INTEGER REFERENCES cartoes_credito(id),
            data_compra DATE,
            descricao TEXT,
            categoria TEXT,
            valor_parcela NUMERIC,
            parcela_numero INTEGER,
            qtd_parcelas INTEGER,
            mes_fatura DATE  -- Data de referência da fatura (Ex: 01/01/2025)
        )
    ''')

    # 8. Recorrências (Contas Fixas)
    c.execute('''
        CREATE TABLE IF NOT EXISTS recorrencias (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            nome TEXT,
            valor NUMERIC,
            categoria TEXT,
            dia_vencimento INTEGER,
            tipo TEXT, -- Receita ou Despesa
            ativa BOOLEAN DEFAULT TRUE
        )
    ''')
    
    conn.commit()
    conn.close()

# --- SESSÃO E AUTH (MANTIDO IGUAL) ---

def criar_sessao(user_id):
    token = str(uuid.uuid4())
    expires = datetime.now() + timedelta(days=30)
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO sessions (token, user_id, expires_at) VALUES (%s, %s, %s)", (token, user_id, expires))
        conn.commit()
        return token, expires
    except: return None, None
    finally: conn.close()

def validar_sessao(token):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT s.user_id, u.name, u.username 
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = %s AND s.expires_at > NOW()
    """, (token,))
    result = c.fetchone()
    conn.close()
    if result: return {"id": result[0], "name": result[1], "username": result[2]}
    return None

def apagar_sessao(token):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE token = %s", (token,))
    conn.commit()
    conn.close()

def criar_usuario(username, password, name):
    conn = get_connection()
    c = conn.cursor()
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    try:
        c.execute("INSERT INTO users (username, password_hash, name) VALUES (%s, %s, %s)", (username, hashed, name))
        conn.commit()
        return True
    except: return False
    finally: conn.close()

def verificar_login(username, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, password_hash, name FROM users WHERE username = %s", (username,))
    user = c.fetchone()
    conn.close()
    if user:
        user_id, stored_hash, name = user
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
            return {"id": user_id, "name": name, "username": username}
    return None

# --- FUNÇÕES DE LANÇAMENTOS (CAIXA) ---

def salvar_lancamento(user_id, dados: dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO lancamentos (user_id, data, tipo, categoria, subcategoria, descricao, valor, conta, forma_pagamento, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (user_id, dados['data'], dados['tipo'], dados['categoria'], dados['subcategoria'], dados['descricao'], dados['valor'], dados['conta'], dados['forma_pagamento'], dados['status']))
    conn.commit()
    conn.close()

def carregar_dados(user_id):
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM lancamentos WHERE user_id = %s", conn, params=(user_id,))
    conn.close()
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    return df

def excluir_lancamento(user_id, id_lancamento):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM lancamentos WHERE id=%s AND user_id=%s", (id_lancamento, user_id))
    rows = c.rowcount
    conn.commit()
    conn.close()
    return rows > 0

# --- FUNÇÕES DE INVESTIMENTOS ---

def salvar_investimento(user_id, dados: dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO investimentos (user_id, data, ticker, tipo_operacao, classe, quantidade, preco_unitario, taxas, total_operacao, notas)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (user_id, dados['data'], dados['ticker'], dados['tipo_operacao'], dados['classe'], dados['quantidade'], dados['preco_unitario'], dados['taxas'], dados['total_operacao'], dados['notas']))
    conn.commit()
    conn.close()

def carregar_investimentos(user_id):
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM investimentos WHERE user_id = %s", conn, params=(user_id,))
    conn.close()
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    return df

def excluir_investimento(user_id, id_investimento):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM investimentos WHERE id=%s AND user_id=%s", (id_investimento, user_id))
    rows = c.rowcount
    conn.commit()
    conn.close()
    return rows > 0

# --- FUNÇÕES DE METAS ---

def salvar_meta(user_id, categoria, valor):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO metas (user_id, categoria, valor_meta) VALUES (%s, %s, %s)
        ON CONFLICT (user_id, categoria) DO UPDATE SET valor_meta = EXCLUDED.valor_meta
    ''', (user_id, categoria, valor))
    conn.commit()
    conn.close()

def carregar_metas(user_id):
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM metas WHERE user_id = %s", conn, params=(user_id,))
    conn.close()
    return df

def excluir_meta(user_id, categoria):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM metas WHERE category=%s AND user_id=%s", (categoria, user_id))
    conn.commit()
    conn.close()
    return True

# --- NOVAS FUNÇÕES: CARTÕES DE CRÉDITO ---

def salvar_cartao(user_id, nome, fechamento, vencimento):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO cartoes_credito (user_id, nome_cartao, dia_fechamento, dia_vencimento)
        VALUES (%s, %s, %s, %s)
    ''', (user_id, nome, fechamento, vencimento))
    conn.commit()
    conn.close()

def carregar_cartoes(user_id):
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM cartoes_credito WHERE user_id = %s", conn, params=(user_id,))
    conn.close()
    return df

def excluir_cartao(user_id, cartao_id):
    conn = get_connection()
    c = conn.cursor()
    # Primeiro apaga os lançamentos atrelados para não dar erro de chave estrangeira
    c.execute("DELETE FROM lancamentos_cartao WHERE cartao_id=%s AND user_id=%s", (cartao_id, user_id))
    c.execute("DELETE FROM cartoes_credito WHERE id=%s AND user_id=%s", (cartao_id, user_id))
    conn.commit()
    conn.close()
    return True

def salvar_compra_credito(user_id, cartao_id, data_compra, descricao, categoria, valor_total, qtd_parcelas, dia_fechamento):
    """
    Gera automaticamente as parcelas nas datas corretas de fatura.
    """
    conn = get_connection()
    c = conn.cursor()
    
    valor_parcela = valor_total / qtd_parcelas
    data_obj = pd.to_datetime(data_compra)
    
    # Define a data da primeira fatura
    # Se comprou ANTES do fechamento, cai neste mês. Se DEPOIS, cai no próximo.
    dia_compra = data_obj.day
    mes_atual = data_obj.replace(day=1)
    
    if dia_compra >= dia_fechamento:
        # Pula para o próximo mês
        mes_referencia = (mes_atual + pd.DateOffset(months=1)).date()
    else:
        mes_referencia = mes_atual.date()

    # Loop para criar as N parcelas
    for i in range(qtd_parcelas):
        c.execute('''
            INSERT INTO lancamentos_cartao 
            (user_id, cartao_id, data_compra, descricao, categoria, valor_parcela, parcela_numero, qtd_parcelas, mes_fatura)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (user_id, cartao_id, data_compra, descricao, categoria, valor_parcela, i+1, qtd_parcelas, mes_referencia))
        
        # Avança o mês da referência para a próxima parcela
        mes_referencia = (pd.to_datetime(mes_referencia) + pd.DateOffset(months=1)).date()

    conn.commit()
    conn.close()

def carregar_fatura(user_id, cartao_id, mes_fatura_str):
    """
    Carrega os itens de uma fatura específica (Ex: mes_fatura_str = '2025-02-01')
    """
    conn = get_connection()
    sql = """
        SELECT * FROM lancamentos_cartao 
        WHERE user_id = %s AND cartao_id = %s AND mes_fatura = %s
    """
    df = pd.read_sql_query(sql, conn, params=(user_id, cartao_id, mes_fatura_str))
    conn.close()
    return df

# --- NOVAS FUNÇÕES: RECORRÊNCIAS ---

def salvar_recorrencia(user_id, nome, valor, categoria, dia_vencimento, tipo):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO recorrencias (user_id, nome, valor, categoria, dia_vencimento, tipo)
        VALUES (%s, %s, %s, %s, %s, %s)
    ''', (user_id, nome, valor, categoria, dia_vencimento, tipo))
    conn.commit()
    conn.close()

def carregar_recorrencias(user_id):
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM recorrencias WHERE user_id = %s", conn, params=(user_id,))
    conn.close()
    return df

def excluir_recorrencia(user_id, id_rec):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM recorrencias WHERE id=%s AND user_id=%s", (id_rec, user_id))
    conn.commit()
    conn.close()
    return True

def atualizar_recorrencia(user_id, id_rec, nome, valor, categoria, dia_vencimento, tipo):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE recorrencias 
        SET nome=%s, valor=%s, categoria=%s, dia_vencimento=%s, tipo=%s
        WHERE id=%s AND user_id=%s
    ''', (nome, valor, categoria, dia_vencimento, tipo, id_rec, user_id))
    conn.commit()
    conn.close()
    return True