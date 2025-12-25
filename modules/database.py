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

    # 2. Sessões (NOVA TABELA PARA COOKIES)
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
    ''')

    # 3. Lançamentos
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
    
    conn.commit()
    conn.close()

# --- SESSÃO E COOKIES (NOVO) ---

def criar_sessao(user_id):
    """Gera um token único, salva no banco e retorna para ser gravado no cookie."""
    token = str(uuid.uuid4())
    # Define validade de 30 dias
    expires = datetime.now() + timedelta(days=30)
    
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO sessions (token, user_id, expires_at) VALUES (%s, %s, %s)", 
                  (token, user_id, expires))
        conn.commit()
        return token, expires
    except Exception as e:
        print(e)
        return None, None
    finally:
        conn.close()

def validar_sessao(token):
    """Verifica se o token do cookie existe no banco e não expirou."""
    conn = get_connection()
    c = conn.cursor()
    # Busca sessão válida unindo com tabela de usuários para pegar o nome
    c.execute("""
        SELECT s.user_id, u.name, u.username 
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = %s AND s.expires_at > NOW()
    """, (token,))
    result = c.fetchone()
    conn.close()
    
    if result:
        return {"id": result[0], "name": result[1], "username": result[2]}
    return None

def apagar_sessao(token):
    """Remove o token do banco ao fazer logout."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE token = %s", (token,))
    conn.commit()
    conn.close()

# --- AUTENTICAÇÃO ---

def criar_usuario(username, password, name):
    conn = get_connection()
    c = conn.cursor()
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    try:
        c.execute("INSERT INTO users (username, password_hash, name) VALUES (%s, %s, %s)", 
                  (username, hashed, name))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

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

# --- FUNÇÕES DE DADOS (Inalteradas, apenas resumidas aqui para contexto) ---
# ... (Mantenha as funções salvar_lancamento, carregar_dados, etc. exatamente como estavam)
# Vou incluir as essenciais abaixo para garantir que o arquivo fique completo

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
    sql = "SELECT * FROM lancamentos WHERE user_id = %s"
    df = pd.read_sql_query(sql, conn, params=(user_id,))
    conn.close()
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    return df

def excluir_lancamento(user_id, id_lancamento):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM lancamentos WHERE id=%s AND user_id=%s", (id_lancamento, user_id))
    rows_deleted = c.rowcount
    conn.commit()
    conn.close()
    return rows_deleted > 0

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
    sql = "SELECT * FROM investimentos WHERE user_id = %s"
    df = pd.read_sql_query(sql, conn, params=(user_id,))
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
    sql = "SELECT * FROM metas WHERE user_id = %s"
    df = pd.read_sql_query(sql, conn, params=(user_id,))
    conn.close()
    return df

def excluir_meta(user_id, categoria):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM metas WHERE category=%s AND user_id=%s", (categoria, user_id))
    conn.commit()
    conn.close()
    return True