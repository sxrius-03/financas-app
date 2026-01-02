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
CONFIG_UI = {
    "GERAL": {
        "titulo_pag": "📊 Dashboard Financeiro",
        "msg_vazio": "Sem dados para exibir neste período."
    },
    "VISAO_TOTAL": {
        "titulo_grafico": "Evolução do Fluxo de Caixa",
        "eixo_x": "Período",
        "eixo_y": "Valor (R$)",
        "tooltip_receita": "Entradas",
        "tooltip_despesa": "Saídas"
    },
    "VISAO_ANUAL": {
        "titulo_barras": "Fluxo Mensal Consolidado",
        "titulo_pizza": "Distribuição de Despesas (Top Categorias)",
        "label_eixo_x": "Mês",
        "label_eixo_y": "Total (R$)"
    },
    "VISAO_MENSAL": {
        "titulo_barras": "Movimentação Diária",
        "titulo_pizza": "Detalhamento por Categoria",
        "label_eixo_x": "Dia do Mês",
        "label_eixo_y": "Volume (R$)"
    },
    "TABELA": {
        "col_data": "📅 Data",
        "col_tipo": "Tipo",
        "col_cat": "📂 Categoria",
        "col_desc": "📝 Descrição",
        "col_conta": "Conta",
        "col_valor": "💲 Valor"
    }
}

# --- CORES (SISTEMA HSL) ---
CORES = {
    # Cores Semânticas (Usadas nos Gráficos e Tabela)
    "receita": "hsl(154, 65%, 55%)",    # Verde
    "receita_bg": "hsla(154, 65%, 55%, 0.2)", # Verde Transparente (Fundo Tabela)
    "despesa": "hsl(6, 100%, 65%)",      # Vermelho
    "despesa_bg": "hsla(6, 100%, 65%, 0.2)", # Vermelho Transparente (Fundo Tabela)
    "saldo_pos": "hsl(154, 65%, 55%)",
    "saldo_neg": "hsl(6, 85%, 60%)",
    
    # Cores de Interface
    "texto_geral": "hsl(0, 0%, 90%)",
    "texto_branco": "hsl(0, 0%, 100%)",
    "fundo_transparente": "rgba(0,0,0,0)",
    "grid_color": "hsl(220, 10%, 20%)"
}

# Mapa de Cores para Plotly
MAPA_CORES_PLOTLY = {
    'Receita': CORES['receita'], 
    'Despesa': CORES['despesa']
}

# ==============================================================================
# 🛠️ FUNÇÕES AUXILIARES DE DESIGN E DADOS
# ==============================================================================

def preparar_dados_pizza_detalhada(df_filtrado, tipo_filtro='Despesa'):
    """
    Gera um dataframe pronto para o gráfico de pizza, incluindo
    uma string HTML com as top subcategorias para o tooltip.
    """
    # 1. Filtra pelo tipo (ex: Despesa)
    df_f = df_filtrado[df_filtrado['tipo'] == tipo_filtro].copy()
    
    if df_f.empty: return pd.DataFrame()

    # 2. Agrupa por Categoria para o gráfico principal
    df_cat = df_f.groupby('categoria')['valor'].sum().reset_index()
    
    # 3. Lógica para criar o texto do tooltip (Subcategorias)
    lista_tooltips = []
    
    for cat in df_cat['categoria']:
        # Pega as subcategorias desta categoria
        df_sub = df_f[df_f['categoria'] == cat]
        total_cat = df_sub['valor'].sum()
        
        # Agrupa subcategorias, ordena e pega top 5
        sub_group = df_sub.groupby('subcategoria')['valor'].sum().reset_index()
        sub_group = sub_group.sort_values('valor', ascending=False).head(5)
        
        # Monta HTML
        html_tooltip = ""
        for _, row in sub_group.iterrows():
            pct = (row['valor'] / total_cat) * 100
            # Se a subcategoria for vazia/nula, chama de "Geral"
            nome_sub = row['subcategoria'] if row['subcategoria'] else "Geral"
            html_tooltip += f"• {nome_sub}: R$ {row['valor']:,.2f} ({pct:.0f}%)<br>"
            
        lista_tooltips.append(html_tooltip)
        
    df_cat['info_extra'] = lista_tooltips
    return df_cat

