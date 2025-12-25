import streamlit as st
from datetime import datetime
import pandas as pd
from modules.database import salvar_lancamento, carregar_dados, excluir_lancamento
# IMPORTAÇÃO CENTRALIZADA
from modules.constants import CATEGORIAS

def show_lancamentos():
    # --- PEGAR USUÁRIO LOGADO ---
    if 'user_id' not in st.session_state:
        st.error("Erro: Usuário não identificado.")
        return
    user_id = st.session_state['user_id']

    # Criação de Abas
    tab_novo, tab_gerenciar = st.tabs(["➕ Novo Lançamento", "❌ Gerenciar / Excluir"])

    # ===================================================
    # ABA 1: ADICIONAR NOVO
    # ===================================================
    with tab_novo:
        st.header("📝 Registrar Movimentação (Caixa)")
        st.caption("Use esta tela para movimentações que afetam seu saldo IMEDIATAMENTE (Débito, PIX, Dinheiro). Compras no Crédito devem ir para o menu 'Cartões'.")

        # Usa as categorias do arquivo central constants.py
        mapa_categorias = CATEGORIAS

        col1, col2 = st.columns(2)
        data = col1.date_input("Data", datetime.today())
        tipo = col2.selectbox("Tipo", options=list(mapa_categorias.keys()), key="sb_tipo")
        
        col3, col4 = st.columns(2)
        opcoes_categoria = list(mapa_categorias[tipo].keys())
        categoria = col3.selectbox("Categoria", options=opcoes_categoria, key="sb_categoria")
        
        opcoes_subcategoria = mapa_categorias[tipo][categoria]
        subcategoria = col4.selectbox("Subcategoria", options=opcoes_subcategoria, key="sb_subcategoria")
        
        descricao = st.text_input("Descrição", placeholder="Ex: Jantar no Outback")
        
        # --- LINHA DE VALORES E CONTA ---
        col5, col6, col7 = st.columns(3)
        
        # Coluna 5: Valor
        valor = col5.number_input("Valor (R$)", min_value=0.01, format="%.2f", step=10.00)
        
        # Coluna 6: Forma de Pagamento e Instituição
        with col6:
            metodo_pagamento = st.selectbox(
                "Forma de Pagamento", 
                ["PIX", "Transferência Bancária", "Cartão de Débito", "Boleto", "Dinheiro", "Cheque", "Vale Alimentação"],
                key="sb_metodo"
            )
            
            bancos_disponiveis = ["Nubank", "Sicredi", "Sicoob", "BNDES", "Banco do Brasil", "Bradesco", "Itaú", "Santander", "Caixa", "Inter", "C6 Bank", "Investimento"]
            
            if metodo_pagamento in ["PIX", "Transferência Bancária", "Cartão de Débito", "Boleto"]:
                instituicao = st.selectbox("Instituição Financeira", bancos_disponiveis, key="sb_instituicao")
                conta_final = instituicao
            elif metodo_pagamento == "Vale Alimentação":
                conta_final = "Vale Alimentação"
            else:
                # Dinheiro ou Cheque
                conta_final = "Carteira"

        # Coluna 7: Status
        status = col7.selectbox("Status", ["Pago/Recebido", "Pendente", "Agendado"], key="sb_status")
        
        st.markdown("---")
        
        if st.button("💾 Salvar Lançamento", type="primary", use_container_width=True):
            novo_dado = {
                "data": data.strftime("%Y-%m-%d"),
                "tipo": tipo,
                "categoria": categoria,
                "subcategoria": subcategoria,
                "descricao": descricao,
                "valor": valor,
                "conta": conta_final,
                "forma_pagamento": metodo_pagamento,
                "status": status
            }
            salvar_lancamento(user_id, novo_dado)
            st.toast("Lançamento salvo com sucesso!", icon="✅")

        # --- HISTÓRICO RECENTE ---
        st.divider()
        st.subheader("Últimos Registros")
        
        df = carregar_dados(user_id)
        if not df.empty:
            df = df.sort_values(by="data", ascending=False)
            
            st.dataframe(
                df[['data', 'tipo', 'categoria', 'valor', 'conta', 'status']].head(20),
                use_container_width=True,
                hide_index=True,
                height=300,
                column_config={
                    "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                    "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")
                }
            )

    # ===================================================
    # ABA 2: GERENCIAR / EXCLUIR
    # ===================================================
    with tab_gerenciar:
        st.header("🗂️ Histórico Completo")
        
        df = carregar_dados(user_id)
        
        if df.empty:
            st.info("Nenhum lançamento encontrado.")
        else:
            df = df.sort_values(by="data", ascending=False)
            
            filtro_texto = st.text_input("🔍 Buscar (Descrição ou Categoria)", placeholder="Digite para filtrar...")
            if filtro_texto:
                df = df[
                    df['descricao'].str.contains(filtro_texto, case=False, na=False) | 
                    df['categoria'].str.contains(filtro_texto, case=False, na=False)
                ]

            st.dataframe(
                df, 
                use_container_width=True,
                column_config={
                    "id": st.column_config.NumberColumn("ID", format="%d"),
                    "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                    "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY")
                }
            )
            
            st.divider()
            st.subheader("🗑️ Excluir Lançamento")
            
            if not df.empty:
                def formatar_opcao(row):
                    try:
                        data_fmt = row['data'].strftime('%d/%m/%Y') if pd.notnull(row['data']) else "DATA INVÁLIDA"
                    except:
                        data_fmt = "ERRO DATA"
                    return f"ID: {row['id']} | {data_fmt} | {row['descricao']} | R$ {row['valor']:.2f}"

                opcoes_exclusao = df.apply(formatar_opcao, axis=1)
                
                escolha = st.selectbox("Selecione o item para excluir:", options=opcoes_exclusao)
                
                if escolha:
                    id_para_excluir = int(escolha.split(" |")[0].replace("ID: ", ""))
                    
                    col_btn1, col_btn2 = st.columns([1, 4])
                    if col_btn1.button("❌ Excluir Item", type="secondary"):
                        sucesso = excluir_lancamento(user_id, id_para_excluir)
                        if sucesso:
                            st.success("Item excluído! Atualizando...")
                            st.rerun()
                        else:
                            st.error("Erro ao excluir.")
            else:
                st.info("Nenhum item corresponde à busca.")