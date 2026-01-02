import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
from modules.database import carregar_dados, carregar_reservas

# ==============================================================================
# 🎛️ PAINEL DE CONTROLE (CONFIGURAÇÕES DE UI & DESIGN)
# ==============================================================================

# --- TEXTOS E LABELS ---
CONFIG_TXT = {
    "titulo_pag": "📊 Dashboard Financeiro",
    "titulo_evolucao": "Evolução Receita/Despesa em Caixa",
    "msg_vazio": "Sem dados para exibir neste período.",
    "tooltip_receita": "Entradas",
    "tooltip_despesa": "Saídas"
}

# --- CORES (SISTEMA HSL) ---
# Dica: HSL(Matiz 0-360, Saturação%, Luminosidade%)
CORES = {
    # Cores Semânticas
    "receita": "hsl(154, 65%, 55%)",    # Verde Menta Vibrante (era #00CC96)
    "despesa": "hsl(6, 100%, 60%)",      # Vermelho Coral (era #EF553B)
    "saldo_pos": "hsl(154, 65%, 55%)",
    "saldo_neg": "hsl(6, 85%, 60%)",
    
    # Cores de Interface
    "texto_geral": "hsl(0, 0%, 90%)",
    "fundo_transparente": "rgba(0,0,0,0)", # Essencial para dashboards modernos
    "grid_color": "hsl(220, 10%, 20%)"     # Cinza azulado muito escuro (para linhas sutis se precisar)
}

# Mapa de Cores para Plotly (Linkando nomes do banco de dados às cores HSL)
MAPA_CORES_PLOTLY = {
    'Receita': CORES['receita'], 
    'Despesa': CORES['despesa']
}

# ==============================================================================
# 🛠️ FUNÇÕES LÓGICAS
# ==============================================================================

