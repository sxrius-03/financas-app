import streamlit as st
import pandas as pd
from datetime import datetime, date
from modules.database import carregar_dados, salvar_meta, carregar_metas, excluir_meta, listar_meses_com_metas
from modules.constants import LISTA_CATEGORIAS_DESPESA

def show_orcamento():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']

    st.header("🎯 Controle de Orçamento")
    
    tab_monitor, tab_config = st.tabs(["📊 Monitoramento Mensal", "⚙️ Definir Metas (Por Mês)"])
    
    # ===================================================
    # ABA 1: MONITORAMENTO (FILTRO DINÂMICO)
    # ===================================================
    with tab_monitor:
        # 1. Busca quais meses têm metas cadastradas
        meses_com_metas = listar_meses_com_metas(user_id)
        
        if not meses_com_metas:
            st.warning("Você ainda não definiu metas. Vá na aba 'Definir Metas' para começar.")
        else:
            # Cria opções legíveis para o selectbox (Ex: "01/2025", "12/2024")
            mapa_meses = {1:"Jan", 2:"Fev", 3:"Mar", 4:"Abr", 5:"Mai", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Set", 10:"Out", 11:"Nov", 12:"Dez"}
            opcoes_formatadas = [f"{mapa_meses[m]} / {a}" for m, a in meses_com_metas]
            
            # Tenta selecionar o mês atual por padrão, se existir na lista
            hj = date.today()
            lbl_atual = f"{mapa_meses[hj.month]} / {hj.year}"
            idx_padrao = opcoes_formatadas.index(lbl_atual) if lbl_atual in opcoes_formatadas else 0
            
            escolha = st.selectbox("📅 Selecione o Período para Visualizar:", opcoes_formatadas, index=idx_padrao)
            
            # Recupera o mês/ano numérico da escolha
            idx_escolha = opcoes_formatadas.index(escolha)
            mes_sel, ano_sel = meses_com_metas[idx_escolha]
            
            st.divider()
            
            # 2. Carrega dados filtrados
            df_metas = carregar_metas(user_id, mes=mes_sel, ano=ano_sel)
            df_lancamentos = carregar_dados(user_id)
            
            # Filtra lançamentos do mesmo período para comparar
            if not df_lancamentos.empty:
                # Garante tipo datetime
                df_lancamentos['data'] = pd.to_datetime(df_lancamentos['data'])
                mask = (df_lancamentos['data'].dt.month == mes_sel) & \
                       (df_lancamentos['data'].dt.year == ano_sel) & \
                       (df_lancamentos['tipo'] == 'Despesa')
                gastos = df_lancamentos[mask].groupby('categoria')['valor'].sum().reset_index()
            else:
                gastos = pd.DataFrame(columns=['categoria', 'valor'])

            # 3. Merge e Exibição
            df_final = pd.merge(df_metas, gastos, on='categoria', how='left')
            df_final['valor'] = df_final['valor'].fillna(0)
            df_final['Saldo'] = df_final['valor_meta'] - df_final['valor']
            df_final['Progresso'] = (df_final['valor'] / df_final['valor_meta']).clip(0, 1)
            
            # Exibe tabela rica
            st.dataframe(
                df_final[['categoria', 'valor_meta', 'valor', 'Saldo', 'Progresso']],
                use_container_width=True,
                column_config={
                    "categoria": "Categoria",
                    "valor_meta": st.column_config.NumberColumn("Meta", format="R$ %.2f"),
                    "valor": st.column_config.NumberColumn("Gasto Real", format="R$ %.2f"),
                    "Saldo": st.column_config.NumberColumn("Disponível", format="R$ %.2f"),
                    "Progresso": st.column_config.ProgressColumn("Consumo", format="%.0f%%", min_value=0, max_value=1),
                },
                hide_index=True
            )
            
            # Alertas
            estourados = df_final[df_final['valor'] > df_final['valor_meta']]
            if not estourados.empty:
                for _, row in estourados.iterrows():
                    st.error(f"🚨 Atenção: Você estourou o orçamento de **{row['categoria']}** em R$ {abs(row['Saldo']):.2f}!")

    # ===================================================
    # ABA 2: DEFINIR METAS (AGORA COM DATA)
    # ===================================================
    with tab_config:
        col_add, col_del = st.columns([1, 1], gap="large")
        
        with col_add:
            st.subheader("➕ Definir Meta Mensal")
            st.caption("Escolha o mês de referência. Isso permite ter orçamentos diferentes para meses diferentes (ex: Natal).")
            
            with st.form("form_meta"):
                # Seletores de Data
                c_mes, c_ano = st.columns(2)
                mes_form = c_mes.selectbox("Mês", range(1, 13), index=date.today().month-1)
                ano_form = c_ano.number_input("Ano", min_value=2023, max_value=2030, value=date.today().year)
                
                cat_selecionada = st.selectbox("Categoria", options=LISTA_CATEGORIAS_DESPESA)
                valor_meta = st.number_input("Limite para este mês (R$)", min_value=0.0)
                
                if st.form_submit_button("💾 Salvar Meta"):
                    if valor_meta > 0:
                        salvar_meta(user_id, cat_selecionada, valor_meta, mes_form, ano_form)
                        st.success(f"Meta de {cat_selecionada} para {mes_form}/{ano_form} salva!")
                        st.rerun()
                    else:
                        st.warning("Valor deve ser maior que zero.")

        with col_del:
            st.subheader("🗑️ Excluir Meta Específica")
            
            # Carrega todas as metas para o selectbox de exclusão
            df_todas = carregar_metas(user_id) # Sem filtro, traz tudo
            
            if df_todas.empty:
                st.info("Nenhuma meta cadastrada.")
            else:
                # Cria lista descritiva: "01/2025 - Alimentação - R$ 500"
                df_todas['label'] = df_todas.apply(lambda x: f"{x['mes']:02d}/{x['ano']} - {x['categoria']} (R$ {x['valor_meta']:.2f})", axis=1)
                
                meta_para_excluir = st.selectbox("Selecione para remover:", df_todas['label'].tolist())
                
                if st.button("❌ Apagar Selecionada"):
                    # Recupera dados originais pelo label
                    item = df_todas[df_todas['label'] == meta_para_excluir].iloc[0]
                    excluir_meta(user_id, item['categoria'], item['mes'], item['ano'])
                    st.success("Meta removida.")
                    st.rerun()

        st.divider()
        st.info("💡 Dica: Se não definir meta para um mês específico, ele não aparecerá no monitoramento.")