import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
from modules.database import salvar_investimento, carregar_investimentos, excluir_investimento, atualizar_investimento

# ... MANTENHA AS FUNÇÕES AUXILIARES (calcular_carteira, buscar_cotacoes) IGUAIS ...
# Vou colocar aqui apenas a função principal show_investimentos atualizada para economizar espaço, 
# mas no seu arquivo mantenha as funções auxiliares no topo.

def calcular_carteira(df):
    if df.empty: return pd.DataFrame()
    carteira = {}
    df = df.sort_values(by='data')
    for _, row in df.iterrows():
        ticker = row['ticker']; qtd = float(row['quantidade']); total = float(row['total_operacao'])
        tipo = row['tipo_operacao']; classe = row['classe']
        if ticker not in carteira: carteira[ticker] = {'qtd': 0, 'custo_total': 0.0, 'classe': classe}
        if tipo == 'Compra':
            carteira[ticker]['qtd'] += qtd; carteira[ticker]['custo_total'] += total
        elif tipo == 'Venda':
            pm = carteira[ticker]['custo_total'] / carteira[ticker]['qtd'] if carteira[ticker]['qtd'] > 0 else 0
            carteira[ticker]['qtd'] -= qtd; carteira[ticker]['custo_total'] -= (qtd * pm)
    dados = []
    for t, d in carteira.items():
        if d['qtd'] > 0: dados.append({'Ticker': t, 'Classe': d['classe'], 'Quantidade': d['qtd'], 'Preço Médio': d['custo_total']/d['qtd'], 'Custo Total': d['custo_total']})
    return pd.DataFrame(dados)

@st.cache_data(ttl=300)
def buscar_cotacoes(tickers):
    if not tickers: return {}
    validos = [t for t in tickers if len(t) < 7 or t.endswith(".SA")]
    if not validos: return {}
    try:
        ajustados = [t + ".SA" if not t.endswith(".SA") and len(t) < 6 else t for t in validos]
        dados = yf.download(ajustados, period="1d", progress=False)['Close']
        cotacoes = {}
        if isinstance(dados, pd.Series): cotacoes[validos[0]] = float(dados.iloc[-1])
        elif not dados.empty:
            ultimos = dados.iloc[-1]
            for o, a in zip(validos, ajustados):
                try: cotacoes[o] = float(ultimos[a])
                except: cotacoes[o] = 0.0
        return cotacoes
    except: return {}