def show_dashboard():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']

    st.header(CONFIG_TXT['titulo_pag'])
    
    df = carregar_dados(user_id)
    
    if df.empty:
        st.info("Adicione lançamentos para ver o dashboard.")
        return

    # Processamento Inicial
    df['data'] = pd.to_datetime(df['data'])
    df['Mes'] = df['data'].dt.month
    df['Ano'] = df['data'].dt.year
    df['Dia'] = df['data'].dt.day
    
    tab_total, tab_anual, tab_mensal = st.tabs(["🌎 Visão Total (Acumulado)", "📅 Visão Anual", "📆 Visão Mensal"])

    # ===================================================
    # ABA 1: VISÃO TOTAL (COM GRÁFICO NOVO)
    # ===================================================
    with tab_total:
        # 1. Dados do Caixa (Lançamentos)
        total_rec = df[df['tipo'] == 'Receita']['valor'].sum()
        total_desp = df[df['tipo'] == 'Despesa']['valor'].sum()
        saldo_caixa = total_rec - total_desp
        
        # 2. Dados da Reserva
        df_reserva = carregar_reservas(user_id)
        saldo_reserva = df_reserva['saldo_atual'].sum() if not df_reserva.empty else 0.0
        
        # 3. Total Geral
        total_liquidez = saldo_caixa + saldo_reserva

        # --- SEÇÃO 1: CARDS (Métricas) ---
        st.markdown("### 💰 Posição Geral")
        c_tot1, c_tot2, c_tot3 = st.columns(3)
        c_tot1.metric("Saldo em Caixa", f"R$ {saldo_caixa:,.2f}", help="Disponível para uso imediato")
        c_tot2.metric("Reservas Acumuladas", f"R$ {saldo_reserva:,.2f}", delta="Patrimônio", help="Total investido/guardado")
        c_tot3.metric("Patrimônio Líquido", f"R$ {total_liquidez:,.2f}", help="Soma total")
        
        st.divider()

        # --- SEÇÃO 2: GRÁFICO CURVO (SPLINE) ---
        st.markdown(f"### 📉 {CONFIG_TXT['titulo_evolucao']}")
        
        # Preparação dos dados para o gráfico
        df_tempo = df.groupby(['Ano', 'Mes', 'tipo'])['valor'].sum().reset_index()
        df_tempo['Data_Ref'] = pd.to_datetime(df_tempo['Ano'].astype(str) + '-' + df_tempo['Mes'].astype(str) + '-01')
        df_tempo = df_tempo.sort_values('Data_Ref')
        
        # Criação do Gráfico
        fig_evolucao = px.line(
            df_tempo, 
            x='Data_Ref', 
            y='valor', 
            color='tipo',
            # ORDEM DAS CAMADAS: Receita primeiro, Despesa por cima (último da lista fica em cima)
            category_orders={"tipo": ["Receita", "Despesa"]},
            title=None, # Título removido do gráfico (já está no markdown)
            color_discrete_map=MAPA_CORES_PLOTLY,
            # spline = Curvas suaves
            line_shape='spline',
            render_mode='svg' # Melhora a renderização das curvas
        )

        # Customização Avançada (O "Tratamento de Beleza")
        fig_evolucao.update_traces(
            fill='tozeroy',     # Preenche a área até o eixo Y=0
            mode='lines',       # Apenas linhas (sem bolinhas/markers para ficar mais clean)
            line=dict(width=3), # Linha um pouco mais grossa
            opacity=0.7         # Transparência geral (linha + preenchimento) para ver sobreposição
        )
        
        fig_evolucao.update_layout(
            template="plotly_dark",
            paper_bgcolor=CORES["fundo_transparente"],
            plot_bgcolor=CORES["fundo_transparente"],
            xaxis=dict(
                showgrid=False,       # Remove grade vertical
                title=None,           # Remove label "Data_Ref"
                showline=True,        # Mostra linha do eixo
                linecolor="#333"
            ),
            yaxis=dict(
                showgrid=True,        # Mantém grade horizontal sutil para leitura de valor
                gridcolor=CORES["grid_color"],
                gridwidth=0.5,
                title=None,
                zeroline=False,
                tickprefix="R$ "
            ),
            legend=dict(
                orientation="h",      # Legenda horizontal
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                title=None            # Remove título da legenda
            ),
            margin=dict(l=0, r=0, t=30, b=0) # Margens otimizadas
        )
        
        st.plotly_chart(fig_evolucao, use_container_width=True)

        # Métricas simples abaixo do gráfico
        k1, k2 = st.columns(2)
        k1.metric("Total Entradas (Histórico)", f"R$ {total_rec:,.2f}")
        k2.metric("Total Saídas (Histórico)", f"R$ {total_desp:,.2f}")

    # ===================================================
    # ABA 2: VISÃO ANUAL (Mantida funcional, com cores novas)
    # ===================================================
    with tab_anual:
        anos = sorted(df['Ano'].unique().tolist(), reverse=True)
        sel_ano = st.selectbox("Selecione o Ano", anos, key="sb_ano_dash")
        
        df_ano = df[df['Ano'] == sel_ano]
        
        if df_ano.empty:
            st.warning(CONFIG_TXT['msg_vazio'])
        else:
            rec_ano = df_ano[df_ano['tipo'] == 'Receita']['valor'].sum()
            desp_ano = df_ano[df_ano['tipo'] == 'Despesa']['valor'].sum()
            saldo_ano = rec_ano - desp_ano
            poupanca_ano = (saldo_ano / rec_ano * 100) if rec_ano > 0 else 0
            
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Receita", f"R$ {rec_ano:,.2f}")
            k2.metric("Despesa", f"R$ {desp_ano:,.2f}")
            k3.metric("Saldo", f"R$ {saldo_ano:,.2f}")
            k4.metric("Poupança", f"{poupanca_ano:.1f}%")
            
            st.divider()
            
            g1, g2 = st.columns(2)
            
            with g1:
                df_barras = df_ano.groupby(['Mes', 'tipo'])['valor'].sum().reset_index()
                mapa_mes = {1:'Jan', 2:'Fev', 3:'Mar', 4:'Abr', 5:'Mai', 6:'Jun', 7:'Jul', 8:'Ago', 9:'Set', 10:'Out', 11:'Nov', 12:'Dez'}
                df_barras['NomeMes'] = df_barras['Mes'].map(mapa_mes)
                
                fig_bar = px.bar(
                    df_barras, x='NomeMes', y='valor', color='tipo', barmode='group',
                    title=f"Fluxo Mensal ({sel_ano})",
                    color_discrete_map=MAPA_CORES_PLOTLY, template="plotly_dark",
                    category_orders={"NomeMes": list(mapa_mes.values())}
                )
                fig_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_bar, use_container_width=True)
            
            with g2:
                # Mantendo o gráfico de pizza antigo por enquanto, só atualizando cores
                df_cat = df_ano[df_ano['tipo']=='Despesa'].groupby('categoria')['valor'].sum().reset_index()
                if not df_cat.empty:
                    fig_pie = px.pie(
                        df_cat, values='valor', names='categoria', hole=0.4,
                        title=f"Gastos por Categoria ({sel_ano})",
                        template="plotly_dark", color_discrete_sequence=px.colors.sequential.RdBu
                    )
                    fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("Sem despesas para gráfico.")

    # ===================================================
    # ABA 3: VISÃO MENSAL (Mantida funcional)
    # ===================================================
    with tab_mensal:
        c_filt1, c_filt2 = st.columns(2)
        sel_ano_m = c_filt1.selectbox("Ano", anos, key="sb_ano_mes")
        meses_disp = {k:v for k,v in {1:"Janeiro", 2:"Fevereiro", 3:"Março", 4:"Abril", 5:"Maio", 6:"Junho", 7:"Julho", 8:"Agosto", 9:"Setembro", 10:"Outubro", 11:"Novembro", 12:"Dezembro"}.items()}
        mes_atual_idx = datetime.now().month - 1
        sel_mes_nome = c_filt2.selectbox("Mês", list(meses_disp.values()), index=mes_atual_idx, key="sb_mes_mes")
        sel_mes_num = [k for k,v in meses_disp.items() if v == sel_mes_nome][0]
        
        df_mes = df[(df['Ano'] == sel_ano_m) & (df['Mes'] == sel_mes_num)]
        
        if df_mes.empty:
            st.warning(CONFIG_TXT['msg_vazio'])
        else:
            rec_m = df_mes[df_mes['tipo'] == 'Receita']['valor'].sum()
            desp_m = df_mes[df_mes['tipo'] == 'Despesa']['valor'].sum()
            saldo_m = rec_m - desp_m
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Receita", f"R$ {rec_m:,.2f}")
            m2.metric("Despesa", f"R$ {desp_m:,.2f}")
            m3.metric("Saldo", f"R$ {saldo_m:,.2f}", delta=f"{saldo_m:,.2f}")
            
            st.divider()
            
            gm1, gm2 = st.columns(2)
            
            with gm1:
                df_dias = df_mes.groupby(['Dia', 'tipo'])['valor'].sum().reset_index()
                fig_bar_dia = px.bar(
                    df_dias, x='Dia', y='valor', color='tipo', barmode='group',
                    title=f"Diário ({sel_mes_nome})",
                    color_discrete_map=MAPA_CORES_PLOTLY, template="plotly_dark"
                )
                fig_bar_dia.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_bar_dia, use_container_width=True)

            with gm2:
                df_cat_mes = df_mes[df_mes['tipo']=='Despesa'].groupby('categoria')['valor'].sum().reset_index()
                if not df_cat_mes.empty:
                    fig_pie_mes = px.pie(
                        df_cat_mes, values='valor', names='categoria', hole=0.4,
                        title=f"Categorias ({sel_mes_nome})",
                        template="plotly_dark", color_discrete_sequence=px.colors.sequential.RdBu
                    )
                    fig_pie_mes.update_layout(paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_pie_mes, use_container_width=True)
                else:
                    st.info("Sem despesas.")
            
            st.dataframe(
                df_mes[['data', 'descricao', 'categoria', 'valor', 'tipo', 'conta']].sort_values('data'),
                use_container_width=True, hide_index=True,
                column_config={"data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"), "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")}
            )