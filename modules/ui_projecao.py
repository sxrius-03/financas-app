import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import calendar
from modules.database import (
    calcular_saldo_atual, carregar_recorrencias, buscar_faturas_futuras, 
    buscar_metas_saldo_restante, carregar_metas
)

# ==============================================================================
# 🎛️ PAINEL DE CONTROLE (CONFIGURAÇÕES DE UI & DESIGN)
# ==============================================================================

CONFIG_UI = {
    "GERAL": {
        "titulo": "🔮 Saldo Projetado (Fluxo de Caixa)",
        "caption": "Esta ferramenta simula o futuro da sua conta bancária cruzando: Saldo Atual + Contas Fixas + Faturas + Metas de Orçamento.",
        "config_label": "⚙️ Configurar Simulação",
        "lbl_meses": "Projetar até quantos meses?",
        "lbl_metas": "Simular gasto total das Metas?",
        "help_metas": "Se marcado, o sistema reserva o dinheiro das suas metas (Lazer, Mercado, etc) como se fosse uma conta obrigatória. É o cenário mais seguro."
    },
    "METRICAS": {
        "saldo_inicial": "Saldo Inicial (Hoje)",
        "pior_saldo": "Pior Saldo Previsto",
        "saldo_final": "Saldo em {} meses"
    },
    "MENSAGENS": {
        "risco": "🚨 **Risco de Quebra:** Seu saldo deve ficar negativo no dia **{}**. Considere reduzir suas Metas ou cortar Despesas Fixas.",
        "seguro": "✅ **Saúde Financeira:** Pelas projeções, você não ficará no vermelho no período, mesmo gastando todo o orçamento das metas.",
        "sem_dados": "Sem dados suficientes para projetar."
    },
    "TABELA": {
        "titulo_expander": "🔎 Ver Detalhes dia a dia",
        # AQUI VOCÊ MUDA O NOME DAS COLUNAS
        "col_data": "📅 Data",
        "col_saldo": "💰 Saldo Final (R$)",
        "col_entrada": "🟢 Entradas",
        "col_saida": "🔴 Saídas",
        "col_desc": "📝 Descrição do Movimento"
    }
}

# --- CORES (SISTEMA HSL) ---
CORES = {
    "positivo": "hsl(140, 100%, 50%)", # Verde Primavera (#00FF7F)
    "negativo": "hsl(0, 100%, 65%)",   # Vermelho Suave (#FF4B4B)
    "linha_zero": "hsl(0, 0%, 100%)",  # Branco
    "texto_padrao": "hsl(0, 0%, 90%)"
}

# ==============================================================================
# 🛠️ LÓGICA DE PROJEÇÃO
# ==============================================================================

