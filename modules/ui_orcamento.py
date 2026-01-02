import streamlit as st
import pandas as pd
from datetime import datetime, date
from modules.database import (
    carregar_dados, salvar_meta, carregar_metas, excluir_meta, 
    listar_meses_com_metas
)
# Importa as duas listas agora
try:
    from modules.constants import LISTA_CATEGORIAS_DESPESA, LISTA_CATEGORIAS_INVESTIMENTO
except ImportError:
    # Fallback caso constants.py não tenha sido atualizado ainda
    from modules.constants import LISTA_CATEGORIAS_DESPESA
    LISTA_CATEGORIAS_INVESTIMENTO = ["Reserva de Emergência", "Aposentadoria", "Objetivos", "Investimentos"]

def show_orcamento():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']

    st.header("🎯 Gestão de Metas e Orçamento")

    tab_monitor, tab_mensal, tab_anual = st.tabs([
        "📊 Monitoramento", 
        "🗓️ Metas Mensais", 
        "📅 Metas Anuais"
    ])
    
    # ===================================================
    # ABA 1: MONITORAMENTO GERAL
    # ===================================================
    with tab_monitor:
        st.caption("Acompanhe o progresso das suas metas (Despesas e Reservas).")
        
        meses_com_metas = listar_meses_com_metas(user_id)
        
        if not meses_com_metas:
            st.warning("Nenhuma meta definida ainda.")
        else:
            mapa_meses = {0: "Anual", 1:"Jan", 2:"Fev", 3:"Mar", 4:"Abr", 5:"Mai", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Set", 10:"Out", 11:"Nov", 12:"Dez"}
            
            opcoes_formatadas = []
            dados_originais = []
            
            for m, a in meses_com_metas:
                lbl = f"Ano {a}" if m == 0 else f"{mapa_meses[m]} / {a}"
                opcoes_formatadas.append(lbl)
                dados_originais.append((m, a))

            hj = date.today()
            lbl_atual = f"{mapa_meses[hj.month]} / {hj.year}"
            idx_padrao = opcoes_formatadas.index(lbl_atual) if lbl_atual in opcoes_formatadas else 0
            
            escolha = st.selectbox("📅 Selecione o Período:", opcoes_formatadas, index=idx_padrao)
            mes_sel, ano_sel = dados_originais[opcoes_formatadas.index(escolha)]
            
            st.divider()

            df_metas = carregar_metas(user_id, mes=mes_sel, ano=ano_sel)
            df_lancamentos = carregar_dados(user_id)
            
            if not df_lancamentos.empty:
                df_lancamentos['data'] = pd.to_datetime(df_lancamentos['data'])

            def calcular_progresso(df_metas_filtrada, tipo_meta):
                if df_metas_filtrada.empty: return pd.DataFrame()

                mask_periodo = (df_lancamentos['data'].dt.year == ano_sel)
                if mes_sel != 0:
                    mask_periodo = mask_periodo & (df_lancamentos['data'].dt.month == mes_sel)
                
                df_periodo = df_lancamentos[mask_periodo]

                if tipo_meta == 'Despesa':
                    df_filtrado = df_periodo[df_periodo['tipo'] == 'Despesa']
                else:
                    # Considera tudo que não é despesa nem receita pura como potencial investimento/reserva
                    df_filtrado = df_periodo[df_periodo['tipo'].isin(['Investimento', 'Reserva', 'Aplicação', 'Despesa'])]
                    # Refina apenas pelas categorias que estão na lista de investimento
                    df_filtrado = df_filtrado[df_filtrado['categoria'].isin(LISTA_CATEGORIAS_INVESTIMENTO)]

                gastos = df_filtrado.groupby('categoria')['valor'].sum().reset_index()
                
                merged = pd.merge(df_metas_filtrada, gastos, on='categoria', how='left')
                merged['valor'] = merged['valor'].fillna(0)
                
                if tipo_meta == 'Despesa':
                    merged['Saldo'] = merged['valor_meta'] - merged['valor']
                    merged['Progresso'] = (merged['valor'] / merged['valor_meta']).clip(0, 1)
                else:
                    merged['Saldo'] = merged['valor_meta'] - merged['valor']
                    merged['Progresso'] = (merged['valor'] / merged['valor_meta']).clip(0, 1)

                return merged

            df_metas['tipo_meta'] = df_metas['categoria'].apply(lambda x: 'Reserva' if x in LISTA_CATEGORIAS_INVESTIMENTO else 'Despesa')
            
            metas_despesa = df_metas[df_metas['tipo_meta'] == 'Despesa']
            metas_reserva = df_metas[df_metas['tipo_meta'] == 'Reserva']

            if not metas_despesa.empty:
                st.subheader("💸 Orçamento de Gastos")
                df_res_desp = calcular_progresso(metas_despesa, 'Despesa')
                st.dataframe(
                    df_res_desp[['categoria', 'valor_meta', 'valor', 'Saldo', 'Progresso']],
                    use_container_width=True,
                    column_config={
                        "valor_meta": st.column_config.NumberColumn("Limite", format="R$ %.2f"),
                        "valor": st.column_config.NumberColumn("Gasto", format="R$ %.2f"),
                        "Saldo": st.column_config.NumberColumn("Disponível", format="R$ %.2f"),
                        "Progresso": st.column_config.ProgressColumn("Consumo", format="%.0f%%", min_value=0, max_value=1),
                    },
                    hide_index=True
                )
                
                for _, row in df_res_desp[df_res_desp['valor'] > df_res_desp['valor_meta']].iterrows():
                    st.error(f"🚨 Você estourou **{row['categoria']}** em R$ {abs(row['Saldo']):.2f}!")

            if not metas_reserva.empty:
                st.subheader("💰 Metas de Economia")
                df_res_invest = calcular_progresso(metas_reserva, 'Reserva')
                st.dataframe(
                    df_res_invest[['categoria', 'valor_meta', 'valor', 'Saldo', 'Progresso']],
                    use_container_width=True,
                    column_config={
                        "valor_meta": st.column_config.NumberColumn("Meta", format="R$ %.2f"),
                        "valor": st.column_config.NumberColumn("Aportado", format="R$ %.2f"),
                        "Saldo": st.column_config.NumberColumn("Falta", format="R$ %.2f"),
                        "Progresso": st.column_config.ProgressColumn("Atingido", format="%.0f%%", min_value=0, max_value=1),
                    },
                    hide_index=True
                )

    # ===================================================
    # FUNÇÃO DO FORMULÁRIO (CORRIGIDA)
    # ===================================================
    def renderizar_gerenciador_metas(tipo_periodo="mensal"):
        is_anual = (tipo_periodo == "anual")
        
        all_metas = carregar_metas(user_id)
        if is_anual:
            metas_filtradas = all_metas[all_metas['mes'] == 0]
        else:
            metas_filtradas = all_metas[all_metas['mes'] != 0]

        opcoes_edicao = ["✨ Criar Nova Meta"]
        mapa_dados = {}
        
        for idx, row in metas_filtradas.iterrows():
            if is_anual:
                lbl = f"{row['ano']} - {row['categoria']} (R$ {row['valor_meta']:.2f})"
            else:
                lbl = f"{row['mes']:02d}/{row['ano']} - {row['categoria']} (R$ {row['valor_meta']:.2f})"
            opcoes_edicao.append(lbl)
            mapa_dados[lbl] = row

        col_sel, col_del = st.columns([3, 1])
        with col_sel:
            selecao = st.selectbox(f"Selecione uma meta ({tipo_periodo}) para editar:", options=opcoes_edicao, key=f"sel_{tipo_periodo}")
        
        modo_edicao = selecao != "✨ Criar Nova Meta"
        dados_edit = mapa_dados.get(selecao) if modo_edicao else None

        with col_del:
            st.write("") 
            st.write("") 
            if modo_edicao:
                if st.button("🗑️ Excluir", key=f"del_{tipo_periodo}", type="primary"):
                    excluir_meta(user_id, str(dados_edit['categoria']), int(dados_edit['mes']), int(dados_edit['ano']))
                    st.success("Meta excluída!")
                    st.rerun()

        st.divider()
        st.subheader(f"{'✏️ Editando' if modo_edicao else '➕ Nova'} Meta {tipo_periodo.capitalize()}")

        # --- CORREÇÃO: Radio fora do st.form para reatividade ---
        # Determina o valor inicial
        idx_tipo = 0
        if modo_edicao and dados_edit['categoria'] in LISTA_CATEGORIAS_INVESTIMENTO:
            idx_tipo = 1
            
        tipo_lancamento = st.radio(
            "Tipo de Meta", 
            ["Despesa", "Reserva/Investimento"], 
            index=idx_tipo,
            horizontal=True,
            key=f"radio_tipo_{tipo_periodo}"
        )
        
        # Define a lista correta baseada no radio (agora atualiza na hora!)
        lista_cats = LISTA_CATEGORIAS_DESPESA if tipo_lancamento == "Despesa" else LISTA_CATEGORIAS_INVESTIMENTO

        # Formulário para os demais campos
        with st.form(f"form_meta_{tipo_periodo}"):
            c_cat, c_data, c_val = st.columns([2, 1, 1])
            
            # Recupera índice da categoria se estiver editando e a categoria existir na lista atual
            idx_cat = 0
            if modo_edicao and dados_edit['categoria'] in lista_cats:
                idx_cat = lista_cats.index(dados_edit['categoria'])

            with c_cat:
                cat_selecionada = st.selectbox("Categoria", options=lista_cats, index=idx_cat)

            with c_data:
                if is_anual:
                    val_ano = int(dados_edit['ano']) if modo_edicao else date.today().year
                    ano_form = st.number_input("Ano", min_value=2023, max_value=2030, value=val_ano)
                    mes_form = 0
                else:
                    val_mes = int(dados_edit['mes']) if modo_edicao else date.today().month
                    val_ano = int(dados_edit['ano']) if modo_edicao else date.today().year
                    mes_form = st.selectbox("Mês", range(1, 13), index=val_mes-1)
                    # Hackzinho para passar ano para variavel acessivel
                    st.write("") # Espaço visual se precisar, ou coloque o ano em outra coluna se preferir
            
            # Se for mensal, coloca o Ano numa coluna extra ou ajusta layout. 
            # Para simplificar aqui, vou adicionar o ano abaixo do mês se for mensal
            if not is_anual:
                ano_form = st.number_input("Ano", min_value=2023, max_value=2030, value=val_ano)

            with c_val:
                val_meta = float(dados_edit['valor_meta']) if modo_edicao else 0.0
                valor_meta = st.number_input("Valor (R$)", min_value=0.0, value=val_meta, step=50.0)

            submitted = st.form_submit_button("💾 Salvar Meta")
            
            if submitted:
                if valor_meta > 0:
                    if modo_edicao:
                        mudou_chave = (dados_edit['categoria'] != cat_selecionada) or \
                                      (int(dados_edit['mes']) != mes_form) or \
                                      (int(dados_edit['ano']) != ano_form)
                        if mudou_chave:
                             excluir_meta(user_id, str(dados_edit['categoria']), int(dados_edit['mes']), int(dados_edit['ano']))
                    
                    salvar_meta(user_id, cat_selecionada, valor_meta, mes_form, ano_form)
                    st.success(f"Meta de {cat_selecionada} salva!")
                    st.rerun()
                else:
                    st.warning("Valor inválido.")

    # ===================================================
    # RENDERIZAÇÃO DAS ABAS
    # ===================================================
    with tab_mensal:
        renderizar_gerenciador_metas("mensal")

    with tab_anual:
        st.info("ℹ️ Metas anuais servem para grandes objetivos ou teto de gastos anual.")
        renderizar_gerenciador_metas("anual")