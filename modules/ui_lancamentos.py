import streamlit as st
from datetime import datetime
import pandas as pd
from modules.database import salvar_lancamento, carregar_dados, excluir_lancamento, atualizar_lancamento
from modules.constants import CATEGORIAS

def show_lancamentos():
    if 'user_id' not in st.session_state:
        st.error("Erro: Usuário não identificado.")
        return
    user_id = st.session_state['user_id']

    tab_novo, tab_gerenciar = st.tabs(["➕ Novo Lançamento", "✏️ Gerenciar / Editar / Excluir"])

    # ABA 1: ADICIONAR (MANTIDA IGUAL, SÓ USANDO CONSTANTS)
    with tab_novo:
        st.header("📝 Registrar Movimentação (Caixa)")
        st.caption("Use esta tela para movimentações que afetam seu saldo IMEDIATAMENTE (Débito, PIX, Dinheiro).")

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
        
        col5, col6, col7 = st.columns(3)
        valor = col5.number_input("Valor (R$)", min_value=0.01, format="%.2f", step=10.00)
        
        with col6:
            metodo_pagamento = st.selectbox(
                "Forma de Pagamento", 
                ["PIX", "Transferência Bancária", "Cartão de Débito", "Boleto", "Dinheiro", "Cheque", "Vale Alimentação"],
                key="sb_metodo"
            )
            bancos_disponiveis = ["Nubank", "Sicredi", "Sicoob", "BNDES", "Banco do Brasil", "Bradesco", "Itaú", "Santander", "Caixa", "Inter", "C6 Bank", "Investimento"]
            
            if metodo_pagamento in ["PIX", "Transferência Bancária", "Cartão de Débito", "Boleto"]:
                conta_final = st.selectbox("Instituição Financeira", bancos_disponiveis, key="sb_instituicao")
            elif metodo_pagamento == "Vale Alimentação":
                conta_final = "Vale Alimentação"
            else:
                conta_final = "Carteira"

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

        # Histórico Recente
        st.divider()
        st.subheader("Últimos Registros")
        df = carregar_dados(user_id)
        if not df.empty:
            df = df.sort_values(by="data", ascending=False)
            st.dataframe(
                df[['data', 'tipo', 'categoria', 'valor', 'conta', 'status']].head(10),
                use_container_width=True, hide_index=True,
                column_config={"data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"), "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")}
            )

    # ABA 2: GERENCIAR / EDITAR
    with tab_gerenciar:
        st.header("🗂️ Histórico Completo")
        df = carregar_dados(user_id)
        
        if df.empty:
            st.info("Nenhum lançamento encontrado.")
        else:
            df = df.sort_values(by="data", ascending=False)
            
            # Seletor para Editar
            st.subheader("✏️ Editar Lançamento")
            opcoes_editar = df.apply(lambda row: f"ID: {row['id']} | {row['data'].strftime('%d/%m/%Y')} | {row['descricao']} | R$ {row['valor']:.2f}", axis=1)
            escolha_editar = st.selectbox("Selecione para editar:", options=opcoes_editar)
            
            if escolha_editar:
                id_edit = int(escolha_editar.split(" |")[0].replace("ID: ", ""))
                dados_atuais = df[df['id'] == id_edit].iloc[0]
                
                with st.form(f"form_edit_{id_edit}"):
                    ec1, ec2 = st.columns(2)
                    e_data = ec1.date_input("Data", value=dados_atuais['data'])
                    e_tipo = ec2.selectbox("Tipo", list(mapa_categorias.keys()), index=0 if dados_atuais['tipo']=="Despesa" else 1)
                    
                    ec3, ec4 = st.columns(2)
                    e_cat_opts = list(mapa_categorias[e_tipo].keys())
                    try: idx_cat = e_cat_opts.index(dados_atuais['categoria'])
                    except: idx_cat = 0
                    e_cat = ec3.selectbox("Categoria", e_cat_opts, index=idx_cat)
                    
                    e_sub_opts = mapa_categorias[e_tipo][e_cat]
                    try: idx_sub = e_sub_opts.index(dados_atuais['subcategoria'])
                    except: idx_sub = 0
                    e_sub = ec4.selectbox("Subcategoria", e_sub_opts, index=idx_sub)
                    
                    e_desc = st.text_input("Descrição", value=dados_atuais['descricao'])
                    
                    ec5, ec6, ec7 = st.columns(3)
                    e_val = ec5.number_input("Valor", value=float(dados_atuais['valor']), min_value=0.01)
                    
                    # Simplificação no Edit para a conta, mantém a string original ou permite trocar
                    # Para ser perfeito precisaria da mesma logica condicional do Add, mas vamos simplificar
                    bancos_completos = bancos_disponiveis + ["Vale Alimentação", "Carteira"]
                    try: idx_banco = bancos_completos.index(dados_atuais['conta'])
                    except: idx_banco = 0
                    e_conta = ec6.selectbox("Conta", bancos_completos, index=idx_banco)
                    
                    try: idx_stat = ["Pago/Recebido", "Pendente", "Agendado"].index(dados_atuais['status'])
                    except: idx_stat = 0
                    e_status = ec7.selectbox("Status", ["Pago/Recebido", "Pendente", "Agendado"], index=idx_stat)
                    
                    c_save, c_del = st.columns([1, 4])
                    if c_save.form_submit_button("💾 Salvar Alterações"):
                        novos_dados = {
                            "data": e_data, "tipo": e_tipo, "categoria": e_cat, "subcategoria": e_sub,
                            "descricao": e_desc, "valor": e_val, "conta": e_conta, 
                            "forma_pagamento": dados_atuais['forma_pagamento'], # Mantém original por simplicidade
                            "status": e_status
                        }
                        atualizar_lancamento(user_id, id_edit, novos_dados)
                        st.success("Atualizado!")
                        st.rerun()
            
            # Opção de Excluir Separada
            st.divider()
            if st.button("🗑️ Excluir este item permanentemente", type="secondary"):
                excluir_lancamento(user_id, id_edit)
                st.rerun()
            
            st.dataframe(df, use_container_width=True, hide_index=True)