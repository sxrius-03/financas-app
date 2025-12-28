import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from modules.database import (
    salvar_reserva_conta, carregar_reservas, salvar_transacao_reserva, 
    carregar_extrato_reserva, migrar_dados_antigos_para_reserva, 
    salvar_lancamento, excluir_reserva_conta, carregar_dados
)

def show_reserva():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']

    st.header("🛡️ Reserva & Segurança Financeira")
    
    # Ferramenta de Migração Inteligente
    with st.expander("🔧 Ferramentas de Sistema (Correção de Saldo)", expanded=False):
        st.write("Esta ferramenta busca lançamentos antigos de Aporte (Despesa) e Resgate (Receita) e recalcula o saldo das reservas.")
        if st.button("🔄 Migrar (Recalcular Saldo Completo)"):
            qtd = migrar_dados_antigos_para_reserva(user_id)
            if qtd > 0:
                st.success(f"{qtd} transações migradas e saldo recalculado!")
                st.rerun()
            else:
                st.info("Nenhum lançamento antigo encontrado para migrar.")

    tab_visao, tab_operar, tab_config = st.tabs(["📊 Visão Geral", "💰 Movimentações", "⚙️ Configurar"])

    df_reservas = carregar_reservas(user_id)
    
    # --- ABA 1: VISÃO GERAL ---
    with tab_visao:
        if df_reservas.empty:
            st.warning("Nenhuma reserva encontrada. Vá na aba 'Configurar' para criar a primeira.")
        else:
            saldo_total = df_reservas['saldo_atual'].sum()
            meta_total = df_reservas['meta_valor'].sum()
            
            # Cálculo Runway (Sobrevivência)
            df_dash = carregar_dados(user_id)
            media_gastos = 0
            if not df_dash.empty:
                df_dash['data'] = pd.to_datetime(df_dash['data'])
                # Média dos últimos 3 meses
                mask = (df_dash['data'] > pd.Timestamp.now() - pd.DateOffset(days=90)) & (df_dash['tipo'] == 'Despesa')
                total_90d = df_dash[mask]['valor'].sum()
                media_gastos = total_90d / 3 if total_90d > 0 else 0
            
            meses_sobrevivencia = saldo_total / media_gastos if media_gastos > 0 else 0
            
            # Big Numbers
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Saldo Total", f"R$ {saldo_total:,.2f}")
            c2.metric("Meta Total", f"R$ {meta_total:,.2f}")
            c3.metric("Gasto Médio Mensal", f"R$ {media_gastos:,.2f}")
            c4.metric("Autonomia", f"{meses_sobrevivencia:.1f} Meses", delta="Runway")
            
            if meta_total > 0:
                st.progress(min(saldo_total / meta_total, 1.0), text=f"Progresso da Meta: {saldo_total/meta_total*100:.1f}%")
            
            st.divider()
            
            # Tabela de Potes (Agora com Rentabilidade formatada)
            st.subheader("Meus Potes de Reserva")
            
            cols_to_show = ['nome', 'tipo_aplicacao', 'saldo_atual', 'meta_valor']
            # O banco gera a coluna 'rentabilidade' (Ex: "110% CDI") automaticamente na inserção
            if 'rentabilidade' in df_reservas.columns:
                cols_to_show.insert(2, 'rentabilidade')
            
            st.dataframe(
                df_reservas[cols_to_show],
                use_container_width=True,
                column_config={
                    "saldo_atual": st.column_config.NumberColumn("Saldo Atual", format="R$ %.2f"),
                    "meta_valor": st.column_config.NumberColumn("Meta", format="R$ %.2f"),
                    "rentabilidade": "Rendimento Base"
                }
            )

    # --- ABA 2: OPERAÇÕES ---
    with tab_operar:
        st.subheader("Nova Movimentação")
        if df_reservas.empty:
            st.warning("Sem reservas cadastradas.")
        else:
            tipo_mov = st.radio("Ação", ["➕ Aportar (Guardar)", "➖ Resgatar (Usar)", "📈 Render Juros (Atualizar)"], horizontal=True)
            
            with st.form("form_mov"):
                reserva_nome = st.selectbox("Selecione a Reserva", df_reservas['nome'].tolist())
                res_id = int(df_reservas[df_reservas['nome'] == reserva_nome]['id'].values[0])
                
                c_data, c_val = st.columns(2)
                d_mov = c_data.date_input("Data", date.today())
                val = c_val.number_input("Valor (R$)", min_value=0.01)
                desc = st.text_input("Descrição", value="Rendimento Mensal" if "Render" in tipo_mov else "")
                
                conta_cx = None
                if "Aportar" in tipo_mov:
                    st.info("ℹ️ Isso lançará automaticamente uma DESPESA no seu Caixa.")
                    conta_cx = st.selectbox("Saiu de qual conta?", ["Nubank", "Bradesco", "Itaú", "Santander", "Caixa", "Carteira", "Inter"])
                elif "Resgatar" in tipo_mov:
                    st.info("ℹ️ Isso lançará automaticamente uma RECEITA no seu Caixa.")
                    conta_cx = st.selectbox("Entrou em qual conta?", ["Nubank", "Bradesco", "Itaú", "Santander", "Caixa", "Carteira", "Inter"])
                
                if st.form_submit_button("Confirmar Transação"):
                    tipo_db = 'Rendimento'
                    if "Aportar" in tipo_mov: tipo_db = 'Aporte'
                    elif "Resgatar" in tipo_mov: tipo_db = 'Resgate'
                    
                    # 1. Salva na Reserva
                    salvar_transacao_reserva(user_id, res_id, d_mov, tipo_db, val, desc)
                    
                    # 2. Espelha no Caixa (Lançamentos)
                    if tipo_db == 'Aporte':
                        l_dados = {"data": d_mov, "tipo": "Despesa", "categoria": "Financeiro", "subcategoria": "Transf. Reserva", "descricao": f"Aporte: {reserva_nome}", "valor": val, "conta": conta_cx, "forma_pagamento": "Transferência", "status": "Pago/Recebido"}
                        salvar_lancamento(user_id, l_dados)
                    elif tipo_db == 'Resgate':
                        l_dados = {"data": d_mov, "tipo": "Receita", "categoria": "Financeiro", "subcategoria": "Resgate Reserva", "descricao": f"Resgate: {reserva_nome}", "valor": val, "conta": conta_cx, "forma_pagamento": "Transferência", "status": "Pago/Recebido"}
                        salvar_lancamento(user_id, l_dados)
                        
                    st.success("Sucesso! Saldo atualizado.")
                    st.rerun()
            
            st.divider()
            st.subheader("Extrato Recente")
            st.dataframe(carregar_extrato_reserva(user_id), use_container_width=True)

    # --- ABA 3: CONFIGURAR (FLEXÍVEL & ESTRUTURADA) ---
    with tab_config:
        st.subheader("Criar Nova Reserva")
        
        with st.form("form_new"):
            nome = st.text_input("Nome da Reserva (Ex: Fundo de Emergência)")
            
            c1, c2 = st.columns(2)
            tipo = c1.selectbox("Tipo de Aplicação", ["CDB", "LCI/LCA", "Tesouro Direto", "Poupança", "Fundo DI", "Caixinha/Cofre", "Outro"])
            meta = c2.number_input("Meta para este pote (R$)", min_value=0.0)
            
            st.markdown("### 📊 Rentabilidade")
            c3, c4 = st.columns(2)
            # Input Estruturado conforme solicitado
            indice = c3.selectbox("Índice Base", ["CDI", "Selic", "IPCA", "Pré-fixado", "TR", "Poupança", "Outro"])
            taxa = c4.number_input("Taxa (%)", min_value=0.0, value=100.0, step=0.1, help="Ex: Digite 110 para 110% do CDI. Digite 6.5 para IPCA+6.5%.")
            
            if st.form_submit_button("Salvar Nova Reserva"):
                # Envia os dados estruturados para o database atualizado
                salvar_reserva_conta(user_id, nome, tipo, indice, taxa, meta)
                st.success("Reserva criada com sucesso!")
                st.rerun()
        
        if not df_reservas.empty:
            st.divider()
            st.write("Gerenciar Reservas Existentes")
            del_sel = st.selectbox("Selecione para Excluir", df_reservas['nome'].tolist())
            if st.button("🗑️ Apagar Reserva Selecionada"):
                rid = int(df_reservas[df_reservas['nome'] == del_sel]['id'].values[0])
                excluir_reserva_conta(user_id, rid)
                st.rerun()