def aplicar_estilo_tabela(df):
    """
    Aplica cores de fundo na coluna Valor baseada no Tipo (Receita/Despesa).
    Retorna um objeto Styler do Pandas.
    """
    # Define função de colorização linha a linha
    def colorir_linhas(row):
        cor_fundo = CORES['receita'] if row['tipo'] == 'Receita' else CORES['despesa']
        cor_texto = "white" # Texto branco para contraste
        
        # CSS Styles
        estilos = [''] * len(row) # Padrão vazio para todas as colunas
        
        # Encontra o índice da coluna 'valor'
        if 'valor' in row.index:
            idx = row.index.get_loc('valor')
            estilos[idx] = f'background-color: {cor_fundo}; color: {cor_texto}; font-weight: bold; border-radius: 5px;'
            
        return estilos

    # Reordena colunas conforme solicitado
    colunas_ordem = ['data', 'tipo', 'categoria', 'descricao', 'conta', 'valor']
    # Garante que as colunas existem antes de selecionar
    cols_existentes = [c for c in colunas_ordem if c in df.columns]
    df_final = df[cols_existentes].copy()
    
    # Renomeia para exibição (usando Config)
    mapa_nomes = {
        'data': CONFIG_UI['TABELA']['col_data'],
        'tipo': CONFIG_UI['TABELA']['col_tipo'],
        'categoria': CONFIG_UI['TABELA']['col_cat'],
        'descricao': CONFIG_UI['TABELA']['col_desc'],
        'conta': CONFIG_UI['TABELA']['col_conta'],
        'valor': CONFIG_UI['TABELA']['col_valor']
    }
    
    # Aplica formatação de números antes do estilo (opcional, mas st.dataframe lida melhor com raw numbers)
    # Aqui vamos retornar o DF e usar column_config do Streamlit para formatação de texto, 
    # e Pandas Styler para Cor.
    
    # O Styler precisa trabalhar com os nomes originais antes de renomear no visual, 
    # mas o Streamlit aplica o Styler.
    
    styler = df_final.style.apply(colorir_linhas, axis=1)
    
    # Formatação de string para o Styler (caso o column_config falhe em cima do styler)
    styler.format({'valor': "R$ {:,.2f}", 'data': "{:%d/%m/%Y}"})
    
    return styler, mapa_nomes

# ==============================================================================
# 🚀 RENDERIZAÇÃO
# ==============================================================================

