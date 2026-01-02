import streamlit as st
import pandas as pd
from datetime import datetime, date
from modules.database import (
    carregar_dados, salvar_meta, carregar_metas, excluir_meta, 
    listar_meses_com_metas
)

# Tenta importar listas de investimento, caso não existam, use listas genéricas
try:
    from modules.constants import LISTA_CATEGORIAS_DESPESA, LISTA_CATEGORIAS_INVESTIMENTO
except ImportError:
    from modules.constants import LISTA_CATEGORIAS_DESPESA
    LISTA_CATEGORIAS_INVESTIMENTO = ["Reserva de Emergência", "Aposentadoria", "Objetivos", "Investimentos"]

# ==============================================================================
# 🎛️ PAINEL DE CONTROLE (CONFIGURAÇÕES DE UI & DESIGN)
# ==============================================================================

CONFIG_UI = {
    "GERAL": {
        "titulo": "🎯 Metas de Gasto",
        "caption": "Defina tetos de gastos e objetivos de economia para manter o orçamento em dia.",
        "tabs": ["📊 Monitoramento", "🗓️ Metas Mensais", "📅 Metas Anuais"]
    },
    "MONITORAMENTO": {
        "titulo_despesas": "💸 Orçamento de Gastos (Limites)",
        "titulo_reservas": "💰 Metas de Economia (Objetivos)",
        "msg_vazio": "Nenhuma meta definida para este período.",
        # Nomes das Colunas das Tabelas
        "col_cat": "Categoria",
        "col_meta": "🎯 Meta / Teto (R$)",
        "col_real": "📉 Realizado (R$)",
        "col_saldo": "💵 Disponível / Falta",
        "col_prog": "📊 % Consumido"
    },
    "FORMULARIO": {
        "header_novo": "➕ Nova Meta",
        "header_edit": "✏️ Editando Meta",
        "lbl_tipo": "Tipo de Meta",
        "lbl_cat": "Categoria",
        "lbl_mes": "Mês de Referência",
        "lbl_ano": "Ano",
        "lbl_valor": "Valor da Meta (R$)",
        "btn_salvar": "💾 Salvar Meta",
        "btn_excluir": "🗑️ Excluir Meta"
    }
}

# --- CORES (SISTEMA HSL) ---
CORES = {
    "barra_sucesso": "hsl(140, 100%, 30%)", # Verde
    "barra_aviso": "hsl(40, 100%, 50%)",    # Amarelo
    "barra_erro": "hsl(0, 100%, 60%)",      # Vermelho
    "texto_padrao": "hsl(0, 0%, 90%)",
    "card_bg": "hsl(220, 13%, 18%)"
}

# Mapa de Meses para Exibição
MAPA_MESES_NOME = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

# ==============================================================================
# 🛠️ LÓGICA DO ORÇAMENTO
# ==============================================================================