def show_projecao():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']

    st.header(CONFIG_UI["GERAL"]["titulo"])
    st.caption(CONFIG_UI["GERAL"]["caption"])

    # --- CONFIGURAÇÃO ---
    with st.expander(CONFIG_UI["GERAL"]["config_label"], expanded=True):
        col1, col2 = st.columns(2)
        meses_proj = col1.slider(CONFIG_UI["GERAL"]["lbl_meses"], 1, 12, 6)
        usar_metas = col2.checkbox(CONFIG_UI["GERAL"]["lbl_metas"], value=True, help=CONFIG_UI["GERAL"]["help_metas"])

    # --- CARGA DE DADOS (CACHEADA) ---
    saldo_atual = calcular_saldo_atual(user_id)
    df_fixas = carregar_recorrencias(user_id)
    df_faturas = buscar_faturas_futuras(user_id)
    
    # --- MOTOR DE SIMULAÇÃO ---
    timeline = []
    saldo_corrente = float(saldo_atual)
    data_cursor = date.today()
    data_fim = data_cursor + relativedelta(months=meses_proj)

    # Avança dia a dia
    while data_cursor <= data_fim:
        dia = data_cursor.day
        mes = data_cursor.month
        ano = data_cursor.year
        
        entradas = 0.0
        saidas = 0.0
        detalhes = []

        # 1. Recorrências (Despesas Fixas / Receitas Fixas)
        if not df_fixas.empty:
            recs_do_dia = df_fixas[df_fixas['dia_vencimento'] == dia]
            for _, row in recs_do_dia.iterrows():
                val = float(row['valor'])
                if row['tipo'] == 'Receita':
                    entradas += val
                    detalhes.append(f"Receita: {row['nome']}")
                else:
                    saidas += val
                    detalhes.append(f"Fixo: {row['nome']}")

        # 2. Faturas de Cartão
        if not df_faturas.empty:
            for _, fat in df_faturas.iterrows():
                dt_fat = pd.to_datetime(fat['mes_fatura']).date()
                dia_venc_card = int(fat['dia_vencimento'])
                
                if dt_fat.month == mes and dt_fat.year == ano and dia_venc_card == dia:
                    val_fat = float(fat['total_fatura'])
                    saidas += val_fat
                    detalhes.append(f"Fatura Cartão: R$ {val_fat:.2f}")

        # 3. Provisão de Metas
        _, ultimo_dia = calendar.monthrange(ano, mes)
        if usar_metas and dia == ultimo_dia:
            if mes == date.today().month and ano == date.today().year:
                df_rest = buscar_metas_saldo_restante(user_id, mes, ano)
                if not df_rest.empty:
                    soma_restante = df_rest['restante'].sum()
                    if soma_restante > 0:
                        saidas += soma_restante
                        detalhes.append(f"Provisão Metas (Restante Mês): R$ {soma_restante:.2f}")
            elif data_cursor > date.today():
                df_metas_futuras = carregar_metas(user_id, mes, ano)
                if not df_metas_futuras.empty:
                    soma_metas = df_metas_futuras['valor_meta'].sum()
                    if soma_metas > 0:
                        saidas += soma_metas
                        detalhes.append(f"Provisão Metas (Orçamento Cheio): R$ {soma_metas:.2f}")

        # Atualiza Saldo
        saldo_corrente = saldo_corrente + entradas - saidas
        
        # Registra na timeline
        if entradas != 0 or saidas != 0 or data_cursor == date.today() or data_cursor == data_fim:
            timeline.append({
                "Data": data_cursor,
                "Saldo": saldo_corrente,
                "Entrada": entradas,
                "Saida": saidas,
                "Descricao": ", ".join(detalhes)
            })
        
        data_cursor += timedelta(days=1)

    df_proj = pd.DataFrame(timeline)

    # --- VISUALIZAÇÃO ---
    if df_proj.empty:
        st.warning(CONFIG_UI["MENSAGENS"]["sem_dados"])
        return

    min_saldo = df_proj['Saldo'].min()
    data_min = df_proj.loc[df_proj['Saldo'].idxmin()]['Data'].strftime('%d/%m/%Y')
    
    # KPIs
    k1, k2, k3 = st.columns(3)
    k1.metric(CONFIG_UI["METRICAS"]["saldo_inicial"], f"R$ {saldo_atual:,.2f}")
    
    delta_color = "normal" if min_saldo > 0 else "inverse"
    k2.metric(CONFIG_UI["METRICAS"]["pior_saldo"], f"R$ {min_saldo:,.2f}", f"em {data_min}", delta_color=delta_color)
    
    saldo_final = df_proj.iloc[-1]['Saldo']
    k3.metric(CONFIG_UI["METRICAS"]["saldo_final"].format(meses_proj), f"R$ {saldo_final:,.2f}")

    if min_saldo < 0:
        st.error(CONFIG_UI["MENSAGENS"]["risco"].format(data_min))
    else:
        st.success(CONFIG_UI["MENSAGENS"]["seguro"])

    # Gráfico Interativo
    fig = go.Figure()
    
    cor_linha = CORES["positivo"] if min_saldo >= 0 else CORES["negativo"]
    
    fig.add_trace(go.Scatter(
        x=df_proj['Data'], y=df_proj['Saldo'],
        mode='lines+markers', name='Saldo Projetado',
        line=dict(color=cor_linha, width=3),
        hovertemplate='%{x|%d/%m/%Y}<br>Saldo: R$ %{y:.2f}'
    ))
    
    # Linha Zero
    fig.add_hline(y=0, line_dash="dash", line_color=CORES["linha_zero"], annotation_text="Zero")

    fig.update_layout(title="Evolução do Saldo", template="plotly_dark", height=450)
    st.plotly_chart(fig, use_container_width=True)

    # Tabela Drill-down (Configurável)
    with st.expander(CONFIG_UI["TABELA"]["titulo_expander"]):
        st.dataframe(
            df_proj[df_proj['Descricao'] != ""],
            column_config={
                "Data": st.column_config.DateColumn(CONFIG_UI["TABELA"]["col_data"], format="DD/MM/YYYY"),
                "Saldo": st.column_config.NumberColumn(CONFIG_UI["TABELA"]["col_saldo"], format="R$ %.2f"),
                "Entrada": st.column_config.NumberColumn(CONFIG_UI["TABELA"]["col_entrada"], format="R$ %.2f"),
                "Saida": st.column_config.NumberColumn(CONFIG_UI["TABELA"]["col_saida"], format="R$ %.2f"),
                "Descricao": st.column_config.TextColumn(CONFIG_UI["TABELA"]["col_desc"]),
            },
            use_container_width=True,
            hide_index=True
        )