def show_dashboard():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']

    st.header(CONFIG_UI['GERAL']['titulo_pag'])
    
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
    # ABA 1: VISÃO TOTAL (Mantido o Spline)
    # ===================================================
    with tab_total:
        total_rec = df[df['tipo'] == 'Receita']['valor'].sum()
        total_desp = df[df['tipo'] == 'Despesa']['valor'].sum()
        saldo_caixa = total_rec - total_desp
        
        df_reserva = carregar_reservas(user_id)
        saldo_reserva = df_reserva['saldo_atual'].sum() if not df_reserva.empty else 0.0
        total_liquidez = saldo_caixa + saldo_reserva

        st.markdown("### 💰 Posição Geral")
        c1, c2, c3 = st.columns(3)
        c1.metric("Saldo em Caixa", f"R$ {saldo_caixa:,.2f}")
        c2.metric("Reservas", f"R$ {saldo_reserva:,.2f}")
        c3.metric("Patrimônio Total", f"R$ {total_liquidez:,.2f}")
        st.divider()

        st.markdown(f"### 📉 {CONFIG_UI['VISAO_TOTAL']['titulo_grafico']}")
        
        df_tempo = df.groupby(['Ano', 'Mes', 'tipo'])['valor'].sum().reset_index()
        df_tempo['Data_Ref'] = pd.to_datetime(df_tempo['Ano'].astype(str) + '-' + df_tempo['Mes'].astype(str) + '-01')
        df_tempo = df_tempo.sort_values('Data_Ref')
        
        fig_evolucao = px.line(
            df_tempo, x='Data_Ref', y='valor', color='tipo',
            category_orders={"tipo": ["Receita", "Despesa"]},
            color_discrete_map=MAPA_CORES_PLOTLY, line_shape='spline', render_mode='svg'
        )
        fig_evolucao.update_traces(fill='tozeroy', mode='lines', line=dict(width=3), opacity=0.7)
        # Tooltip limpo para o gráfico de linhas
        fig_evolucao.update_traces(hovertemplate='%{x|%b/%Y}<br><b>%{y:,.2f}</b><extra></extra>')

        fig_evolucao.update_layout(
            template="plotly_dark", paper_bgcolor=CORES["fundo_transparente"], plot_bgcolor=CORES["fundo_transparente"],
            xaxis=dict(showgrid=False, title=CONFIG_UI['VISAO_TOTAL']['eixo_x'], linecolor="#333"),
            yaxis=dict(showgrid=True, gridcolor=CORES["grid_color"], title=CONFIG_UI['VISAO_TOTAL']['eixo_y'], tickprefix="R$ "),
            legend=dict(orientation="h", y=1.02, x=1, title=None), margin=dict(t=30)
        )
        st.plotly_chart(fig_evolucao, use_container_width=True)

    # ===================================================
    # ABA 2: VISÃO ANUAL (ATUALIZADA)
    # ===================================================
    with tab_anual:
        anos = sorted(df['Ano'].unique().tolist(), reverse=True)
        sel_ano = st.selectbox("Selecione o Ano", anos, key="sb_ano_dash")
        df_ano = df[df['Ano'] == sel_ano]
        
        if df_ano.empty:
            st.warning(CONFIG_UI['GERAL']['msg_vazio'])
        else:
            # Métricas
            rec_a = df_ano[df_ano['tipo'] == 'Receita']['valor'].sum()
            desp_a = df_ano[df_ano['tipo'] == 'Despesa']['valor'].sum()
            saldo_a = rec_a - desp_a
            col_m = st.columns(3)
            col_m[0].metric("Receita Anual", f"R$ {rec_a:,.2f}")
            col_m[1].metric("Despesa Anual", f"R$ {desp_a:,.2f}")
            col_m[2].metric("Saldo Anual", f"R$ {saldo_a:,.2f}")
            st.divider()

            g1, g2 = st.columns(2)
            
            # --- GRÁFICO DE BARRAS (Fluxo Mensal) ---
            with g1:
                df_barras = df_ano.groupby(['Mes', 'tipo'])['valor'].sum().reset_index()
                mapa_mes = {1:'Jan', 2:'Fev', 3:'Mar', 4:'Abr', 5:'Mai', 6:'Jun', 7:'Jul', 8:'Ago', 9:'Set', 10:'Out', 11:'Nov', 12:'Dez'}
                df_barras['NomeMes'] = df_barras['Mes'].map(mapa_mes)
                
                fig_bar = px.bar(
                    df_barras, x='NomeMes', y='valor', color='tipo', barmode='group',
                    title=f"{CONFIG_UI['VISAO_ANUAL']['titulo_barras']} ({sel_ano})",
                    color_discrete_map=MAPA_CORES_PLOTLY, template="plotly_dark",
                    category_orders={"NomeMes": list(mapa_mes.values())}
                )
                
                # Tooltip Limpo: "Tipo: R$ Valor"
                fig_bar.update_traces(hovertemplate='<b>%{data.name}</b><br>R$ %{y:,.2f}<extra></extra>')
                
                fig_bar.update_layout(
                    paper_bgcolor=CORES["fundo_transparente"], plot_bgcolor=CORES["fundo_transparente"],
                    xaxis_title=CONFIG_UI['VISAO_ANUAL']['label_eixo_x'],
                    yaxis_title=CONFIG_UI['VISAO_ANUAL']['label_eixo_y'],
                    legend=dict(title=None, orientation="h")
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            
            # --- GRÁFICO DE PIZZA (Com Detalhes) ---
            with g2:
                # Prepara dados com HTML de subcategorias
                df_pizza = preparar_dados_pizza_detalhada(df_ano, 'Despesa')
                
                if not df_pizza.empty:
                    fig_pie = go.Figure(data=[go.Pie(
                        labels=df_pizza['categoria'],
                        values=df_pizza['valor'],
                        hole=0.4,
                        # Adiciona a info extra nos dados customizados
                        customdata=df_pizza['info_extra'],
                        # Tooltip: Categoria, Valor, Porcentagem E a lista de subcategorias
                        hovertemplate="<b>%{label}</b><br>Total: R$ %{value:,.2f} (%{percent})<br><br><b>Top Detalhes:</b><br>%{customdata}<extra></extra>",
                        marker=dict(colors=px.colors.sequential.RdBu) # Ou use uma paleta fixa
                    )])
                    
                    fig_pie.update_layout(
                        title=f"{CONFIG_UI['VISAO_ANUAL']['titulo_pizza']} ({sel_ano})",
                        template="plotly_dark",
                        paper_bgcolor=CORES["fundo_transparente"]
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("Sem despesas registradas.")

    # ===================================================
    # ABA 3: VISÃO MENSAL (ATUALIZADA)
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
            st.warning(CONFIG_UI['GERAL']['msg_vazio'])
        else:
            rec_m = df_mes[df_mes['tipo'] == 'Receita']['valor'].sum()
            desp_m = df_mes[df_mes['tipo'] == 'Despesa']['valor'].sum()
            saldo_m = rec_m - desp_m
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Receita Mensal", f"R$ {rec_m:,.2f}")
            m2.metric("Despesa Mensal", f"R$ {desp_m:,.2f}")
            m3.metric("Saldo Mensal", f"R$ {saldo_m:,.2f}")
            st.divider()
            
            gm1, gm2 = st.columns(2)
            
            # --- GRÁFICO DIÁRIO ---
            with gm1:
                df_dias = df_mes.groupby(['Dia', 'tipo'])['valor'].sum().reset_index()
                fig_bar_dia = px.bar(
                    df_dias, x='Dia', y='valor', color='tipo', barmode='group',
                    title=f"{CONFIG_UI['VISAO_MENSAL']['titulo_barras']} - {sel_mes_nome}",
                    color_discrete_map=MAPA_CORES_PLOTLY, template="plotly_dark"
                )
                fig_bar_dia.update_traces(hovertemplate='Dia %{x}<br><b>%{data.name}</b>: R$ %{y:,.2f}<extra></extra>')
                fig_bar_dia.update_layout(
                    paper_bgcolor=CORES["fundo_transparente"], plot_bgcolor=CORES["fundo_transparente"],
                    xaxis_title=CONFIG_UI['VISAO_MENSAL']['label_eixo_x'],
                    yaxis_title=CONFIG_UI['VISAO_MENSAL']['label_eixo_y'],
                    legend=dict(title=None, orientation="h")
                )
                st.plotly_chart(fig_bar_dia, use_container_width=True)

            # --- PIZZA MENSAL ---
            with gm2:
                df_pizza_mes = preparar_dados_pizza_detalhada(df_mes, 'Despesa')
                if not df_pizza_mes.empty:
                    fig_pie_m = go.Figure(data=[go.Pie(
                        labels=df_pizza_mes['categoria'],
                        values=df_pizza_mes['valor'],
                        hole=0.4,
                        customdata=df_pizza_mes['info_extra'],
                        hovertemplate="<b>%{label}</b><br>R$ %{value:,.2f} (%{percent})<br><br><b>Detalhes:</b><br>%{customdata}<extra></extra>",
                        marker=dict(colors=px.colors.sequential.RdBu)
                    )])
                    fig_pie_m.update_layout(
                        title=f"{CONFIG_UI['VISAO_MENSAL']['titulo_pizza']} - {sel_mes_nome}",
                        template="plotly_dark", paper_bgcolor=CORES["fundo_transparente"]
                    )
                    st.plotly_chart(fig_pie_m, use_container_width=True)
                else:
                    st.info("Sem despesas.")
            
            st.markdown("### 📋 Lançamentos Detalhados")
            
            # --- TABELA ESTILIZADA ---
            # Prepara o Styler (Cores) e o Mapa de Nomes
            styler_tabela, mapa_nomes = aplicar_estilo_tabela(df_mes)
            
            st.dataframe(
                styler_tabela,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "data": st.column_config.DateColumn(mapa_nomes['data'], format="DD/MM/YYYY"),
                    "tipo": st.column_config.TextColumn(mapa_nomes['tipo']),
                    "categoria": st.column_config.TextColumn(mapa_nomes['categoria']),
                    "descricao": st.column_config.TextColumn(mapa_nomes['descricao']),
                    "conta": st.column_config.TextColumn(mapa_nomes['conta']),
                    "valor": st.column_config.NumberColumn(mapa_nomes['valor'], format="R$ %.2f")
                }
            )