def show_orcamento():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']

    st.header(CONFIG_UI["GERAL"]["titulo"])
    st.caption(CONFIG_UI["GERAL"]["caption"])

    tab_monitor, tab_mensal, tab_anual = st.tabs(CONFIG_UI["GERAL"]["tabs"])
    
    # ===================================================
    # ABA 1: MONITORAMENTO GERAL
    # ===================================================
    with tab_monitor:
        meses_com_metas = listar_meses_com_metas(user_id)
        
        if not meses_com_metas:
            st.warning("Nenhuma meta definida ainda. Configure nas abas ao lado.")
        else:
            opcoes_formatadas = []
            dados_originais = []
            
            for m, a in meses_com_metas:
                # Usa o mapa de nomes para criar o label (Ex: Janeiro / 2025)
                nome_mes = MAPA_MESES_NOME.get(m, "Anual") if m != 0 else "Meta Anual"
                lbl = f"{nome_mes} de {a}"
                opcoes_formatadas.append(lbl)
                dados_originais.append((m, a))

            # Tenta selecionar o mês atual
            hj = date.today()
            lbl_atual = f"{MAPA_MESES_NOME.get(hj.month)} de {hj.year}"
            
            idx_padrao = 0
            if lbl_atual in opcoes_formatadas:
                idx_padrao = opcoes_formatadas.index(lbl_atual)
            
            escolha = st.selectbox("📅 Selecione o Período:", opcoes_formatadas, index=idx_padrao)
            mes_sel, ano_sel = dados_originais[opcoes_formatadas.index(escolha)]
            
            st.divider()

            # --- Carregamento de Dados ---
            df_metas = carregar_metas(user_id, mes=mes_sel, ano=ano_sel)
            df_lancamentos = carregar_dados(user_id)
            
            if not df_lancamentos.empty:
                df_lancamentos['data'] = pd.to_datetime(df_lancamentos['data'])

            # Função auxiliar para calcular progresso
            def calcular_progresso(df_metas_filtrada, tipo_meta):
                if df_metas_filtrada.empty: return pd.DataFrame()

                # Filtra lançamentos pelo período
                mask_periodo = (df_lancamentos['data'].dt.year == ano_sel)
                if mes_sel != 0: # Se não for anual, filtra mês
                    mask_periodo = mask_periodo & (df_lancamentos['data'].dt.month == mes_sel)
                
                df_periodo = df_lancamentos[mask_periodo]

                # Define filtro por tipo (Despesa vs Reserva/Investimento)
                if tipo_meta == 'Despesa':
                    df_filtrado = df_periodo[df_periodo['tipo'] == 'Despesa']
                else:
                    # Considera tudo que pode ser investimento
                    df_filtrado = df_periodo[df_periodo['tipo'].isin(['Investimento', 'Reserva', 'Aplicação', 'Despesa'])]
                    # Refina apenas pelas categorias que estão na lista de investimento
                    df_filtrado = df_filtrado[df_filtrado['categoria'].isin(LISTA_CATEGORIAS_INVESTIMENTO)]

                gastos = df_filtrado.groupby('categoria')['valor'].sum().reset_index()
                
                merged = pd.merge(df_metas_filtrada, gastos, on='categoria', how='left')
                merged['valor'] = merged['valor'].fillna(0)
                
                # Lógica de Saldo/Progresso
                if tipo_meta == 'Despesa':
                    merged['Saldo'] = merged['valor_meta'] - merged['valor']
                    merged['Progresso'] = (merged['valor'] / merged['valor_meta']).clip(0, 1)
                else:
                    # Para reservas: Saldo é quanto falta para atingir a meta
                    merged['Saldo'] = merged['valor_meta'] - merged['valor']
                    # Progresso é quanto já guardou
                    merged['Progresso'] = (merged['valor'] / merged['valor_meta']).clip(0, 1)

                return merged

            # Identifica quais metas são de Investimento
            df_metas['tipo_meta'] = df_metas['categoria'].apply(lambda x: 'Reserva' if x in LISTA_CATEGORIAS_INVESTIMENTO else 'Despesa')
            
            metas_despesa = df_metas[df_metas['tipo_meta'] == 'Despesa']
            metas_reserva = df_metas[df_metas['tipo_meta'] == 'Reserva']

            # --- Exibição Despesas ---
            if not metas_despesa.empty:
                st.subheader(CONFIG_UI["MONITORAMENTO"]["titulo_despesas"])
                df_res_desp = calcular_progresso(metas_despesa, 'Despesa')
                
                st.dataframe(
                    df_res_desp[['categoria', 'valor_meta', 'valor', 'Saldo', 'Progresso']],
                    use_container_width=True,
                    column_config={
                        "categoria": st.column_config.TextColumn(CONFIG_UI["MONITORAMENTO"]["col_cat"]),
                        "valor_meta": st.column_config.NumberColumn(CONFIG_UI["MONITORAMENTO"]["col_meta"], format="R$ %.2f"),
                        "valor": st.column_config.NumberColumn(CONFIG_UI["MONITORAMENTO"]["col_real"], format="R$ %.2f"),
                        "Saldo": st.column_config.NumberColumn(CONFIG_UI["MONITORAMENTO"]["col_saldo"], format="R$ %.2f"),
                        "Progresso": st.column_config.ProgressColumn(
                            CONFIG_UI["MONITORAMENTO"]["col_prog"], 
                            format="%.0f%%", 
                            min_value=0, max_value=1
                        ),
                    },
                    hide_index=True
                )
                
                # Alertas de estouro
                for _, row in df_res_desp[df_res_desp['valor'] > df_res_desp['valor_meta']].iterrows():
                    st.error(f"🚨 Você estourou **{row['categoria']}** em R$ {abs(row['Saldo']):.2f}!")

            # --- Exibição Reservas ---
            if not metas_reserva.empty:
                st.subheader(CONFIG_UI["MONITORAMENTO"]["titulo_reservas"])
                df_res_invest = calcular_progresso(metas_reserva, 'Reserva')
                
                st.dataframe(
                    df_res_invest[['categoria', 'valor_meta', 'valor', 'Saldo', 'Progresso']],
                    use_container_width=True,
                    column_config={
                        "categoria": st.column_config.TextColumn(CONFIG_UI["MONITORAMENTO"]["col_cat"]),
                        "valor_meta": st.column_config.NumberColumn(CONFIG_UI["MONITORAMENTO"]["col_meta"], format="R$ %.2f"),
                        "valor": st.column_config.NumberColumn(CONFIG_UI["MONITORAMENTO"]["col_real"], format="R$ %.2f"),
                        "Saldo": st.column_config.NumberColumn(CONFIG_UI["MONITORAMENTO"]["col_saldo"], format="R$ %.2f"),
                        "Progresso": st.column_config.ProgressColumn(
                            CONFIG_UI["MONITORAMENTO"]["col_prog"], 
                            format="%.0f%%", 
                            min_value=0, max_value=1
                        ),
                    },
                    hide_index=True
                )

    # ===================================================
    # FUNÇÃO DE FORMULÁRIO (GERENCIADOR)
    # ===================================================
    def renderizar_gerenciador_metas(tipo_periodo="mensal"):
        """
        tipo_periodo: 'mensal' ou 'anual'
        """
        is_anual = (tipo_periodo == "anual")
        
        # 1. Carregar metas existentes para edição
        all_metas = carregar_metas(user_id)
        
        if is_anual:
            metas_filtradas = all_metas[all_metas['mes'] == 0]
        else:
            metas_filtradas = all_metas[all_metas['mes'] != 0]

        # Criar lista de seleção para Edição
        opcoes_edicao = ["✨ Criar Nova Meta"]
        mapa_dados = {}
        
        for idx, row in metas_filtradas.iterrows():
            if is_anual:
                lbl = f"{row['ano']} - {row['categoria']} (R$ {row['valor_meta']:.2f})"
            else:
                # Usa nome do mês no label de edição também
                nome_mes = MAPA_MESES_NOME.get(row['mes'], str(row['mes']))
                lbl = f"{nome_mes}/{row['ano']} - {row['categoria']} (R$ {row['valor_meta']:.2f})"
            
            opcoes_edicao.append(lbl)
            mapa_dados[lbl] = row

        col_sel, col_del = st.columns([3, 1])
        with col_sel:
            selecao = st.selectbox(f"Selecione uma meta ({tipo_periodo}) para editar:", options=opcoes_edicao, key=f"sel_{tipo_periodo}")
        
        modo_edicao = selecao != "✨ Criar Nova Meta"
        dados_edit = mapa_dados.get(selecao) if modo_edicao else None

        with col_del:
            st.write("") # Espaçamento
            st.write("") 
            if modo_edicao:
                if st.button(CONFIG_UI["FORMULARIO"]["btn_excluir"], key=f"del_{tipo_periodo}", type="primary"):
                    excluir_meta(user_id, str(dados_edit['categoria']), int(dados_edit['mes']), int(dados_edit['ano']))
                    st.success("Meta excluída!")
                    st.rerun()

        st.divider()
        st.subheader(CONFIG_UI["FORMULARIO"]["header_edit"] if modo_edicao else CONFIG_UI["FORMULARIO"]["header_novo"])

        # --- TIPO DE META (Radio fora do form para atualizar categorias) ---
        idx_tipo = 0
        if modo_edicao and dados_edit['categoria'] in LISTA_CATEGORIAS_INVESTIMENTO:
            idx_tipo = 1
            
        tipo_lancamento = st.radio(
            CONFIG_UI["FORMULARIO"]["lbl_tipo"], 
            ["Despesa", "Reserva/Investimento"], 
            index=idx_tipo,
            horizontal=True,
            key=f"radio_tipo_{tipo_periodo}"
        )
        
        lista_cats = LISTA_CATEGORIAS_DESPESA if tipo_lancamento == "Despesa" else LISTA_CATEGORIAS_INVESTIMENTO

        # Formulário Unificado
        with st.form(f"form_meta_{tipo_periodo}"):
            c_cat, c_data, c_val = st.columns([2, 1, 1])
            
            # Index da Categoria
            idx_cat = 0
            if modo_edicao and dados_edit['categoria'] in lista_cats:
                idx_cat = lista_cats.index(dados_edit['categoria'])

            with c_cat:
                cat_selecionada = st.selectbox(CONFIG_UI["FORMULARIO"]["lbl_cat"], options=lista_cats, index=idx_cat)

            with c_data:
                if is_anual:
                    val_ano = int(dados_edit['ano']) if modo_edicao else date.today().year
                    ano_form = st.number_input(CONFIG_UI["FORMULARIO"]["lbl_ano"], min_value=2023, max_value=2030, value=val_ano)
                    mes_form = 0 # 0 representa Anual no banco
                else:
                    # Lógica de Meses por Nome
                    val_mes_num = int(dados_edit['mes']) if modo_edicao else date.today().month
                    val_ano = int(dados_edit['ano']) if modo_edicao else date.today().year
                    
                    # Selectbox mostra NOMES, mas precisamos converter para NÚMERO
                    nomes_meses = list(MAPA_MESES_NOME.values()) # ['Janeiro', 'Fevereiro'...]
                    
                    # O index do selectbox deve ser mes_num - 1 (pois lista começa em 0)
                    mes_nome_selecionado = st.selectbox(
                        CONFIG_UI["FORMULARIO"]["lbl_mes"], 
                        nomes_meses, 
                        index=val_mes_num - 1
                    )
                    
                    # Converte o nome escolhido de volta para número
                    mes_form = [k for k, v in MAPA_MESES_NOME.items() if v == mes_nome_selecionado][0]
                    
                    # Hackzinho visual para alinhar inputs
                    st.write("") 
            
            if not is_anual:
                ano_form = st.number_input(CONFIG_UI["FORMULARIO"]["lbl_ano"], min_value=2023, max_value=2030, value=val_ano)

            with c_val:
                val_meta = float(dados_edit['valor_meta']) if modo_edicao else 0.0
                valor_meta = st.number_input(CONFIG_UI["FORMULARIO"]["lbl_valor"], min_value=0.0, value=val_meta, step=50.0)

            submitted = st.form_submit_button(CONFIG_UI["FORMULARIO"]["btn_salvar"])
            
            if submitted:
                if valor_meta > 0:
                    if modo_edicao:
                        mudou_chave = (dados_edit['categoria'] != cat_selecionada) or \
                                      (int(dados_edit['mes']) != mes_form) or \
                                      (int(dados_edit['ano']) != ano_form)
                        if mudou_chave:
                             excluir_meta(user_id, str(dados_edit['categoria']), int(dados_edit['mes']), int(dados_edit['ano']))
                    
                    salvar_meta(user_id, cat_selecionada, valor_meta, mes_form, ano_form)
                    st.success(f"Meta de {cat_selecionada} salva com sucesso!")
                    st.rerun()
                else:
                    st.warning("O valor deve ser maior que zero.")

    # ===================================================
    # RENDERIZAÇÃO DAS ABAS
    # ===================================================
    with tab_mensal:
        renderizar_gerenciador_metas("mensal")

    with tab_anual:
        st.info("ℹ️ Metas anuais são úteis para grandes objetivos (ex: Viagem de fim de ano, IPVA) ou teto de gastos anual.")
        renderizar_gerenciador_metas("anual")