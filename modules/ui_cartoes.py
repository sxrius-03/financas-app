import streamlit as st
import pandas as pd
from datetime import datetime, date
from modules.database import salvar_cartao, carregar_cartoes, excluir_cartao, salvar_compra_credito, carregar_fatura

def show_cartoes():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']
    
    st.header("💳 Gestão de Cartões de Crédito")
    
    tab_fatura, tab_compra, tab_gerenciar = st.tabs(["📄 Ver Faturas", "🛍️ Nova Compra", "⚙️ Cadastrar Cartão"])
    
    df_cartoes = carregar_cartoes(user_id)

    # --- ABA 1: VER FATURAS ---
    with tab_fatura:
        if df_cartoes.empty:
            st.warning("Cadastre um cartão primeiro na aba 'Cadastrar Cartão'.")
        else:
            c1, c2 = st.columns(2)
            # Selecionar Cartão
            cartao_selecionado = c1.selectbox("Selecione o Cartão", df_cartoes['nome_cartao'].tolist())
            id_cartao = df_cartoes[df_cartoes['nome_cartao'] == cartao_selecionado]['id'].values[0]
            
            # Selecionar Mês da Fatura (Gera lista de datas para o filtro)
            # Cria uma lista de meses (Ex: 2025-01-01, 2025-02-01...)
            mes_atual = date.today().replace(day=1)
            opcoes_meses = [mes_atual.replace(month=m) for m in range(1, 13)] # Jan a Dez do ano atual
            # Adiciona ano que vem para garantir
            try:
                opcoes_meses += [mes_atual.replace(year=mes_atual.year+1, month=m) for m in range(1, 13)]
            except: pass # Evita erro de bissexto
            
            mes_escolhido = c2.selectbox(
                "Mês da Fatura", 
                opcoes_meses, 
                format_func=lambda x: x.strftime("%B/%Y"),
                index=mes_atual.month - 1 # Tenta selecionar mês atual
            )
            
            # Busca Fatura
            df_fatura = carregar_fatura(user_id, id_cartao, mes_escolhido)
            
            st.divider()
            
            if df_fatura.empty:
                st.info(f"Nenhuma fatura encontrada para {cartao_selecionado} em {mes_escolhido.strftime('%m/%Y')}.")
            else:
                total_fatura = df_fatura['valor_parcela'].sum()
                st.metric(f"Total da Fatura ({mes_escolhido.strftime('%m/%Y')})", f"R$ {total_fatura:,.2f}")
                
                st.dataframe(
                    df_fatura[['data_compra', 'descricao', 'parcela_numero', 'qtd_parcelas', 'valor_parcela']],
                    use_container_width=True,
                    column_config={
                        "data_compra": st.column_config.DateColumn("Data Compra", format="DD/MM/YYYY"),
                        "valor_parcela": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                        "parcela_numero": "Parc.",
                        "qtd_parcelas": "Total Parc."
                    }
                )

    # --- ABA 2: NOVA COMPRA ---
    with tab_compra:
        st.subheader("Registrar Gasto no Crédito")
        if df_cartoes.empty:
            st.warning("Cadastre um cartão primeiro!")
        else:
            with st.form("form_compra_credito"):
                c1, c2 = st.columns(2)
                cartao_nome = c1.selectbox("Cartão Usado", df_cartoes['nome_cartao'].tolist())
                data_compra = c2.date_input("Data da Compra", date.today())
                
                desc = st.text_input("Descrição (Loja/Item)")
                cat = st.selectbox("Categoria", ["Alimentação", "Transporte", "Lazer", "Compras", "Serviços", "Viagem", "Outros"])
                
                c3, c4 = st.columns(2)
                valor_total = c3.number_input("Valor TOTAL da Compra (R$)", min_value=0.01)
                parcelas = c4.number_input("Nº de Parcelas", min_value=1, step=1, value=1)
                
                if st.form_submit_button("Lançar Compra", type="primary"):
                    # Pega ID e Dia de Fechamento do cartão escolhido
                    info_cartao = df_cartoes[df_cartoes['nome_cartao'] == cartao_nome].iloc[0]
                    
                    salvar_compra_credito(
                        user_id, 
                        int(info_cartao['id']), 
                        data_compra, 
                        desc, 
                        cat, 
                        valor_total, 
                        int(parcelas), 
                        int(info_cartao['dia_fechamento'])
                    )
                    st.success("Compra registrada e parcelas geradas!")

    # --- ABA 3: GERENCIAR CARTÕES ---
    with tab_gerenciar:
        st.subheader("Cadastrar Novo Cartão")
        with st.form("form_novo_cartao"):
            nome = st.text_input("Nome do Cartão (Ex: Nubank, Black)")
            c1, c2 = st.columns(2)
            fechamento = c1.number_input("Dia Fechamento", 1, 31, 1)
            vencimento = c2.number_input("Dia Vencimento", 1, 31, 10)
            
            if st.form_submit_button("Salvar Cartão"):
                salvar_cartao(user_id, nome, fechamento, vencimento)
                st.success("Cartão cadastrado!")
                st.rerun()
        
        st.divider()
        st.subheader("Meus Cartões")
        if not df_cartoes.empty:
            st.dataframe(df_cartoes, hide_index=True)
            
            cartao_del = st.selectbox("Excluir Cartão", df_cartoes['nome_cartao'].tolist(), key="del_cartao")
            if st.button("🗑️ Excluir Selecionado"):
                id_del = df_cartoes[df_cartoes['nome_cartao'] == cartao_del]['id'].values[0]
                excluir_cartao(user_id, int(id_del))
                st.success("Cartão excluído.")
                st.rerun()