def show_investimentos():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']

    st.header("📈 Gestão de Investimentos")
    
    tab_carteira, tab_novo, tab_gerenciar = st.tabs(["💼 Minha Carteira", "➕ Nova Operação", "📝 Gerenciar / Editar"])

    # ABA 1: CARTEIRA (Igual)
    with tab_carteira:
        df_transacoes = carregar_investimentos(user_id)
        if df_transacoes.empty:
            st.info("Nenhuma operação registrada.")
        else:
            df_custodia = calcular_carteira(df_transacoes)
            if df_custodia.empty: st.warning("Carteira zerada.")
            else:
                lista_tickers = df_custodia['Ticker'].tolist()
                with st.spinner("Atualizando..."): cotacoes = buscar_cotacoes(lista_tickers)
                
                df_custodia['Preço Atual'] = df_custodia.apply(lambda r: cotacoes.get(r['Ticker'], r['Preço Médio']), axis=1)
                df_custodia['Valor Atual'] = df_custodia['Quantidade'] * df_custodia['Preço Atual']
                df_custodia['Lucro/Prejuízo'] = df_custodia['Valor Atual'] - df_custodia['Custo Total']
                
                total_patrimonio = df_custodia['Valor Atual'].sum()
                st.metric("Patrimônio Total", f"R$ {total_patrimonio:,.2f}")
                
                st.dataframe(df_custodia, use_container_width=True, hide_index=True)

    # ABA 2: NOVA (Igual)
    with tab_novo:
        st.subheader("Registrar Operação")
        with st.form("form_invest"):
            c1, c2, c3 = st.columns(3)
            data = c1.date_input("Data", datetime.today())
            tipo = c2.selectbox("Tipo", ["Compra", "Venda"])
            classe = c3.selectbox("Classe", ["Renda Fixa", "Ação", "FII", "ETF", "Cripto"])
            
            c4, c5 = st.columns(2)
            ticker = c4.text_input("Código (Ticker)").upper().strip()
            qtd = c5.number_input("Quantidade", min_value=0.01, step=0.01)
            
            c6, c7 = st.columns(2)
            preco = c6.number_input("Preço Unitário", min_value=0.01)
            taxas = c7.number_input("Taxas", min_value=0.0)
            
            nota = st.text_input("Notas")
            
            if st.form_submit_button("Salvar"):
                total = (qtd * preco) + taxas if tipo == "Compra" else (qtd * preco) - taxas
                dados = {"data": data, "ticker": ticker, "tipo_operacao": tipo, "classe": classe, "quantidade": qtd, "preco_unitario": preco, "taxas": taxas, "total_operacao": total, "notas": nota}
                salvar_investimento(user_id, dados)
                st.success("Salvo!")
                st.rerun()

    # ABA 3: GERENCIAR / EDITAR (NOVA)
    with tab_gerenciar:
        st.subheader("Histórico de Transações")
        df_hist = carregar_investimentos(user_id)
        
        if not df_hist.empty:
            df_hist = df_hist.sort_values(by='data', ascending=False)
            
            opcoes_hist = df_hist.apply(lambda r: f"ID: {r['id']} | {r['ticker']} | {r['tipo_operacao']} {r['quantidade']}", axis=1)
            sel_hist = st.selectbox("Selecione para editar:", options=opcoes_hist)
            
            if sel_hist:
                id_edit = int(sel_hist.split(" |")[0].replace("ID: ", ""))
                d_atual = df_hist[df_hist['id'] == id_edit].iloc[0]
                
                with st.form(f"form_edit_inv_{id_edit}"):
                    ec1, ec2, ec3 = st.columns(3)
                    e_data = ec1.date_input("Data", value=d_atual['data'])
                    e_tipo = ec2.selectbox("Tipo", ["Compra", "Venda"], index=0 if d_atual['tipo_operacao']=="Compra" else 1)
                    e_classe = ec3.selectbox("Classe", ["Renda Fixa", "Ação", "FII", "ETF", "Cripto"], index=["Renda Fixa", "Ação", "FII", "ETF", "Cripto"].index(d_atual['classe']))
                    
                    ec4, ec5 = st.columns(2)
                    e_ticker = ec4.text_input("Ticker", value=d_atual['ticker'])
                    e_qtd = ec5.number_input("Qtd", value=float(d_atual['quantidade']))
                    
                    ec6, ec7 = st.columns(2)
                    e_preco = ec6.number_input("Preço", value=float(d_atual['preco_unitario']))
                    e_taxas = ec7.number_input("Taxas", value=float(d_atual['taxas']) if pd.notnull(d_atual['taxas']) else 0.0)
                    
                    e_nota = st.text_input("Notas", value=d_atual['notas'] if pd.notnull(d_atual['notas']) else "")
                    
                    if st.form_submit_button("💾 Atualizar Transação"):
                        e_total = (e_qtd * e_preco) + e_taxas if e_tipo == "Compra" else (e_qtd * e_preco) - e_taxas
                        dados_up = {"data": e_data, "ticker": e_ticker, "tipo_operacao": e_tipo, "classe": e_classe, "quantidade": e_qtd, "preco_unitario": e_preco, "taxas": e_taxas, "total_operacao": e_total, "notas": e_nota}
                        atualizar_investimento(user_id, id_edit, dados_up)
                        st.success("Atualizado!")
                        st.rerun()
                
                st.markdown("---")
                if st.button("🗑️ Excluir esta operação"):
                    excluir_investimento(user_id, id_edit)
                    st.rerun()
            
            st.dataframe(df_hist, use_container_width=True, hide_index=True)