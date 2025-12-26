import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime
from modules.database import carregar_dados

def show_dashboard():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']

    st.header("📊 Dashboard Financeiro")
    
    df = carregar_dados(user_id)
    
    if df.empty:
        st.info("Adicione lançamentos para ver o dashboard.")
        return

    # Processamento Inicial
    df['data'] = pd.to_datetime(df['data'])
    df['Mes'] = df['data'].dt.month
    df['Ano'] = df['data'].dt.year
    
    # Cores personalizadas
    color_map = {'Receita': '#00CC96', 'Despesa': '#EF553B'}

    # Abas Principais
    tab_total, tab_anual, tab_mensal = st.tabs(["🌎 Visão Total (Acumulado)", "📅 Visão Anual", "📆 Visão Mensal"])

    # ===================================================
    # ABA 1: VISÃO TOTAL (Tudo que já aconteceu)
    # ===================================================
    with tab_total:
        st.markdown("### Resumo Geral (Desde o Início)")
        
        total_rec = df[df['tipo'] == 'Receita']['valor'].sum()
        total_desp = df[df['tipo'] == 'Despesa']['valor'].sum()
        saldo_geral = total_rec - total_desp
        
        # Big Numbers
        c1, c2, c3 = st.columns(3)
        c1.metric("Receita Total Histórica", f"R$ {total_rec:,.2f}")
        c2.metric("Despesa Total Histórica", f"R$ {total_desp:,.2f}", delta_color="inverse")
        c3.metric("Saldo Atual Acumulado", f"R$ {saldo_geral:,.2f}", delta=f"{saldo_geral:,.2f}")
        
        st.divider()
        
        # Gráfico de Evolução Patrimonial (Linha do Tempo)
        df_tempo = df.groupby(['Ano', 'Mes', 'tipo'])['valor'].sum().reset_index()
        # Cria uma coluna de data fictícia (dia 1) para o gráfico entender a ordem cronológica
        df_tempo['Data_Ref'] = pd.to_datetime(df_tempo['Ano'].astype(str) + '-' + df_tempo['Mes'].astype(str) + '-01')
        df_tempo = df_tempo.sort_values('Data_Ref')
        
        fig_evolucao = px.line(
            df_tempo, x='Data_Ref', y='valor', color='tipo',
            title='Evolução de Receitas e Despesas no Tempo',
            color_discrete_map=color_map, template="plotly_dark", markers=True
        )
        st.plotly_chart(fig_evolucao, use_container_width=True)

    # ===================================================
    # ABA 2: VISÃO ANUAL
    # ===================================================
    with tab_anual:
        anos = sorted(df['Ano'].unique().tolist(), reverse=True)
        sel_ano = st.selectbox("Selecione o Ano", anos, key="sb_ano_dash")
        
        df_ano = df[df['Ano'] == sel_ano]
        
        if df_ano.empty:
            st.warning("Sem dados neste ano.")
        else:
            rec_ano = df_ano[df_ano['tipo'] == 'Receita']['valor'].sum()
            desp_ano = df_ano[df_ano['tipo'] == 'Despesa']['valor'].sum()
            saldo_ano = rec_ano - desp_ano
            poupanca_ano = (saldo_ano / rec_ano * 100) if rec_ano > 0 else 0
            
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Receita (Ano)", f"R$ {rec_ano:,.2f}")
            k2.metric("Despesa (Ano)", f"R$ {desp_ano:,.2f}")
            k3.metric("Saldo (Ano)", f"R$ {saldo_ano:,.2f}")
            k4.metric("Taxa de Poupança", f"{poupanca_ano:.1f}%")
            
            st.divider()
            
            g1, g2 = st.columns(2)
            
            # Gráfico Barras Mês a Mês
            with g1:
                df_barras = df_ano.groupby(['Mes', 'tipo'])['valor'].sum().reset_index()
                mapa_mes = {1:'Jan', 2:'Fev', 3:'Mar', 4:'Abr', 5:'Mai', 6:'Jun', 7:'Jul', 8:'Ago', 9:'Set', 10:'Out', 11:'Nov', 12:'Dez'}
                df_barras['NomeMes'] = df_barras['Mes'].map(mapa_mes)
                
                fig_bar = px.bar(
                    df_barras, x='NomeMes', y='valor', color='tipo', barmode='group',
                    title=f"Fluxo Mensal em {sel_ano}",
                    color_discrete_map=color_map, template="plotly_dark",
                    category_orders={"NomeMes": list(mapa_mes.values())}
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            
            # Gráfico de Categorias (Rosca) - Só Despesas
            with g2:
                df_cat = df_ano[df_ano['tipo']=='Despesa'].groupby('categoria')['valor'].sum().reset_index()
                if not df_cat.empty:
                    fig_pie = px.pie(
                        df_cat, values='valor', names='categoria', hole=0.4,
                        title=f"Gastos por Categoria ({sel_ano})",
                        template="plotly_dark", color_discrete_sequence=px.colors.sequential.RdBu
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("Sem despesas para gráfico.")

    # ===================================================
    # ABA 3: VISÃO MENSAL
    # ===================================================
    with tab_mensal:
        c_filt1, c_filt2 = st.columns(2)
        
        # Filtros independentes para esta aba
        sel_ano_m = c_filt1.selectbox("Ano", anos, key="sb_ano_mes")
        
        meses_disp = {k:v for k,v in {1:"Janeiro", 2:"Fevereiro", 3:"Março", 4:"Abril", 5:"Maio", 6:"Junho", 7:"Julho", 8:"Agosto", 9:"Setembro", 10:"Outubro", 11:"Novembro", 12:"Dezembro"}.items()}
        mes_atual_idx = datetime.now().month - 1
        sel_mes_nome = c_filt2.selectbox("Mês", list(meses_disp.values()), index=mes_atual_idx, key="sb_mes_mes")
        sel_mes_num = [k for k,v in meses_disp.items() if v == sel_mes_nome][0]
        
        df_mes = df[(df['Ano'] == sel_ano_m) & (df['Mes'] == sel_mes_num)]
        
        st.markdown(f"### Detalhes de: {sel_mes_nome}/{sel_ano_m}")
        
        if df_mes.empty:
            st.warning("Sem movimentações neste período.")
        else:
            rec_m = df_mes[df_mes['tipo'] == 'Receita']['valor'].sum()
            desp_m = df_mes[df_mes['tipo'] == 'Despesa']['valor'].sum()
            saldo_m = rec_m - desp_m
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Receita", f"R$ {rec_m:,.2f}")
            m2.metric("Despesa", f"R$ {desp_m:,.2f}", delta_color="inverse")
            m3.metric("Saldo", f"R$ {saldo_m:,.2f}", delta=f"{saldo_m:,.2f}")
            
            st.divider()
            
            # Tabela de Extrato
            st.dataframe(
                df_mes[['data', 'descricao', 'categoria', 'valor', 'tipo', 'conta']].sort_values('data'),
                use_container_width=True, hide_index=True,
                column_config={"data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"), "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")}
            )