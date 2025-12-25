import streamlit as st
import pandas as pd
import psycopg2
import bcrypt
from datetime import datetime

# Função para conectar ao Supabase usando st.secrets
def get_connection():
    # Quando rodar localmente sem secrets, pode dar erro se não configurado, 
    # mas focaremos no deploy nuvem.
    return psycopg2.connect(st.secrets["DATABASE_URL"])

def init_db():
    """Cria as tabelas no PostgreSQL (Supabase) se não existirem."""
    conn = get_connection()
    c = conn.cursor()
    
    # 1. Tabela de Usuários (Login)
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT
        )
    ''')

    # 2. Lançamentos (Com user_id)
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

    # 3. Investimentos (Com user_id)
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

    # 4. Metas (Com user_id e chave composta)
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

# --- AUTENTICAÇÃO ---

def criar_usuario(username, password, name):
    conn = get_connection()
    c = conn.cursor()
    # Criptografar senha
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    try:
        c.execute("INSERT INTO users (username, password_hash, name) VALUES (%s, %s, %s)", 
                  (username, hashed, name))
        conn.commit()
        return True
    except Exception as e:
        print(e) # Provavelmente usuário já existe
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

# --- FUNÇÕES DE DADOS (Agora todas pedem user_id) ---

def salvar_lancamento(user_id, dados: dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO lancamentos (user_id, data, tipo, categoria, subcategoria, descricao, valor, conta, forma_pagamento, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (
        user_id, dados['data'], dados['tipo'], dados['categoria'], dados['subcategoria'],
        dados['descricao'], dados['valor'], dados['conta'], dados['forma_pagamento'], dados['status']
    ))
    conn.commit()
    conn.close()

def carregar_dados(user_id):
    conn = get_connection()
    # Usando pandas com SQLAlchemy engine seria ideal, mas psycopg2 direto é mais leve p/ setup
    sql = "SELECT * FROM lancamentos WHERE user_id = %s"
    df = pd.read_sql_query(sql, conn, params=(user_id,))
    conn.close()
    
    # Converter data (Postgres retorna date object, pandas precisa de datetime)
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    return df

def excluir_lancamento(user_id, id_lancamento):
    conn = get_connection()
    c = conn.cursor()
    # Importante: WHERE user_id garante que um não apague do outro
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
    ''', (
        user_id, dados['data'], dados['ticker'], dados['tipo_operacao'], dados['classe'],
        dados['quantidade'], dados['preco_unitario'], dados['taxas'], dados['total_operacao'], dados['notas']
    ))
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
    # Upsert no Postgres (ON CONFLICT)
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