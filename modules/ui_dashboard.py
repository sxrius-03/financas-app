import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime
from modules.database import carregar_dados

def show_dashboard():
    # --- PEGAR USUÁRIO LOGADO ---
    if 'user_id' not in st.session_state:
        return
    user_id = st.session_state['user_id']

    st.header("📊 Dashboard Financeiro")
    
    # ATUALIZADO: Passando user_id
    df = carregar_dados(user_id)
    
    if df.empty:
        st.info("Nenhum dado para exibir. Vá em 'Lançamentos' e adicione o primeiro registro.")
        return

    # Tratamento de dados
    df['data'] = pd.to_datetime(df['data'])
    df['Mes'] = df['data'].dt.month
    df['Ano'] = df['data'].dt.year

    # --- FILTROS LATERAIS ---
    st.sidebar.header("📅 Filtros")
    
    anos_disponiveis = sorted(df['Ano'].unique().tolist(), reverse=True)
    ano_atual_real = datetime.now().year
    if ano_atual_real not in anos_disponiveis:
        anos_disponiveis.insert(0, ano_atual_real)
        
    ano_selecionado = st.sidebar.selectbox("Selecione o Ano", anos_disponiveis)
    
    meses_map = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    
    mes_atual_real = datetime.now().month
    idx_padrao = mes_atual_real - 1 if 1 <= mes_atual_real <= 12 else 0
    
    nome_mes_selecionado = st.sidebar.selectbox(
        "Selecione o Mês (Para Visão Mensal)", 
        list(meses_map.values()), 
        index=idx_padrao
    )
    mes_selecionado = [k for k, v in meses_map.items() if v == nome_mes_selecionado][0]

    # --- PREPARAÇÃO DOS DADOS ---
    df_ano = df[df['Ano'] == ano_selecionado]
    df_mes = df[(df['Ano'] == ano_selecionado) & (df['Mes'] == mes_selecionado)]

    # --- CRIAÇÃO DAS ABAS ---
    tab_mensal, tab_anual = st.tabs(["📅 Visão Mensal", "📆 Visão Anual Completa"])

    # ===================================================
    # ABA 1: VISÃO MENSAL (Micro)
    # ===================================================
    with tab_mensal:
        st.markdown(f"### Resumo de: **{nome_mes_selecionado}/{ano_selecionado}**")
        
        rec_mes = df_mes[df_mes['tipo'] == 'Receita']['valor'].sum()
        desp_mes = df_mes[df_mes['tipo'] == 'Despesa']['valor'].sum()
        saldo_mes = rec_mes - desp_mes
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Receitas (Mês)", f"R$ {rec_mes:,.2f}")
        c2.metric("Despesas (Mês)", f"R$ {desp_mes:,.2f}", delta_color="inverse")
        c3.metric("Saldo (Mês)", f"R$ {saldo_mes:,.2f}", delta=f"{saldo_mes:,.2f}")
        
        st.divider()

        if not df_mes.empty:
            df_desp_mes = df_mes[df_mes['tipo'] == 'Despesa']
            if not df_desp_mes.empty:
                fig_pie_mes = px.pie(
                    df_desp_mes, 
                    values='valor', 
                    names='categoria', 
                    title=f'Para onde foi seu dinheiro em {nome_mes_selecionado}?',
                    hole=0.5,
                    template="plotly_dark",
                    color_discrete_sequence=px.colors.sequential.RdBu
                )
                fig_pie_mes.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_pie_mes, use_container_width=True)
            else:
                st.info("Nenhuma despesa registrada neste mês.")
        else:
            st.warning("Sem dados para este mês.")

    # ===================================================
    # ABA 2: VISÃO ANUAL (Macro)
    # ===================================================
    with tab_anual:
        st.markdown(f"### Panorama Geral de **{ano_selecionado}**")
        
        if df_ano.empty:
            st.warning(f"Não há nenhum dado registrado em {ano_selecionado}.")
        else:
            rec_ano = df_ano[df_ano['tipo'] == 'Receita']['valor'].sum()
            desp_ano = df_ano[df_ano['tipo'] == 'Despesa']['valor'].sum()
            saldo_ano = rec_ano - desp_ano
            taxa_poupanca = (saldo_ano / rec_ano * 100) if rec_ano > 0 else 0
            
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Receita Total (Ano)", f"R$ {rec_ano:,.2f}")
            k2.metric("Despesa Total (Ano)", f"R$ {desp_ano:,.2f}", delta_color="inverse")
            k3.metric("Saldo Acumulado", f"R$ {saldo_ano:,.2f}", delta=f"{saldo_ano:,.2f}")
            k4.metric("Taxa de Poupança", f"{taxa_poupanca:.1f}%", help="Quanto da sua renda sobrou no ano")
            
            st.divider()
            
            g_col1, g_col2 = st.columns(2)
            
            with g_col1:
                st.subheader("Categorias (Ano Todo)")
                df_desp_ano = df_ano[df_ano['tipo'] == 'Despesa']
                
                if not df_desp_ano.empty:
                    df_pie_ano = df_desp_ano.groupby('categoria')['valor'].sum().reset_index()
                    fig_pie_ano = px.pie(
                        df_pie_ano, 
                        values='valor', 
                        names='categoria', 
                        hole=0.5,
                        template="plotly_dark",
                        color_discrete_sequence=px.colors.sequential.RdBu
                    )
                    fig_pie_ano.update_layout(showlegend=False)
                    fig_pie_ano.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_pie_ano, use_container_width=True)
                else:
                    st.info("Sem despesas no ano.")

            with g_col2:
                st.subheader("Evolução Mensal")
                df_evolucao = df_ano.groupby(['Mes', 'tipo'])['valor'].sum().reset_index()
                
                mapa_meses_curto = {1:'Jan', 2:'Fev', 3:'Mar', 4:'Abr', 5:'Mai', 6:'Jun', 7:'Jul', 8:'Ago', 9:'Set', 10:'Out', 11:'Nov', 12:'Dez'}
                df_evolucao['Mês'] = df_evolucao['Mes'].map(mapa_meses_curto)
                
                fig_bar = px.bar(
                    df_evolucao, 
                    x='Mês', 
                    y='valor', 
                    color='tipo', 
                    barmode='group',
                    template="plotly_dark",
                    color_discrete_map={'Receita': '#00CC96', 'Despesa': '#EF553B'},
                    category_orders={"Mês": ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]}
                )
                st.plotly_chart(fig_bar, use_container_width=True)