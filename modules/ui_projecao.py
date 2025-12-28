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

def show_projecao():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']

    st.header("🔮 Saldo Projetado (Fluxo de Caixa)")
    st.caption("Esta ferramenta simula o futuro da sua conta bancária cruzando: Saldo Atual + Contas Fixas + Faturas + Metas de Orçamento.")

    # --- CONFIGURAÇÃO ---
    with st.expander("⚙️ Configurar Simulação", expanded=True):
        col1, col2 = st.columns(2)
        meses_proj = col1.slider("Projetar até quantos meses?", 1, 12, 6)
        usar_metas = col2.checkbox("Simular gasto total das Metas?", value=True, 
                                   help="Se marcado, o sistema reserva o dinheiro das suas metas (Lazer, Mercado, etc) como se fosse uma conta obrigatória. É o cenário mais seguro.")

    # --- CARGA DE DADOS (CACHEADA PELO DATABASE.PY) ---
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
            # Filtra o que vence neste dia
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
            # Filtra faturas que vencem neste mês/ano e neste dia
            # O banco retorna 'mes_fatura' como data (ex: 2025-02-01)
            for _, fat in df_faturas.iterrows():
                dt_fat = pd.to_datetime(fat['mes_fatura']).date()
                dia_venc_card = int(fat['dia_vencimento'])
                
                if dt_fat.month == mes and dt_fat.year == ano and dia_venc_card == dia:
                    val_fat = float(fat['total_fatura'])
                    saidas += val_fat
                    detalhes.append(f"Fatura Cartão: R$ {val_fat:.2f}")

        # 3. Provisão de Metas (Lógica do Breno)
        # Aplicamos no ÚLTIMO dia do mês
        _, ultimo_dia = calendar.monthrange(ano, mes)
        if usar_metas and dia == ultimo_dia:
            # Se for o mês atual: desconta apenas o que FALTA gastar
            if mes == date.today().month and ano == date.today().year:
                df_rest = buscar_metas_saldo_restante(user_id, mes, ano)
                if not df_rest.empty:
                    soma_restante = df_rest['restante'].sum()
                    if soma_restante > 0:
                        saidas += soma_restante
                        detalhes.append(f"Provisão Metas (Restante Mês): R$ {soma_restante:.2f}")
            
            # Se for mês futuro: desconta a meta CHEIA (assumindo que vai gastar tudo)
            elif data_cursor > date.today():
                # Busca metas cadastradas para aquele mês futuro
                df_metas_futuras = carregar_metas(user_id, mes, ano)
                if not df_metas_futuras.empty:
                    soma_metas = df_metas_futuras['valor_meta'].sum()
                    if soma_metas > 0:
                        saidas += soma_metas
                        detalhes.append(f"Provisão Metas (Orçamento Cheio): R$ {soma_metas:.2f}")

        # Atualiza Saldo
        saldo_corrente = saldo_corrente + entradas - saidas
        
        # Só registra no gráfico se houve movimento ou se é hoje/fim
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
        st.warning("Sem dados suficientes para projetar.")
        return

    min_saldo = df_proj['Saldo'].min()
    data_min = df_proj.loc[df_proj['Saldo'].idxmin()]['Data'].strftime('%d/%m/%Y')
    
    # KPIs
    k1, k2, k3 = st.columns(3)
    k1.metric("Saldo Inicial (Hoje)", f"R$ {saldo_atual:,.2f}")
    
    delta_color = "normal" if min_saldo > 0 else "inverse"
    k2.metric("Pior Saldo Previsto", f"R$ {min_saldo:,.2f}", f"em {data_min}", delta_color=delta_color)
    
    saldo_final = df_proj.iloc[-1]['Saldo']
    k3.metric(f"Saldo em {meses_proj} meses", f"R$ {saldo_final:,.2f}")

    if min_saldo < 0:
        st.error(f"🚨 **Risco de Quebra:** Seu saldo deve ficar negativo no dia **{data_min}**. Considere reduzir suas Metas ou cortar Despesas Fixas.")
    else:
        st.success("✅ **Saúde Financeira:** Pelas projeções, você não ficará no vermelho no período, mesmo gastando todo o orçamento das metas.")

    # Gráfico Interativo
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df_proj['Data'], y=df_proj['Saldo'],
        mode='lines+markers', name='Saldo Projetado',
        line=dict(color='#00FF7F' if min_saldo >= 0 else '#FF4B4B', width=3),
        hovertemplate='%{x|%d/%m/%Y}<br>Saldo: R$ %{y:.2f}'
    ))
    
    # Linha Zero
    fig.add_hline(y=0, line_dash="dash", line_color="white", annotation_text="Zero")

    fig.update_layout(title="Evolução do Saldo", template="plotly_dark", height=450)
    st.plotly_chart(fig, use_container_width=True)

    # Tabela Drill-down
    with st.expander("🔎 Ver Detalhes dia a dia"):
        st.dataframe(
            df_proj[df_proj['Descricao'] != ""],
            column_config={
                "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "Saldo": st.column_config.NumberColumn("Saldo Final", format="R$ %.2f"),
                "Entrada": st.column_config.NumberColumn("Entradas", format="R$ %.2f"),
                "Saida": st.column_config.NumberColumn("Saídas", format="R$ %.2f"),
            },
            use_container_width=True,
            hide_index=True
        )