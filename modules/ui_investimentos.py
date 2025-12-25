import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
from modules.database import salvar_investimento, carregar_investimentos, excluir_investimento

def calcular_carteira(df):
    if df.empty:
        return pd.DataFrame()

    carteira = {}
    df = df.sort_values(by='data')

    for _, row in df.iterrows():
        ticker = row['ticker']
        qtd = row['quantidade']
        # Converte para float para garantir cálculo
        preco = float(row['preco_unitario'])
        taxas = float(row['taxas']) if row['taxas'] else 0.0
        total = float(row['total_operacao'])
        
        tipo = row['tipo_operacao']
        classe = row['classe']

        if ticker not in carteira:
            carteira[ticker] = {'qtd': 0, 'custo_total': 0.0, 'classe': classe}

        if tipo == 'Compra':
            carteira[ticker]['qtd'] += qtd
            carteira[ticker]['custo_total'] += total
        elif tipo == 'Venda':
            preco_medio_atual = carteira[ticker]['custo_total'] / carteira[ticker]['qtd'] if carteira[ticker]['qtd'] > 0 else 0
            carteira[ticker]['qtd'] -= qtd
            carteira[ticker]['custo_total'] -= (qtd * preco_medio_atual)

    dados_finais = []
    for ticker, dados in carteira.items():
        if dados['qtd'] > 0:
            pm = dados['custo_total'] / dados['qtd']
            dados_finais.append({
                'Ticker': ticker,
                'Classe': dados['classe'],
                'Quantidade': dados['qtd'],
                'Preço Médio': pm,
                'Custo Total': dados['custo_total']
            })
    return pd.DataFrame(dados_finais)

@st.cache_data(ttl=300)
def buscar_cotacoes(tickers):
    if not tickers:
        return {}
    
    tickers_validos = [t for t in tickers if len(t) < 7 or t.endswith(".SA")]
    if not tickers_validos:
        return {}

    try:
        tickers_ajustados = [t + ".SA" if not t.endswith(".SA") and len(t) < 6 else t for t in tickers_validos]
        dados = yf.download(tickers_ajustados, period="1d", progress=False)['Close']
        
        cotacoes = {}
        if isinstance(dados, pd.Series):
             val = dados.iloc[-1]
             cotacoes[tickers_validos[0]] = float(val)
        elif not dados.empty:
            ultimos_precos = dados.iloc[-1]
            for t_original, t_ajustado in zip(tickers_validos, tickers_ajustados):
                try:
                    cotacoes[t_original] = float(ultimos_precos[t_ajustado])
                except:
                    cotacoes[t_original] = 0.0
        return cotacoes
    except Exception as e:
        return {}

