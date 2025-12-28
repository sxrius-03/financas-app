import streamlit as st
import pandas as pd
from datetime import date
from modules.database import (
    salvar_recorrencia, carregar_recorrencias, excluir_recorrencia, 
    salvar_lancamento, atualizar_recorrencia, carregar_dados
)
from modules.constants import LISTA_CATEGORIAS_RECEITA

def show_receitas_fixas():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']
    
    st.header("💰 Rendas Fixas & Salários")
    st.caption("Gerencie suas entradas recorrentes (Salário, Aluguéis, Pró-labore).")
    
    tab_controle, tab_config = st.tabs(["✅ Recebimentos do Mês", "⚙️ Cadastrar Renda"])
    
    # Carrega TUDO, mas filtra apenas RECEITA
    df_all = carregar_recorrencias(user_id)
    if not df_all.empty:
        df_fixas = df_all[df_all['tipo'] == 'Receita'].copy()
    else:
        df_fixas = pd.DataFrame()

    # ===================================================
    # ABA 1: CONTROLE DO MÊS
    # ===================================================
    with tab_controle:
        if df_fixas.empty:
            st.info("Nenhuma renda fixa cadastrada.")
        else:
            mes_atual = date.today().month
            ano_atual = date.today().year
            
            st.subheader(f"Competência: {mes_atual}/{ano_atual}")
            
            # Verifica o que já caiu na conta
            df_lancamentos = carregar_dados(user_id)
            itens_recebidos = []
            if not df_lancamentos.empty:
                df_lancamentos['data'] = pd.to_datetime(df_lancamentos['data'])
                mask = (df_lancamentos['data'].dt.month == mes_atual) & \
                       (df_lancamentos['data'].dt.year == ano_atual) & \
                       (df_lancamentos['tipo'] == "Receita")
                itens_recebidos = df_lancamentos[mask]['descricao'].tolist()

            # Monta lista visual
            status_list = []
            for _, row in df_fixas.iterrows():
                ja_recebeu = any(row['nome'] in item for item in itens_recebidos)
                status_list.append({
                    "id": row['id'], "Dia": row['dia_vencimento'],
                    "Nome": row['nome'], "Valor": row['valor'],
                    "Categoria": row['categoria'],
                    "Status": "✅ Recebido" if ja_recebeu else "⏳ A Receber"
                })
            
            df_status = pd.DataFrame(status_list).sort_values(by="Dia")
            
            # Métricas
            total_previsto = df_status['Valor'].sum()
            total_recebido = df_status[df_status['Status'] == "✅ Recebido"]['Valor'].sum()
            
            c1, c2 = st.columns(2)
            c1.metric("Renda Mensal Fixa", f"R$ {total_previsto:,.2f}")
            c2.metric("Já Caiu na Conta", f"R$ {total_recebido:,.2f}", delta=f"{total_previsto-total_recebido:,.2f} restantes")
            
            st.divider()
            
            # Lista de Ação
            for idx, row in df_status.iterrows():
                with st.container():
                    c_icon, c_dia, c_info, c_val, c_btn = st.columns([0.5, 0.8, 3, 1.5, 2])
                    
                    c_icon.write("💰" if row['Status'] == "✅ Recebido" else "⚪")
                    c_dia.write(f"**Dia {row['Dia']}**")
                    c_info.write(f"**{row['Nome']}**\n<span style='color:grey;font-size:0.8em'>{row['Categoria']}</span>", unsafe_allow_html=True)
                    c_val.write(f"R$ {row['Valor']:,.2f}")
                    
                    if row['Status'] != "✅ Recebido":
                        if c_btn.button(f"Confirmar Entrada", key=f"btn_rec_{row['id']}"):
                            try: d_venc = date(ano_atual, mes_atual, int(row['Dia']))
                            except: d_venc = date(ano_atual, mes_atual, 28)
                            
                            dados = {
                                "data": d_venc, "tipo": "Receita", "categoria": row['Categoria'],
                                "subcategoria": "Salário/Fixa", "descricao": f"{row['Nome']} (Ref. {mes_atual}/{ano_atual})",
                                "valor": row['Valor'], "conta": "Nubank", "forma_pagamento": "Depósito",
                                "status": "Pago/Recebido"
                            }
                            salvar_lancamento(user_id, dados)
                            st.toast("Entrada registrada!")
                            st.rerun()
                    else:
                        c_btn.caption("Registrado")
                    st.markdown("---")

    # ===================================================
    # ABA 2: CADASTRO
    # ===================================================
    with tab_config:
        st.subheader("Nova Fonte de Renda")
        with st.form("form_nova_receita"):
            nome = st.text_input("Nome (Ex: Salário, Aluguel)")
            c1, c2 = st.columns(2)
            valor = c1.number_input("Valor Líquido (R$)", min_value=0.0)
            dia = c2.number_input("Dia do Depósito", 1, 31, 5)
            cat = st.selectbox("Categoria", LISTA_CATEGORIAS_RECEITA)
            
            if st.form_submit_button("Salvar Renda Fixa"):
                # Força tipo='Receita'
                salvar_recorrencia(user_id, nome, valor, cat, dia, "Receita")
                st.success("Salvo!")
                st.rerun()
        
        if not df_fixas.empty:
            st.divider()
            st.write("Excluir Renda")
            opt = df_fixas.apply(lambda x: f"{x['nome']} (R$ {x['valor']})", axis=1)
            sel = st.selectbox("Selecione:", opt)
            if st.button("🗑️ Remover Renda"):
                # Lógica para achar ID pelo nome/valor (simplificada)
                row = df_fixas[df_fixas.apply(lambda x: f"{x['nome']} (R$ {x['valor']})" == sel, axis=1)].iloc[0]
                excluir_recorrencia(user_id, int(row['id']))
                st.rerun()