import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from modules.database import (
    salvar_reserva_conta, carregar_reservas, salvar_transacao_reserva, 
    carregar_extrato_reserva, migrar_dados_antigos_para_reserva, 
    salvar_lancamento, excluir_reserva_conta
)
from modules.database import carregar_dados # Para calcular sobrevivência

def show_reserva():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']

    st.header("🛡️ Reserva & Segurança Financeira")
    
    # --- BOTÃO DE MIGRAÇÃO (Visível apenas se necessário) ---
    with st.expander("🔧 Ferramentas de Sistema", expanded=False):
        st.write("Se você já usava o sistema e tinha lançamentos na categoria 'Investimentos (Aportes)', clique abaixo para mover tudo para cá.")
        if st.button("🔄 Migrar Dados Antigos para Reserva"):
            qtd = migrar_dados_antigos_para_reserva(user_id)
            if qtd > 0:
                st.success(f"{qtd} registros migrados com sucesso!")
                st.rerun()
            else:
                st.info("Nenhum registro antigo encontrado para migrar.")

    tab_visao, tab_operar, tab_config = st.tabs(["📊 Visão Geral & Rendimento", "💰 Aportar / Resgatar / Atualizar", "⚙️ Configurar Contas"])

    df_reservas = carregar_reservas(user_id)
    
    # ===================================================
    # ABA 1: VISÃO GERAL
    # ===================================================
    with tab_visao:
        if df_reservas.empty:
            st.warning("Nenhuma reserva configurada. Vá na aba 'Configurar Contas'.")
        else:
            saldo_total = df_reservas['saldo_atual'].sum()
            meta_total = df_reservas['meta_valor'].sum()
            
            # 1. CÁLCULO DE SOBREVIVÊNCIA (RUNWAY)
            # Pega média de despesas dos últimos 3 meses do Dashboard
            df_dash = carregar_dados(user_id)
            media_gastos = 0
            if not df_dash.empty:
                df_dash['data'] = pd.to_datetime(df_dash['data'])
                # Filtra últimos 90 dias
                mask = (df_dash['data'] > pd.Timestamp.now() - pd.DateOffset(days=90)) & (df_dash['tipo'] == 'Despesa')
                total_90d = df_dash[mask]['valor'].sum()
                media_gastos = total_90d / 3 if total_90d > 0 else 0
            
            meses_sobrevivencia = saldo_total / media_gastos if media_gastos > 0 else 0
            
            # KPIs
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Saldo Total Guardado", f"R$ {saldo_total:,.2f}")
            c2.metric("Meta de Segurança", f"R$ {meta_total:,.2f}")
            c3.metric("Custo de Vida Médio", f"R$ {media_gastos:,.2f}/mês", help="Baseado nos últimos 3 meses de despesas.")
            c4.metric("Tempo de Sobrevivência", f"{meses_sobrevivencia:.1f} Meses", delta="Proteção", delta_color="normal")
            
            st.progress(min(saldo_total / meta_total, 1.0) if meta_total > 0 else 0, text=f"Progresso da Meta: {saldo_total/meta_total*100:.1f}%")
            
            st.divider()
            
            g1, g2 = st.columns(2)
            
            # Gráfico de Composição
            with g1:
                fig_pie = px.pie(df_reservas, values='saldo_atual', names='nome', title="Divisão das Reservas", hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)
            
            # Gráfico de Histórico
            with g2:
                df_ext = carregar_extrato_reserva(user_id)
                if not df_ext.empty:
                    # Cria evolução acumulada
                    df_ext = df_ext.sort_values('data')
                    # Precisamos reconstruir o saldo dia a dia. Simplificação: Saldo por transação
                    # Idealmente seria complexo, vamos mostrar Barras de Movimentação
                    fig_bar = px.bar(df_ext, x='data', y='valor', color='tipo', title="Histórico de Movimentações", barmode='group')
                    st.plotly_chart(fig_bar, use_container_width=True)
                else:
                    st.info("Sem histórico para gráfico.")

    # ===================================================
    # ABA 2: OPERAÇÕES (Aporte, Resgate, Rendimento)
    # ===================================================
    with tab_operar:
        st.subheader("Movimentar Reserva")
        if df_reservas.empty:
            st.warning("Crie uma conta na aba ao lado.")
        else:
            tipo_mov = st.radio("O que você quer fazer?", ["➕ Aportar (Guardar)", "➖ Resgatar (Usar)", "📈 Atualizar Rendimento"], horizontal=True)
            
            with st.form("form_mov_reserva"):
                reserva_nome = st.selectbox("Qual Reserva?", df_reservas['nome'].tolist())
                res_id = int(df_reservas[df_reservas['nome'] == reserva_nome]['id'].values[0])
                
                col_a, col_b = st.columns(2)
                data_mov = col_a.date_input("Data", date.today())
                valor = col_b.number_input("Valor (R$)", min_value=0.01)
                
                desc = st.text_input("Descrição", value="Rendimento Mensal" if tipo_mov == "📈 Atualizar Rendimento" else "")
                
                conta_origem = None
                if tipo_mov == "➕ Aportar (Guardar)":
                    st.info("Isso também criará uma DESPESA no seu Caixa (Lançamentos) automaticamente.")
                    conta_origem = st.selectbox("De onde sai o dinheiro?", ["Nubank", "Bradesco", "Itaú", "Santander", "Caixa", "Carteira"])
                
                elif tipo_mov == "➖ Resgatar (Usar)":
                    st.info("Isso criará uma RECEITA no seu Caixa automaticamente.")
                    conta_origem = st.selectbox("Para onde vai o dinheiro?", ["Nubank", "Bradesco", "Itaú", "Santander", "Caixa", "Carteira"])
                
                if st.form_submit_button("Confirmar Operação"):
                    # 1. Salva na Reserva
                    tipo_banco = 'Rendimento'
                    if "Aportar" in tipo_mov: tipo_banco = 'Aporte'
                    elif "Resgatar" in tipo_mov: tipo_banco = 'Resgate'
                    
                    salvar_transacao_reserva(user_id, res_id, data_mov, tipo_banco, valor, desc)
                    
                    # 2. Espelha no Caixa (Lançamentos) se for Aporte ou Resgate
                    if tipo_banco == 'Aporte':
                        dados_lanc = {
                            "data": data_mov, "tipo": "Despesa", 
                            "categoria": "Financeiro", "subcategoria": "Transferência para Reserva",
                            "descricao": f"Aporte: {reserva_nome}", "valor": valor,
                            "conta": conta_origem, "forma_pagamento": "Transferência", "status": "Pago/Recebido"
                        }
                        salvar_lancamento(user_id, dados_lanc)
                        
                    elif tipo_banco == 'Resgate':
                        dados_lanc = {
                            "data": data_mov, "tipo": "Receita", 
                            "categoria": "Financeiro", "subcategoria": "Resgate de Reserva",
                            "descricao": f"Resgate: {reserva_nome}", "valor": valor,
                            "conta": conta_origem, "forma_pagamento": "Transferência", "status": "Pago/Recebido"
                        }
                        salvar_lancamento(user_id, dados_lanc)
                        
                    st.success("Operação realizada e saldos atualizados!")
                    st.rerun()

            st.divider()
            st.subheader("Extrato Recente")
            df_ext = carregar_extrato_reserva(user_id)
            if not df_ext.empty:
                st.dataframe(df_ext[['data', 'nome_reserva', 'tipo', 'valor', 'descricao']], use_container_width=True)

    # ===================================================
    # ABA 3: CONFIGURAR
    # ===================================================
    with tab_config:
        st.subheader("Cadastrar Novo Pote")
        with st.form("form_new_reserva"):
            nome_pote = st.text_input("Nome (Ex: NuBank Caixinha, CDB Inter)")
            tipo_aplic = st.selectbox("Tipo de Aplicação", ["CDB 100% CDI", "CDB Liquidez Diária", "Tesouro Selic", "LCI/LCA", "Poupança", "Outro"])
            meta = st.number_input("Meta para este pote (R$)", min_value=0.0)
            
            if st.form_submit_button("Criar Reserva"):
                salvar_reserva_conta(user_id, nome_pote, tipo_aplic, meta)
                st.success("Reserva criada!")
                st.rerun()
        
        if not df_reservas.empty:
            st.divider()
            st.write("Excluir Reserva (Cuidado: Apaga histórico dela)")
            res_del = st.selectbox("Selecione", df_reservas['nome'].tolist())
            if st.button("🗑️ Excluir Selecionada"):
                rid = int(df_reservas[df_reservas['nome'] == res_del]['id'].values[0])
                excluir_reserva_conta(user_id, rid)
                st.rerun()