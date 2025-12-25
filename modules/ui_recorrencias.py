<<<<<<< HEAD
import streamlit as st
import pandas as pd
from datetime import date
from modules.database import salvar_recorrencia, carregar_recorrencias, excluir_recorrencia, salvar_lancamento

def show_recorrencias():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']
    
    st.header("🔄 Contas Fixas & Assinaturas")
    
    tab_gerar, tab_nova = st.tabs(["🚀 Gerar do Mês", "⚙️ Configurar Contas"])
    
    df_rec = carregar_recorrencias(user_id)

    # --- ABA 1: GERAR LANÇAMENTOS ---
    with tab_gerar:
        st.subheader("Lançamento Rápido")
        st.write("Use esta função para lançar todas as suas contas fixas no caixa deste mês de uma só vez.")
        
        if df_rec.empty:
            st.warning("Nenhuma conta recorrente cadastrada.")
        else:
            st.dataframe(df_rec, use_container_width=True, hide_index=True)
            
            col_btn, _ = st.columns(2)
            if col_btn.button("✅ Lançar Tudo no Mês Atual", type="primary"):
                contador = 0
                mes_atual = date.today().month
                ano_atual = date.today().year
                
                for _, row in df_rec.iterrows():
                    # Cria a data de vencimento para este mês/ano
                    try:
                        data_venc = date(ano_atual, mes_atual, int(row['dia_vencimento']))
                    except:
                        # Caso dia 31 não exista no mês (ex: Fev), joga pro dia 28
                        data_venc = date(ano_atual, mes_atual, 28)
                    
                    dados = {
                        "data": data_venc,
                        "tipo": row['tipo'],
                        "categoria": row['categoria'],
                        "subcategoria": "Recorrência",
                        "descricao": f"{row['nome']} (Ref. {mes_atual}/{ano_atual})",
                        "valor": row['valor'],
                        "conta": "Conta Padrão",
                        "forma_pagamento": "Boleto/Automático",
                        "status": "Pendente"
                    }
                    salvar_lancamento(user_id, dados)
                    contador += 1
                
                st.success(f"{contador} contas lançadas com sucesso no Caixa!")

    # --- ABA 2: CADASTRAR NOVA ---
    with tab_nova:
        st.subheader("Nova Conta Fixa")
        with st.form("form_rec"):
            nome = st.text_input("Nome (Ex: Aluguel, Netflix)")
            c1, c2 = st.columns(2)
            valor = c1.number_input("Valor (R$)", min_value=0.0)
            dia = c2.number_input("Dia de Vencimento", 1, 31, 10)
            
            tipo = st.selectbox("Tipo", ["Despesa", "Receita"])
            cat = st.text_input("Categoria", value="Moradia")
            
            if st.form_submit_button("Salvar Recorrência"):
                salvar_recorrencia(user_id, nome, valor, cat, dia, tipo)
                st.success("Salvo!")
                st.rerun()
        
        if not df_rec.empty:
            st.divider()
            st.write("Excluir item:")
            lista = df_rec['nome'].tolist()
            item_del = st.selectbox("Selecione", lista)
            if st.button("Excluir"):
                id_del = df_rec[df_rec['nome'] == item_del]['id'].values[0]
                excluir_recorrencia(user_id, int(id_del))
=======
import streamlit as st
import pandas as pd
from datetime import date
from modules.database import salvar_recorrencia, carregar_recorrencias, excluir_recorrencia, salvar_lancamento

def show_recorrencias():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']
    
    st.header("🔄 Contas Fixas & Assinaturas")
    
    tab_gerar, tab_nova = st.tabs(["🚀 Gerar do Mês", "⚙️ Configurar Contas"])
    
    df_rec = carregar_recorrencias(user_id)

    # --- ABA 1: GERAR LANÇAMENTOS ---
    with tab_gerar:
        st.subheader("Lançamento Rápido")
        st.write("Use esta função para lançar todas as suas contas fixas no caixa deste mês de uma só vez.")
        
        if df_rec.empty:
            st.warning("Nenhuma conta recorrente cadastrada.")
        else:
            st.dataframe(df_rec, use_container_width=True, hide_index=True)
            
            col_btn, _ = st.columns(2)
            if col_btn.button("✅ Lançar Tudo no Mês Atual", type="primary"):
                contador = 0
                mes_atual = date.today().month
                ano_atual = date.today().year
                
                for _, row in df_rec.iterrows():
                    # Cria a data de vencimento para este mês/ano
                    try:
                        data_venc = date(ano_atual, mes_atual, int(row['dia_vencimento']))
                    except:
                        # Caso dia 31 não exista no mês (ex: Fev), joga pro dia 28
                        data_venc = date(ano_atual, mes_atual, 28)
                    
                    dados = {
                        "data": data_venc,
                        "tipo": row['tipo'],
                        "categoria": row['categoria'],
                        "subcategoria": "Recorrência",
                        "descricao": f"{row['nome']} (Ref. {mes_atual}/{ano_atual})",
                        "valor": row['valor'],
                        "conta": "Conta Padrão",
                        "forma_pagamento": "Boleto/Automático",
                        "status": "Pendente"
                    }
                    salvar_lancamento(user_id, dados)
                    contador += 1
                
                st.success(f"{contador} contas lançadas com sucesso no Caixa!")

    # --- ABA 2: CADASTRAR NOVA ---
    with tab_nova:
        st.subheader("Nova Conta Fixa")
        with st.form("form_rec"):
            nome = st.text_input("Nome (Ex: Aluguel, Netflix)")
            c1, c2 = st.columns(2)
            valor = c1.number_input("Valor (R$)", min_value=0.0)
            dia = c2.number_input("Dia de Vencimento", 1, 31, 10)
            
            tipo = st.selectbox("Tipo", ["Despesa", "Receita"])
            cat = st.text_input("Categoria", value="Moradia")
            
            if st.form_submit_button("Salvar Recorrência"):
                salvar_recorrencia(user_id, nome, valor, cat, dia, tipo)
                st.success("Salvo!")
                st.rerun()
        
        if not df_rec.empty:
            st.divider()
            st.write("Excluir item:")
            lista = df_rec['nome'].tolist()
            item_del = st.selectbox("Selecione", lista)
            if st.button("Excluir"):
                id_del = df_rec[df_rec['nome'] == item_del]['id'].values[0]
                excluir_recorrencia(user_id, int(id_del))
>>>>>>> 1fad148ea27bba7506d08963bb63dfb23e82c4e5
                st.rerun()