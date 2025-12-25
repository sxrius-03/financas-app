import streamlit as st
import pandas as pd
from datetime import date
from modules.constants import LISTA_CATEGORIAS_DESPESA, LISTA_CATEGORIAS_RECEITA
from modules.database import salvar_recorrencia, carregar_recorrencias, excluir_recorrencia, salvar_lancamento, atualizar_recorrencia

def show_recorrencias():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']
    
    st.header("🔄 Contas Fixas & Assinaturas")
    
    tab_gerar, tab_nova, tab_gerenciar = st.tabs(["🚀 Gerar do Mês", "➕ Nova Conta", "✏️ Gerenciar / Editar"])
    
    df_rec = carregar_recorrencias(user_id)

    # --- ABA 1: GERAR LANÇAMENTOS ---
    with tab_gerar:
        st.subheader("Lançamento Rápido")
        st.write("Use esta função para lançar todas as suas contas fixas no caixa deste mês de uma só vez.")
        
        if df_rec.empty:
            st.warning("Nenhuma conta recorrente cadastrada.")
        else:
            st.dataframe(df_rec[['nome', 'valor', 'dia_vencimento', 'categoria', 'tipo']], use_container_width=True, hide_index=True)
            
            col_btn, _ = st.columns(2)
            if col_btn.button("✅ Lançar Tudo no Mês Atual", type="primary"):
                contador = 0
                mes_atual = date.today().month
                ano_atual = date.today().year
                
                for _, row in df_rec.iterrows():
                    try:
                        data_venc = date(ano_atual, mes_atual, int(row['dia_vencimento']))
                    except:
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
            
            tipo = st.selectbox("Tipo", ["Despesa", "Receita"], key="tipo_new")
            
            opcoes_cat = LISTA_CATEGORIAS_DESPESA if tipo == "Despesa" else LISTA_CATEGORIAS_RECEITA
            cat = st.selectbox("Categoria", options=opcoes_cat, key="cat_new")
            
            if st.form_submit_button("Salvar Recorrência"):
                salvar_recorrencia(user_id, nome, valor, cat, dia, tipo)
                st.success("Salvo!")
                st.rerun()

    # --- ABA 3: GERENCIAR / EDITAR ---
    with tab_gerenciar:
        st.subheader("Editar ou Excluir")
        
        if df_rec.empty:
            st.info("Nada para editar.")
        else:
            opcoes_editar = df_rec.apply(lambda x: f"{x['id']} - {x['nome']} (R$ {x['valor']})", axis=1)
            escolha = st.selectbox("Selecione a conta para alterar:", options=opcoes_editar)
            
            id_selecionado = int(escolha.split(" -")[0])
            dados_atuais = df_rec[df_rec['id'] == id_selecionado].iloc[0]
            
            st.divider()
            st.write(f"**Editando:** {dados_atuais['nome']}")
            
            with st.form("form_editar_rec"):
                e_nome = st.text_input("Nome", value=dados_atuais['nome'])
                
                ec1, ec2 = st.columns(2)
                e_valor = ec1.number_input("Valor (R$)", min_value=0.0, value=float(dados_atuais['valor']))
                e_dia = ec2.number_input("Dia Vencimento", 1, 31, int(dados_atuais['dia_vencimento']))
                
                e_tipo = st.selectbox("Tipo", ["Despesa", "Receita"], index=0 if dados_atuais['tipo'] == "Despesa" else 1)
                e_opcoes_cat = LISTA_CATEGORIAS_DESPESA if e_tipo == "Despesa" else LISTA_CATEGORIAS_RECEITA
                
                try:
                    idx_cat = e_opcoes_cat.index(dados_atuais['categoria'])
                except:
                    idx_cat = 0
                
                e_cat = st.selectbox("Categoria", options=e_opcoes_cat, index=idx_cat)
                
                if st.form_submit_button("💾 Atualizar Dados"):
                    atualizar_recorrencia(user_id, id_selecionado, e_nome, e_valor, e_cat, e_dia, e_tipo)
                    st.success("Atualizado com sucesso!")
                    st.rerun()
            
            st.markdown("---")
            col_del, _ = st.columns([1, 3])
            if col_del.button("🗑️ Excluir esta conta permanentemente", type="secondary"):
                excluir_recorrencia(user_id, id_selecionado)
                st.warning("Item excluído.")
                st.rerun()