def show_investimentos():
    # --- PEGAR USUÁRIO LOGADO ---
    if 'user_id' not in st.session_state:
        return
    user_id = st.session_state['user_id']

    st.header("📈 Gestão de Investimentos")
    
    tab_carteira, tab_novo, tab_historico = st.tabs(["💼 Minha Carteira", "➕ Nova Operação", "📝 Histórico"])

    # --- ABA 1: CARTEIRA ---
    with tab_carteira:
        # ATUALIZADO: Passando user_id
        df_transacoes = carregar_investimentos(user_id)
        
        if df_transacoes.empty:
            st.info("Nenhuma operação registrada.")
        else:
            df_custodia = calcular_carteira(df_transacoes)
            
            if df_custodia.empty:
                st.warning("Carteira zerada.")
            else:
                lista_tickers = df_custodia['Ticker'].tolist()
                
                with st.spinner(f"Atualizando valores..."):
                    cotacoes = buscar_cotacoes(lista_tickers)
                
                def obter_preco_atual(row):
                    preco_online = cotacoes.get(row['Ticker'], 0.0)
                    if preco_online > 0:
                        return preco_online
                    else:
                        return row['Preço Médio']

                df_custodia['Preço Atual'] = df_custodia.apply(obter_preco_atual, axis=1)
                df_custodia['Valor Atual'] = df_custodia['Quantidade'] * df_custodia['Preço Atual']
                df_custodia['Lucro/Prejuízo'] = df_custodia['Valor Atual'] - df_custodia['Custo Total']
                
                df_custodia['Var %'] = df_custodia.apply(
                    lambda x: (x['Lucro/Prejuízo'] / x['Custo Total'] * 100) if x['Custo Total'] > 0 else 0, axis=1
                )

                patrimonio_total = df_custodia['Valor Atual'].sum()
                custo_total = df_custodia['Custo Total'].sum()
                lucro_total = patrimonio_total - custo_total
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Patrimônio Total", f"R$ {patrimonio_total:,.2f}")
                c2.metric("Total Investido", f"R$ {custo_total:,.2f}")
                c3.metric("Lucro / Prejuízo", f"R$ {lucro_total:,.2f}", 
                          delta=f"{(lucro_total/custo_total)*100:.2f}%" if custo_total > 0 else "0%")
                
                st.divider()
                
                g1, g2 = st.columns([1, 2])
                with g1:
                    fig = px.pie(
                        df_custodia, 
                        values='Valor Atual', 
                        names='Classe', 
                        title='Alocação da Carteira', 
                        hole=0.4,
                        template="plotly_dark"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with g2:
                    st.subheader("Meus Ativos")
                    st.dataframe(
                        df_custodia.style.format({
                            "Preço Médio": "R$ {:.2f}",
                            "Preço Atual": "R$ {:.2f}",
                            "Custo Total": "R$ {:.2f}",
                            "Valor Atual": "R$ {:.2f}",
                            "Lucro/Prejuízo": "R$ {:.2f}",
                            "Var %": "{:.2f}%"
                        }),
                        use_container_width=True,
                        hide_index=True
                    )

    # --- ABA 2: NOVA OPERAÇÃO ---
    with tab_novo:
        st.subheader("Registrar Operação")
        st.caption("Para Caixinhas/Reserva: Use um código próprio (Ex: RES_NUBANK) e selecione Classe 'Renda Fixa'.")
        
        with st.form("form_invest"):
            c1, c2, c3 = st.columns(3)
            data = c1.date_input("Data", datetime.today())
            tipo = c2.selectbox("Tipo", ["Compra", "Venda"])
            classe = c3.selectbox("Classe", ["Renda Fixa", "Ação", "FII", "ETF", "Cripto"])
            
            c4, c5 = st.columns(2)
            ticker = c4.text_input("Código (Ticker)", placeholder="Ex: PETR4 ou RES_NUBANK").upper().strip()
            qtd = c5.number_input("Quantidade", min_value=1.0, step=0.01, format="%.2f")
            
            c6, c7 = st.columns(2)
            preco = c6.number_input("Preço Unitário (R$)", min_value=0.01, format="%.2f")
            taxas = c7.number_input("Taxas (R$)", min_value=0.00, format="%.2f")
            
            total_calc = (qtd * preco) + taxas if tipo == "Compra" else (qtd * preco) - taxas
            st.info(f"💰 Valor Total: **R$ {total_calc:,.2f}**")
            
            nota = st.text_input("Notas")
            
            if st.form_submit_button("Salvar", type="primary"):
                if not ticker:
                    st.error("Digite um código para o ativo!")
                else:
                    dados = {
                        "data": data.strftime("%Y-%m-%d"),
                        "ticker": ticker,
                        "tipo_operacao": tipo,
                        "classe": classe,
                        "quantidade": qtd,
                        "preco_unitario": preco,
                        "taxas": taxas,
                        "total_operacao": total_calc,
                        "notas": nota
                    }
                    # ATUALIZADO: Passando user_id
                    salvar_investimento(user_id, dados)
                    st.success("Salvo com sucesso!")
                    st.rerun()

    # --- ABA 3: HISTÓRICO ---
    with tab_historico:
        st.subheader("Histórico")
        # ATUALIZADO: Passando user_id
        df_hist = carregar_investimentos(user_id)
        if not df_hist.empty:
            df_hist = df_hist.sort_values(by='data', ascending=False)
            st.dataframe(
                df_hist, 
                use_container_width=True,
                column_config={
                    "id": st.column_config.NumberColumn("ID", format="%d"),
                    "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                    "preco_unitario": st.column_config.NumberColumn("Preço", format="R$ %.2f"),
                    "total_operacao": st.column_config.NumberColumn("Total", format="R$ %.2f"),
                }
            )
            col_del1, col_del2 = st.columns([3, 1])
            id_del = col_del1.number_input("ID para excluir", min_value=0, step=1)
            if col_del2.button("🗑️ Excluir"):
                # ATUALIZADO: Passando user_id
                if excluir_investimento(user_id, id_del):
                    st.success("Excluído.")
                    st.rerun()
                else:
                    st.error("Erro ao excluir (ID não encontrado ou não pertence a você).")