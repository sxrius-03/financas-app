import streamlit as st
import pandas as pd
from datetime import date
from modules.database import (
    salvar_recorrencia, carregar_recorrencias, excluir_recorrencia, 
    salvar_lancamento, atualizar_recorrencia, carregar_dados
)
from modules.constants import LISTA_CATEGORIAS_DESPESA

def show_despesas_fixas():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']
    
    st.header("📉 Contas Fixas & Assinaturas")
    st.caption("Gerencie apenas suas obrigações de pagamento mensal.")
    
    tab_controle, tab_config = st.tabs(["✅ Contas do Mês", "⚙️ Cadastrar Conta"])
    
    # CARREGA TUDO E FILTRA SÓ DESPESAS
    df_all = carregar_recorrencias(user_id)
    if not df_all.empty:
        df_fixas = df_all[df_all['tipo'] == 'Despesa'].copy()
    else:
        df_fixas = pd.DataFrame()

    with tab_controle:
        if df_fixas.empty:
            st.info("Nenhuma despesa fixa cadastrada.")
        else:
            mes_atual = date.today().month
            ano_atual = date.today().year
            
            st.subheader(f"Vencimentos: {mes_atual}/{ano_atual}")
            
            # Busca pagamentos já feitos
            df_lancamentos = carregar_dados(user_id)
            itens_pagos = []
            if not df_lancamentos.empty:
                df_lancamentos['data'] = pd.to_datetime(df_lancamentos['data'])
                mask = (df_lancamentos['data'].dt.month == mes_atual) & \
                       (df_lancamentos['data'].dt.year == ano_atual) & \
                       (df_lancamentos['tipo'] == "Despesa")
                itens_pagos = df_lancamentos[mask]['descricao'].tolist()

            # Monta lista
            status_list = []
            for _, row in df_fixas.iterrows():
                foi_pago = any(row['nome'] in item for item in itens_pagos)
                
                status = "✅ Pago" if foi_pago else "📅 A Pagar"
                if not foi_pago and date.today().day > int(row['dia_vencimento']):
                    status = "⚠️ Atrasado"
                
                status_list.append({
                    "id": row['id'], "Dia": row['dia_vencimento'],
                    "Nome": row['nome'], "Valor": row['valor'],
                    "Status": status
                })
            
            df_status = pd.DataFrame(status_list).sort_values(by="Dia")
            
            # Totais
            total_mes = df_status['Valor'].sum()
            total_pago = df_status[df_status['Status'] == "✅ Pago"]['Valor'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Contas", f"R$ {total_mes:,.2f}")
            c2.metric("Já Pago", f"R$ {total_pago:,.2f}")
            c3.metric("Falta Pagar", f"R$ {total_mes - total_pago:,.2f}", delta_color="inverse")
            
            st.divider()
            
            for idx, row in df_status.iterrows():
                with st.container():
                    c_icon, c_dia, c_nome, c_val, c_btn = st.columns([0.5, 0.8, 3, 1.5, 2])
                    
                    icon = "✅" if row['Status']=="✅ Pago" else "🔴"
                    if "Atrasado" in row['Status']: icon = "🔥"
                    
                    c_icon.write(f"## {icon}")
                    c_dia.write(f"**Dia {row['Dia']}**")
                    c_nome.write(f"**{row['Nome']}**")
                    c_val.write(f"R$ {row['Valor']:,.2f}")
                    
                    if row['Status'] != "✅ Pago":
                        if c_btn.button("Pagar Conta", key=f"pay_{row['id']}"):
                            try: d_venc = date(ano_atual, mes_atual, int(row['Dia']))
                            except: d_venc = date(ano_atual, mes_atual, 28)
                            
                            dados = {
                                "data": d_venc, "tipo": "Despesa", "categoria": "Moradia", # Simplificação
                                "subcategoria": "Conta Fixa", "descricao": f"{row['Nome']} (Ref. {mes_atual}/{ano_atual})",
                                "valor": row['Valor'], "conta": "Nubank", "forma_pagamento": "Boleto",
                                "status": "Pago/Recebido"
                            }
                            salvar_lancamento(user_id, dados)
                            st.toast("Conta paga!")
                            st.rerun()
                    else:
                        c_btn.caption("Paga")
                    st.markdown("---")

    with tab_config:
        st.subheader("Nova Conta Fixa")
        with st.form("form_nova_despesa"):
            nome = st.text_input("Nome (Ex: Internet, Luz)")
            c1, c2 = st.columns(2)
            valor = c1.number_input("Valor (R$)", min_value=0.0)
            dia = c2.number_input("Dia Vencimento", 1, 31, 10)
            cat = st.selectbox("Categoria", LISTA_CATEGORIAS_DESPESA)
            
            if st.form_submit_button("Salvar Conta"):
                # Força tipo='Despesa'
                salvar_recorrencia(user_id, nome, valor, cat, dia, "Despesa")
                st.success("Salvo!")
                st.rerun()
                
        if not df_fixas.empty:
            st.divider()
            st.write("Excluir Conta")
            opt = df_fixas.apply(lambda x: f"{x['nome']} (R$ {x['valor']})", axis=1)
            sel = st.selectbox("Selecione:", opt)
            if st.button("🗑️ Remover Conta"):
                row = df_fixas[df_fixas.apply(lambda x: f"{x['nome']} (R$ {x['valor']})" == sel, axis=1)].iloc[0]
                excluir_recorrencia(user_id, int(row['id']))
                st.rerun()