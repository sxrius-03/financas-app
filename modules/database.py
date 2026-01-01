import streamlit as st
import pandas as pd
import psycopg2
import bcrypt
import uuid
from datetime import datetime, timedelta

# --- HELPER: LIMPAR CACHE ---
def clear_cache():
    """Limpa o cache do Streamlit para forçar recarregamento de dados."""
    st.cache_data.clear()

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

    # 3. Lançamentos (Caixa)
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

    # 5. Metas (MIGRAÇÃO INTELIGENTE PARA SUPORTAR MÊS/ANO)
    try:
        # Verifica se a tabela existe e se tem a coluna 'mes'
        c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='metas' AND column_name='mes'")
        if c.fetchone() is None:
            # Se a tabela existe mas não tem 'mes', precisamos migrar a estrutura
            c.execute("SELECT to_regclass('public.metas')")
            if c.fetchone()[0] is not None:
                # 1. Renomeia a antiga
                c.execute("ALTER TABLE metas RENAME TO metas_old")
                # 2. Cria a nova com mes/ano
                c.execute('''
                    CREATE TABLE metas (
                        user_id INTEGER REFERENCES users(id),
                        categoria TEXT,
                        valor_meta NUMERIC,
                        mes INTEGER,
                        ano INTEGER,
                        PRIMARY KEY (user_id, categoria, mes, ano)
                    )
                ''')
                # 3. Migra dados antigos (assume mês/ano atual para não perder)
                hj_m = datetime.now().month
                hj_a = datetime.now().year
                c.execute(f"INSERT INTO metas (user_id, categoria, valor_meta, mes, ano) SELECT user_id, categoria, valor_meta, {hj_m}, {hj_a} FROM metas_old")
                # 4. Remove a antiga
                c.execute("DROP TABLE metas_old")
    except Exception as e:
        pass 

    # Criação Padrão (se não existir)
    c.execute('''
        CREATE TABLE IF NOT EXISTS metas (
            user_id INTEGER REFERENCES users(id),
            categoria TEXT,
            valor_meta NUMERIC,
            mes INTEGER,
            ano INTEGER,
            PRIMARY KEY (user_id, categoria, mes, ano)
        )
    ''')

    # 6. Cartões de Crédito
    c.execute('''
        CREATE TABLE IF NOT EXISTS cartoes_credito (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            nome_cartao TEXT,
            dia_fechamento INTEGER,
            dia_vencimento INTEGER
        )
    ''')

    # 7. Lançamentos de Cartão
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
            mes_fatura DATE
        )
    ''')

    # 8. Recorrências
    c.execute('''
        CREATE TABLE IF NOT EXISTS recorrencias (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            nome TEXT,
            valor NUMERIC,
            categoria TEXT,
            dia_vencimento INTEGER,
            tipo TEXT,
            ativa BOOLEAN DEFAULT TRUE
        )
    ''')

    # 9. Controle de Faturas
    c.execute('''
        CREATE TABLE IF NOT EXISTS faturas_controle (
            user_id INTEGER REFERENCES users(id),
            cartao_id INTEGER REFERENCES cartoes_credito(id),
            mes_referencia DATE,
            status TEXT,
            data_pagamento DATE,
            valor_pago NUMERIC,
            PRIMARY KEY (user_id, cartao_id, mes_referencia)
        )
    ''')
    
    # 10. Reservas (COM ÍNDICE E TAXA)
    c.execute('''
        CREATE TABLE IF NOT EXISTS reservas (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            nome TEXT,
            tipo_aplicacao TEXT,
            indice TEXT, 
            taxa NUMERIC, 
            rentabilidade TEXT, 
            saldo_atual NUMERIC DEFAULT 0.0,
            meta_valor NUMERIC DEFAULT 0.0
        )
    ''')

    # 11. Transações da Reserva
    c.execute('''
        CREATE TABLE IF NOT EXISTS reserva_transacoes (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            reserva_id INTEGER REFERENCES reservas(id),
            data DATE,
            tipo TEXT,
            valor NUMERIC,
            descricao TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# --- SESSÃO E AUTH ---

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

# --- LANÇAMENTOS (CAIXA) ---

def salvar_lancamento(user_id, dados: dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO lancamentos (user_id, data, tipo, categoria, subcategoria, descricao, valor, conta, forma_pagamento, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (user_id, dados['data'], dados['tipo'], dados['categoria'], dados['subcategoria'], dados['descricao'], dados['valor'], dados['conta'], dados['forma_pagamento'], dados['status']))
    conn.commit()
    conn.close()
    clear_cache() # Limpa cache para atualizar a tela

def atualizar_lancamento(user_id, id_lancamento, dados: dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE lancamentos
        SET data=%s, tipo=%s, categoria=%s, subcategoria=%s, descricao=%s, valor=%s, conta=%s, forma_pagamento=%s, status=%s
        WHERE id=%s AND user_id=%s
    ''', (dados['data'], dados['tipo'], dados['categoria'], dados['subcategoria'], dados['descricao'], dados['valor'], dados['conta'], dados['forma_pagamento'], dados['status'], id_lancamento, user_id))
    conn.commit()
    conn.close()
    clear_cache()

@st.cache_data(ttl=600, show_spinner=False) # Cache de 10 min
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
    clear_cache()
    return rows > 0

# --- INVESTIMENTOS ---

def salvar_investimento(user_id, dados: dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO investimentos (user_id, data, ticker, tipo_operacao, classe, quantidade, preco_unitario, taxas, total_operacao, notas)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (user_id, dados['data'], dados['ticker'], dados['tipo_operacao'], dados['classe'], dados['quantidade'], dados['preco_unitario'], dados['taxas'], dados['total_operacao'], dados['notas']))
    conn.commit()
    conn.close()
    clear_cache()

def atualizar_investimento(user_id, id_inv, dados: dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE investimentos
        SET data=%s, ticker=%s, tipo_operacao=%s, classe=%s, quantidade=%s, preco_unitario=%s, taxas=%s, total_operacao=%s, notas=%s
        WHERE id=%s AND user_id=%s
    ''', (dados['data'], dados['ticker'], dados['tipo_operacao'], dados['classe'], dados['quantidade'], dados['preco_unitario'], dados['taxas'], dados['total_operacao'], dados['notas'], id_inv, user_id))
    conn.commit()
    conn.close()
    clear_cache()

@st.cache_data(ttl=600, show_spinner=False)
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
    clear_cache()
    return rows > 0

# --- METAS (MENSAL) ---

def salvar_meta(user_id, categoria, valor, mes, ano):
    conn = get_connection()
    c = conn.cursor()
    # Upsert com base em User + Categoria + Mês + Ano
    c.execute('''
        INSERT INTO metas (user_id, categoria, valor_meta, mes, ano) 
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (user_id, categoria, mes, ano) 
        DO UPDATE SET valor_meta = EXCLUDED.valor_meta
    ''', (user_id, categoria, valor, mes, ano))
    conn.commit()
    conn.close()
    clear_cache()

@st.cache_data(ttl=600, show_spinner=False)
def carregar_metas(user_id, mes=None, ano=None):
    conn = get_connection()
    sql = "SELECT * FROM metas WHERE user_id = %s"
    params = [user_id]
    
    # CORREÇÃO IMPORTANTE: Use 'is not None' para que mes=0 (meta anual) funcione
    if mes is not None and ano is not None:
        sql += " AND mes = %s AND ano = %s"
        params.extend([mes, ano])
        
    df = pd.read_sql_query(sql, conn, params=tuple(params))
    conn.close()
    return df

def excluir_meta(user_id, categoria, mes, ano):
    conn = get_connection()
    c = conn.cursor()
    # CORREÇÃO IMPORTANTE: Trocado 'category' por 'categoria'
    c.execute("DELETE FROM metas WHERE categoria=%s AND user_id=%s AND mes=%s AND ano=%s", (categoria, user_id, mes, ano))
    conn.commit()
    conn.close()
    clear_cache()
    return True

@st.cache_data(ttl=600, show_spinner=False)
def listar_meses_com_metas(user_id):
    """Retorna lista de (mes, ano) que possuem metas cadastradas"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT DISTINCT mes, ano FROM metas WHERE user_id = %s ORDER BY ano DESC, mes DESC", (user_id,))
    dados = c.fetchall()
    conn.close()
    return dados 

# --- CARTÕES DE CRÉDITO ---

def salvar_cartao(user_id, nome, fechamento, vencimento):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO cartoes_credito (user_id, nome_cartao, dia_fechamento, dia_vencimento)
        VALUES (%s, %s, %s, %s)
    ''', (user_id, nome, fechamento, vencimento))
    conn.commit()
    conn.close()
    clear_cache()

@st.cache_data(ttl=600, show_spinner=False)
def carregar_cartoes(user_id):
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM cartoes_credito WHERE user_id = %s", conn, params=(user_id,))
    conn.close()
    return df

def excluir_cartao(user_id, cartao_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM lancamentos_cartao WHERE cartao_id=%s AND user_id=%s", (cartao_id, user_id))
    c.execute("DELETE FROM cartoes_credito WHERE id=%s AND user_id=%s", (cartao_id, user_id))
    c.execute("DELETE FROM faturas_controle WHERE cartao_id=%s AND user_id=%s", (cartao_id, user_id))
    conn.commit()
    conn.close()
    clear_cache()
    return True

def salvar_compra_credito(user_id, cartao_id, data_compra, descricao, categoria, valor_total, qtd_parcelas, dia_fechamento):
    conn = get_connection()
    c = conn.cursor()
    valor_parcela = valor_total / qtd_parcelas
    data_obj = pd.to_datetime(data_compra)
    dia_compra = data_obj.day
    mes_atual = data_obj.replace(day=1)
    
    if dia_compra >= dia_fechamento:
        mes_referencia = (mes_atual + pd.DateOffset(months=1)).date()
    else:
        mes_referencia = mes_atual.date()

    for i in range(qtd_parcelas):
        c.execute('''
            INSERT INTO lancamentos_cartao 
            (user_id, cartao_id, data_compra, descricao, categoria, valor_parcela, parcela_numero, qtd_parcelas, mes_fatura)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (user_id, cartao_id, data_compra, descricao, categoria, valor_parcela, i+1, qtd_parcelas, mes_referencia))
        mes_referencia = (pd.to_datetime(mes_referencia) + pd.DateOffset(months=1)).date()

    conn.commit()
    conn.close()
    clear_cache()

@st.cache_data(ttl=600, show_spinner=False)
def carregar_fatura(user_id, cartao_id, mes_fatura_str):
    conn = get_connection()
    sql = """
        SELECT * FROM lancamentos_cartao 
        WHERE user_id = %s AND cartao_id = %s AND mes_fatura = %s
    """
    df = pd.read_sql_query(sql, conn, params=(user_id, cartao_id, mes_fatura_str))
    conn.close()
    return df

def atualizar_item_fatura(user_id, id_item, nova_descricao, novo_valor, nova_data_compra):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE lancamentos_cartao
        SET descricao=%s, valor_parcela=%s, data_compra=%s
        WHERE id=%s AND user_id=%s
    ''', (nova_descricao, novo_valor, nova_data_compra, id_item, user_id))
    conn.commit()
    conn.close()
    clear_cache()

# --- CONTROLE DE PAGAMENTO DE FATURAS ---

def registrar_pagamento_fatura(user_id, cartao_id, mes_referencia, status, valor, data_pagamento):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO faturas_controle (user_id, cartao_id, mes_referencia, status, valor_pago, data_pagamento)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id, cartao_id, mes_referencia) 
        DO UPDATE SET status = EXCLUDED.status, valor_pago = EXCLUDED.valor_pago, data_pagamento = EXCLUDED.data_pagamento
    ''', (user_id, cartao_id, mes_referencia, status, valor, data_pagamento))
    conn.commit()
    conn.close()
    clear_cache()

def excluir_pagamento_fatura(user_id, cartao_id, mes_referencia):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        DELETE FROM faturas_controle 
        WHERE user_id=%s AND cartao_id=%s AND mes_referencia=%s
    ''', (user_id, cartao_id, mes_referencia))
    conn.commit()
    conn.close()
    clear_cache()

def obter_status_fatura(user_id, cartao_id, mes_referencia):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT status, valor_pago, data_pagamento FROM faturas_controle
        WHERE user_id = %s AND cartao_id = %s AND mes_referencia = %s
    ''', (user_id, cartao_id, mes_referencia))
    result = c.fetchone()
    conn.close()
    if result:
        return {"status": result[0], "valor": result[1], "data": result[2]}
    return None

# --- RECORRÊNCIAS ---

def salvar_recorrencia(user_id, nome, valor, categoria, dia_vencimento, tipo):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO recorrencias (user_id, nome, valor, categoria, dia_vencimento, tipo)
        VALUES (%s, %s, %s, %s, %s, %s)
    ''', (user_id, nome, valor, categoria, dia_vencimento, tipo))
    conn.commit()
    conn.close()
    clear_cache()

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
    clear_cache()

@st.cache_data(ttl=600, show_spinner=False)
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
    clear_cache()
    return True

# --- RESERVAS (COMPLETA E OTIMIZADA) ---

def salvar_reserva_conta(user_id, nome, tipo, indice, taxa, meta):
    conn = get_connection()
    c = conn.cursor()
    
    # 1. Tenta inserir com as colunas novas
    try:
        # Formata string de rentabilidade para exibição
        rentab_display = f"{taxa}% {indice}"
        c.execute('''
            INSERT INTO reservas (user_id, nome, tipo_aplicacao, indice, taxa, rentabilidade, meta_valor)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (user_id, nome, tipo, indice, taxa, rentab_display, meta))
        conn.commit()
    except Exception as e:
        conn.rollback()
        # Se falhar (colunas não existem), tenta criar as colunas e tenta de novo
        try:
            c.execute("ALTER TABLE reservas ADD COLUMN IF NOT EXISTS indice TEXT")
            c.execute("ALTER TABLE reservas ADD COLUMN IF NOT EXISTS taxa NUMERIC")
            c.execute("ALTER TABLE reservas ADD COLUMN IF NOT EXISTS rentabilidade TEXT")
            conn.commit()
            
            rentab_display = f"{taxa}% {indice}"
            c.execute('''
                INSERT INTO reservas (user_id, nome, tipo_aplicacao, indice, taxa, rentabilidade, meta_valor)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (user_id, nome, tipo, indice, taxa, rentab_display, meta))
            conn.commit()
        except:
            pass
    finally:
        conn.close()
        clear_cache()

@st.cache_data(ttl=600, show_spinner=False)
def carregar_reservas(user_id):
    conn = get_connection()
    # Tenta buscar com as novas colunas
    try:
        df = pd.read_sql_query("SELECT * FROM reservas WHERE user_id = %s", conn, params=(user_id,))
    except:
        conn.rollback()
        # Fallback se a migração falhou (muito raro se o salvar rodar antes)
        df = pd.read_sql_query("SELECT id, user_id, nome, tipo_aplicacao, saldo_atual, meta_valor FROM reservas WHERE user_id = %s", conn, params=(user_id,))
        df['rentabilidade'] = "-" 
    conn.close()
    return df

def excluir_reserva_conta(user_id, res_id):
    conn = get_connection()
    c = conn.cursor()
    # Apaga histórico primeiro
    c.execute("DELETE FROM reserva_transacoes WHERE reserva_id=%s AND user_id=%s", (res_id, user_id))
    c.execute("DELETE FROM reservas WHERE id=%s AND user_id=%s", (res_id, user_id))
    conn.commit()
    conn.close()
    clear_cache()

def salvar_transacao_reserva(user_id, res_id, data, tipo, valor, desc):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO reserva_transacoes (user_id, reserva_id, data, tipo, valor, descricao)
        VALUES (%s, %s, %s, %s, %s, %s)
    ''', (user_id, res_id, data, tipo, valor, desc))
    
    if tipo in ['Aporte', 'Rendimento']:
        c.execute("UPDATE reservas SET saldo_atual = saldo_atual + %s WHERE id=%s", (valor, res_id))
    elif tipo == 'Resgate':
        c.execute("UPDATE reservas SET saldo_atual = saldo_atual - %s WHERE id=%s", (valor, res_id))
        
    conn.commit()
    conn.close()
    clear_cache()

@st.cache_data(ttl=600, show_spinner=False)
def carregar_extrato_reserva(user_id):
    conn = get_connection()
    sql = """
        SELECT t.*, r.nome as nome_reserva 
        FROM reserva_transacoes t
        JOIN reservas r ON t.reserva_id = r.id
        WHERE t.user_id = %s
        ORDER BY t.data DESC
    """
    df = pd.read_sql_query(sql, conn, params=(user_id,))
    conn.close()
    return df

def migrar_dados_antigos_para_reserva(user_id):
    """
    Migração Inteligente V2:
    1. Cria/Recupera Reserva Geral.
    2. Busca Despesas (Aportes) e SOMA no saldo.
    3. Busca Receitas (Resgates) e SUBTRAI do saldo.
    """
    conn = get_connection()
    c = conn.cursor()
    
    # 1. Cria ou recupera Reserva Geral
    c.execute("SELECT id FROM reservas WHERE user_id=%s AND nome='Reserva Migrada (Geral)'", (user_id,))
    res = c.fetchone()
    
    if not res:
        # Se não existe, cria
        try:
            c.execute("INSERT INTO reservas (user_id, nome, tipo_aplicacao, indice, taxa, rentabilidade, meta_valor) VALUES (%s, 'Reserva Migrada (Geral)', 'Indefinido', 'CDI', 100, '100% CDI', 0) RETURNING id", (user_id,))
        except:
            conn.rollback()
            c.execute("INSERT INTO reservas (user_id, nome, tipo_aplicacao, meta_valor) VALUES (%s, 'Reserva Migrada (Geral)', 'Indefinido', 0) RETURNING id", (user_id,))
        res_id = c.fetchone()[0]
        conn.commit()
    else:
        res_id = res[0]
        c.execute("UPDATE reservas SET saldo_atual = 0 WHERE id=%s", (res_id,))
        c.execute("DELETE FROM reserva_transacoes WHERE reserva_id=%s", (res_id,))
        conn.commit()
    
    count = 0
    
    # 2. Busca e Migra APORTES (Despesas)
    df_aportes = pd.read_sql_query("""
        SELECT * FROM lancamentos 
        WHERE user_id = %s 
        AND tipo = 'Despesa'
        AND (categoria ILIKE '%%Reserva%%' OR categoria ILIKE '%%Investimento%%' OR categoria = 'Investimentos (Aportes)')
    """, conn, params=(user_id,))
    
    for _, row in df_aportes.iterrows():
        c.execute('''
            INSERT INTO reserva_transacoes (user_id, reserva_id, data, tipo, valor, descricao)
            VALUES (%s, %s, %s, 'Aporte', %s, %s)
        ''', (user_id, res_id, row['data'], row['valor'], f"Migrado: {row['descricao']}"))
        c.execute("UPDATE reservas SET saldo_atual = saldo_atual + %s WHERE id=%s", (row['valor'], res_id))
        c.execute("DELETE FROM lancamentos WHERE id=%s", (row['id'],))
        count += 1

    # 3. Busca e Migra RESGATES (Receitas)
    df_resgates = pd.read_sql_query("""
        SELECT * FROM lancamentos 
        WHERE user_id = %s 
        AND tipo = 'Receita'
        AND (categoria ILIKE '%%Resgate%%' OR categoria ILIKE '%%Reserva%%' OR categoria ILIKE '%%Investimento%%' OR categoria = 'Resgates')
    """, conn, params=(user_id,))
    
    for _, row in df_resgates.iterrows():
        c.execute('''
            INSERT INTO reserva_transacoes (user_id, reserva_id, data, tipo, valor, descricao)
            VALUES (%s, %s, %s, 'Resgate', %s, %s)
        ''', (user_id, res_id, row['data'], row['valor'], f"Migrado: {row['descricao']}"))
        c.execute("UPDATE reservas SET saldo_atual = saldo_atual - %s WHERE id=%s", (row['valor'], res_id))
        c.execute("DELETE FROM lancamentos WHERE id=%s", (row['id'],))
        count += 1
            
    conn.commit()
    conn.close()
    clear_cache()
    return count

# --- NOTIFICAÇÕES (LEITURA APENAS) ---

def buscar_pendencias_proximas(user_id):
    conn = get_connection()
    sql = """
        SELECT descricao, valor, data, conta 
        FROM lancamentos 
        WHERE user_id = %s 
        AND status IN ('Pendente', 'Agendado')
        AND data BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '1 day'
    """
    df = pd.read_sql_query(sql, conn, params=(user_id,))
    conn.close()
    return df

# --- PROJEÇÃO / SALDO FUTURO (LEITURAS OTIMIZADAS) ---

@st.cache_data(ttl=300, show_spinner=False)
def calcular_saldo_atual(user_id):
    """Retorna o saldo líquido atual (apenas contas correntes/carteira)"""
    conn = get_connection()
    df = pd.read_sql_query("SELECT tipo, valor FROM lancamentos WHERE user_id = %s AND status = 'Pago/Recebido'", conn, params=(user_id,))
    conn.close()
    
    receitas = df[df['tipo'] == 'Receita']['valor'].sum()
    despesas = df[df['tipo'] == 'Despesa']['valor'].sum()
    return receitas - despesas

@st.cache_data(ttl=300, show_spinner=False)
def buscar_faturas_futuras(user_id):
    """Agrupa as parcelas futuras de cartão por data de vencimento"""
    conn = get_connection()
    sql = """
        SELECT 
            lc.mes_fatura, 
            cc.dia_vencimento,
            SUM(lc.valor_parcela) as total_fatura
        FROM lancamentos_cartao lc
        JOIN cartoes_credito cc ON lc.cartao_id = cc.id
        WHERE lc.user_id = %s
        AND lc.mes_fatura >= CURRENT_DATE
        GROUP BY lc.mes_fatura, cc.dia_vencimento
    """
    df = pd.read_sql_query(sql, conn, params=(user_id,))
    conn.close()
    return df

@st.cache_data(ttl=300, show_spinner=False)
def buscar_metas_saldo_restante(user_id, mes, ano):
    """
    Calcula quanto falta gastar de cada meta no mês atual.
    """
    conn = get_connection()
    # 1. Busca Metas
    df_metas = pd.read_sql_query("SELECT categoria, valor_meta FROM metas WHERE user_id=%s AND mes=%s AND ano=%s", 
                                 conn, params=(user_id, mes, ano))
    if df_metas.empty:
        conn.close()
        return pd.DataFrame()

    # 2. Busca Gastos Reais
    sql_gastos = """
        SELECT categoria, SUM(valor) as gasto_real 
        FROM lancamentos 
        WHERE user_id=%s AND tipo='Despesa' 
        AND EXTRACT(MONTH FROM data) = %s AND EXTRACT(YEAR FROM data) = %s
        GROUP BY categoria
    """
    df_gastos = pd.read_sql_query(sql_gastos, conn, params=(user_id, mes, ano))
    conn.close()
    
    # 3. Cruza os dados
    df_final = pd.merge(df_metas, df_gastos, on='categoria', how='left')
    df_final['gasto_real'] = df_final['gasto_real'].fillna(0)
    df_final['restante'] = df_final['valor_meta'] - df_final['gasto_real']
    
    return df_final[df_final['restante'] > 0]