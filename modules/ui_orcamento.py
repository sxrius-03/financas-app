import streamlit as st
import pandas as pd
from datetime import datetime
from modules.database import carregar_dados, salvar_meta, carregar_metas, excluir_meta
# IMPORTAÇÃO CENTRALIZADA
from modules.constants import LISTA_CATEGORIAS_DESPESA

def show_orcamento():
    # --- PEGAR USUÁRIO LOGADO ---
    if 'user_id' not in st.session_state:
        return
    user_id = st.session_state['user_id']

    st.header("🎯 Controle de Orçamento")
    
    tab_monitor, tab_config = st.tabs(["📊 Monitoramento Mensal", "⚙️ Definir / Excluir Metas"])
    
    # ATUALIZADO: Passando user_id
    df_lancamentos = carregar_dados(user_id)
    df_metas = carregar_metas(user_id)

    # ===================================================
    # ABA 1: MONITORAMENTO
    # ===================================================
    with tab_monitor:
        if df_metas.empty:
            st.warning("Você ainda não definiu nenhuma meta. Vá na aba 'Definir Metas' primeiro.")
        else:
            col_filt1, col_filt2 = st.columns(2)
            mes_atual = datetime.now().month
            
            meses_map = {
                1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
                5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
                9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
            }
            
            sel_ano = col_filt1.selectbox("Ano", [2024, 2025, 2026, 2027], index=1)
            sel_mes_nome = col_filt2.selectbox("Mês", list(meses_map.values()), index=mes_atual-1)
            sel_mes = [k for k, v in meses_map.items() if v == sel_mes_nome][0]
            
            st.divider()

            if not df_lancamentos.empty:
                df_filtrado = df_lancamentos[
                    (df_lancamentos['data'].dt.month == sel_mes) & 
                    (df_lancamentos['data'].dt.year == sel_ano) &
                    (df_lancamentos['tipo'] == 'Despesa')
                ]
                gastos_por_cat = df_filtrado.groupby('categoria')['valor'].sum().reset_index()
            else:
                gastos_por_cat = pd.DataFrame(columns=['categoria', 'valor'])

            df_final = pd.merge(df_metas, gastos_por_cat, on='categoria', how='left')
            df_final['valor'] = df_final['valor'].fillna(0)
            
            df_final['Saldo'] = df_final['valor_meta'] - df_final['valor']
            df_final['Progresso'] = (df_final['valor'] / df_final['valor_meta']).clip(0, 1)
            
            st.dataframe(
                df_final,
                use_container_width=True,
                column_config={
                    "categoria": "Categoria",
                    "valor_meta": st.column_config.NumberColumn("Meta (R$)", format="R$ %.2f"),
                    "valor": st.column_config.NumberColumn("Gasto (R$)", format="R$ %.2f"),
                    "Saldo": st.column_config.NumberColumn("Disponível", format="R$ %.2f"),
                    "Progresso": st.column_config.ProgressColumn(
                        "% Consumido",
                        format="%.1f%%",
                        min_value=0,
                        max_value=1,
                    ),
                },
                hide_index=True
            )
            
            estourados = df_final[df_final['valor'] > df_final['valor_meta']]
            if not estourados.empty:
                st.error("🚨 Você estourou o orçamento nas categorias acima!")

    # ===================================================
    # ABA 2: DEFINIR / EXCLUIR
    # ===================================================
    with tab_config:
        col_add, col_del = st.columns([1, 1], gap="large")
        
        with col_add:
            st.subheader("➕ Nova Meta")
            
            # USANDO LISTA CENTRALIZADA
            with st.form("form_meta"):
                cat_selecionada = st.selectbox("Escolha a Categoria", options=LISTA_CATEGORIAS_DESPESA)
                valor_meta = st.number_input("Limite Mensal (R$)", min_value=0.0)
                
                if st.form_submit_button("💾 Salvar / Atualizar"):
                    if valor_meta > 0:
                        salvar_meta(user_id, cat_selecionada, valor_meta)
                        st.success(f"Meta de {cat_selecionada} salva!")
                        st.rerun()
                    else:
                        st.warning("Valor deve ser maior que zero.")

        with col_del:
            st.subheader("🗑️ Excluir Meta")
            
            if df_metas.empty:
                st.info("Nenhuma meta cadastrada para excluir.")
            else:
                st.write("Selecione a meta que deseja remover:")
                
                lista_metas_existentes = df_metas['categoria'].tolist()
                meta_para_excluir = st.selectbox("Categoria Cadastrada", lista_metas_existentes)
                
                if st.button("❌ Apagar Meta Selecionada"):
                    sucesso = excluir_meta(user_id, meta_para_excluir)
                    if sucesso:
                        st.success(f"Meta de {meta_para_excluir} removida.")
                        st.rerun()
                    else:
                        st.error("Erro ao remover.")

        st.divider()
        st.subheader("📋 Resumo das Metas Ativas")
        if not df_metas.empty:
            st.dataframe(
                df_metas, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "categoria": "Categoria",
                    "valor_meta": st.column_config.NumberColumn("Valor Definido", format="R$ %.2f")
                }
            )
        else:
            st.caption("Nenhuma meta ativa no momento.")