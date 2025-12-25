import streamlit as st
import pandas as pd
from datetime import datetime
from modules.database import carregar_dados, salvar_meta, carregar_metas, excluir_meta
from modules.constants import LISTA_CATEGORIAS_DESPESA

def show_orcamento():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']

    st.header("🎯 Controle de Orçamento")
    
    tab_monitor, tab_config = st.tabs(["📊 Monitoramento Mensal", "⚙️ Definir / Editar Metas"])
    
    df_lancamentos = carregar_dados(user_id)
    df_metas = carregar_metas(user_id)

    # ABA 1: MONITORAMENTO (Igual)
    with tab_monitor:
        if df_metas.empty:
            st.warning("Defina metas na outra aba primeiro.")
        else:
            col_filt1, col_filt2 = st.columns(2)
            sel_ano = col_filt1.selectbox("Ano", [2024, 2025, 2026], index=1)
            meses_map = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
            sel_mes_nome = col_filt2.selectbox("Mês", list(meses_map.values()), index=datetime.now().month-1)
            sel_mes = [k for k, v in meses_map.items() if v == sel_mes_nome][0]
            
            st.divider()
            
            if not df_lancamentos.empty:
                df_filtrado = df_lancamentos[(df_lancamentos['data'].dt.month == sel_mes) & (df_lancamentos['data'].dt.year == sel_ano) & (df_lancamentos['tipo'] == 'Despesa')]
                gastos = df_filtrado.groupby('categoria')['valor'].sum().reset_index()
            else: gastos = pd.DataFrame(columns=['categoria', 'valor'])

            df_final = pd.merge(df_metas, gastos, on='categoria', how='left')
            df_final['valor'] = df_final['valor'].fillna(0)
            df_final['Saldo'] = df_final['valor_meta'] - df_final['valor']
            df_final['Progresso'] = (df_final['valor'] / df_final['valor_meta']).clip(0, 1)
            
            st.dataframe(df_final, use_container_width=True, hide_index=True, column_config={"Progresso": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=1)})

    # ABA 2: DEFINIR / EDITAR (Melhorada)
    with tab_config:
        st.subheader("Gerenciar Metas")
        
        # Seletor para carregar dados existentes (Editar)
        meta_selecionada = st.selectbox("Selecione para Editar (ou deixe em branco para Nova)", ["Nova Meta..."] + df_metas['categoria'].tolist() if not df_metas.empty else ["Nova Meta..."])
        
        val_inicial = 0.0
        idx_cat = 0
        
        if meta_selecionada != "Nova Meta...":
            dados_meta = df_metas[df_metas['categoria'] == meta_selecionada].iloc[0]
            val_inicial = float(dados_meta['valor_meta'])
            try: idx_cat = LISTA_CATEGORIAS_DESPESA.index(meta_selecionada)
            except: idx_cat = 0
        
        with st.form("form_meta"):
            # Se for edição, trava a categoria para evitar duplicidade visual
            if meta_selecionada != "Nova Meta...":
                st.write(f"Editando meta para: **{meta_selecionada}**")
                cat_escolhida = meta_selecionada
            else:
                cat_escolhida = st.selectbox("Categoria", options=LISTA_CATEGORIAS_DESPESA, index=idx_cat)
                
            valor_meta = st.number_input("Limite Mensal (R$)", min_value=0.0, value=val_inicial)
            
            c_salvar, c_excluir = st.columns([1,4])
            if c_salvar.form_submit_button("💾 Salvar Meta"):
                if valor_meta > 0:
                    salvar_meta(user_id, cat_escolhida, valor_meta)
                    st.success(f"Meta de {cat_escolhida} atualizada!")
                    st.rerun()
            
        if meta_selecionada != "Nova Meta...":
            if st.button("🗑️ Excluir esta meta"):
                excluir_meta(user_id, meta_selecionada)
                st.rerun()