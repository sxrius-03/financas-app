import streamlit as st
import pandas as pd
from datetime import date, datetime
from modules.database import (
    salvar_recorrencia, carregar_recorrencias, excluir_recorrencia, 
    salvar_lancamento, atualizar_recorrencia, carregar_dados
)
from modules.constants import LISTA_CATEGORIAS_DESPESA, LISTA_CATEGORIAS_RECEITA

def show_despesas_fixas():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']
    
    st.header("📌 Despesas Fixas & Assinaturas")
    st.caption("Gerencie seus compromissos mensais obrigatórios. Isso é a base para sua Projeção Financeira.")
    
    tab_controle, tab_config = st.tabs(["✅ Controle do Mês", "⚙️ Configurar / Cadastrar"])
    
    # Carrega as contas fixas cadastradas
    df_fixas = carregar_recorrencias(user_id)

    # ===================================================
    # ABA 1: CONTROLE DO MÊS (CHECKLIST)
    # ===================================================
    with tab_controle:
        if df_fixas.empty:
            st.warning("Nenhuma despesa fixa cadastrada. Vá na aba 'Configurar'.")
        else:
            mes_atual = date.today().month
            ano_atual = date.today().year
            
            st.subheader(f"Competência: {mes_atual}/{ano_atual}")
            
            # 1. Busca o que já foi lançado no caixa neste mês para comparar
            df_lancamentos = carregar_dados(user_id)
            if not df_lancamentos.empty:
                df_lancamentos['data'] = pd.to_datetime(df_lancamentos['data'])
                # Filtra lançamentos deste mês que vieram de recorrência
                mask = (df_lancamentos['data'].dt.month == mes_atual) & \
                       (df_lancamentos['data'].dt.year == ano_atual) & \
                       (df_lancamentos['subcategoria'] == "Recorrência")
                itens_pagos = df_lancamentos[mask]['descricao'].tolist()
            else:
                itens_pagos = []

            # 2. Monta a tabela de controle visual
            # Vamos verificar quais fixas já estão nos lançamentos (pelo nome aprox)
            
            status_list = []
            for _, row in df_fixas.iterrows():
                # Tenta achar o nome da fixa dentro das descrições lançadas
                # Ex: Fixa "Aluguel" bate com Lançamento "Aluguel (Ref. 12/2025)"
                foi_pago = any(row['nome'] in item for item in itens_pagos)
                
                # Define status
                if foi_pago:
                    status = "✅ Lançado"
                else:
                    hoje = date.today().day
                    dia_venc = int(row['dia_vencimento'])
                    if hoje > dia_venc:
                        status = "⚠️ Atrasado / Pendente"
                    elif hoje == dia_venc:
                        status = "🔔 Vence Hoje"
                    else:
                        status = "📅 A Vencer"
                
                status_list.append({
                    "id": row['id'],
                    "Dia": row['dia_vencimento'],
                    "Nome": row['nome'],
                    "Valor": row['valor'],
                    "Categoria": row['categoria'],
                    "Tipo": row['tipo'],
                    "Status": status
                })
            
            df_status = pd.DataFrame(status_list)
            
            # Ordena por dia
            df_status = df_status.sort_values(by="Dia")
            
            # Exibe Métricas
            total_fixo = df_status['Valor'].sum()
            total_ja_lancado = df_status[df_status['Status'] == "✅ Lançado"]['Valor'].sum()
            falta_lancar = total_fixo - total_ja_lancado
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Fixo Mensal", f"R$ {total_fixo:,.2f}")
            c2.metric("Já Lançado/Pago", f"R$ {total_ja_lancado:,.2f}")
            c3.metric("Falta Lançar", f"R$ {falta_lancar:,.2f}", delta_color="inverse")
            
            st.divider()
            
            # Exibe Tabela com Botões de Ação
            st.write("### 📋 Lista de Obrigações")
            
            # Iterar para criar botões individuais (Streamlit way)
            for idx, row in df_status.iterrows():
                with st.container():
                    c_check, c_dia, c_nome, c_val, c_btn = st.columns([1, 1, 3, 2, 2])
                    
                    # Ícone Visual
                    icon = "✅" if row['Status'] == "✅ Lançado" else "⬜"
                    if "Atrasado" in row['Status']: icon = "⚠️"
                    
                    c_check.write(f"## {icon}")
                    c_dia.write(f"**Dia {row['Dia']}**")
                    c_nome.write(f"{row['Nome']}\n<span style='color:grey;font-size:0.8em'>{row['Categoria']}</span>", unsafe_allow_html=True)
                    c_val.write(f"**R$ {row['Valor']:,.2f}**")
                    
                    # Botão Lançar (Só aparece se não foi lançado)
                    if row['Status'] != "✅ Lançado":
                        if c_btn.button(f"Lançar no Caixa", key=f"btn_lancar_{row['id']}"):
                            # Lógica de Lançamento Automático
                            try:
                                data_venc = date(ano_atual, mes_atual, int(row['Dia']))
                            except:
                                data_venc = date(ano_atual, mes_atual, 28)
                            
                            # Decide conta padrão baseado no tipo
                            conta_padrao = "Nubank" # Pode melhorar isso futuramente
                            
                            dados = {
                                "data": data_venc,
                                "tipo": row['Tipo'],
                                "categoria": row['Categoria'],
                                "subcategoria": "Recorrência",
                                "descricao": f"{row['Nome']} (Ref. {mes_atual}/{ano_atual})",
                                "valor": row['Valor'],
                                "conta": conta_padrao,
                                "forma_pagamento": "Boleto/Automático",
                                "status": "Pago/Recebido" if data_venc <= date.today() else "Pendente"
                            }
                            salvar_lancamento(user_id, dados)
                            st.toast(f"{row['Nome']} lançado no caixa!")
                            st.rerun()
                    else:
                        c_btn.caption("Já registrado.")
                    
                    st.markdown("---")

            # Botão de Lançar TUDO (Para os apressados)
            if falta_lancar > 0:
                if st.button("🚀 Lançar TODAS as pendências restantes no Caixa"):
                    pendentes = df_status[df_status['Status'] != "✅ Lançado"]
                    for _, row in pendentes.iterrows():
                        try: data_venc = date(ano_atual, mes_atual, int(row['Dia']))
                        except: data_venc = date(ano_atual, mes_atual, 28)
                        
                        dados = {
                            "data": data_venc, "tipo": row['Tipo'], "categoria": row['Categoria'],
                            "subcategoria": "Recorrência", "descricao": f"{row['Nome']} (Ref. {mes_atual}/{ano_atual})",
                            "valor": row['Valor'], "conta": "Nubank", "forma_pagamento": "Boleto/Automático",
                            "status": "Pendente"
                        }
                        salvar_lancamento(user_id, dados)
                    st.success("Tudo lançado!")
                    st.rerun()

    # ===================================================
    # ABA 2: CADASTRO / CONFIGURAÇÃO
    # ===================================================
    with tab_config:
        st.subheader("Nova Despesa Fixa")
        with st.form("form_rec"):
            nome = st.text_input("Nome (Ex: Aluguel, Netflix, Academia)")
            c1, c2 = st.columns(2)
            valor = c1.number_input("Valor Estimado (R$)", min_value=0.0)
            dia = c2.number_input("Dia de Vencimento", 1, 31, 10)
            
            tipo = st.selectbox("Tipo", ["Despesa", "Receita"], key="tipo_new")
            opcoes_cat = LISTA_CATEGORIAS_DESPESA if tipo == "Despesa" else LISTA_CATEGORIAS_RECEITA
            cat = st.selectbox("Categoria", options=opcoes_cat, key="cat_new")
            
            if st.form_submit_button("Salvar Recorrência"):
                salvar_recorrencia(user_id, nome, valor, cat, dia, tipo)
                st.success("Salvo!")
                st.rerun()

        # Área de Edição
        if not df_fixas.empty:
            st.divider()
            st.subheader("Gerenciar Cadastrados")
            
            # Selectbox para editar
            opcoes_editar = df_fixas.apply(lambda x: f"{x['id']} - {x['nome']} (Dia {x['dia_vencimento']})", axis=1)
            escolha = st.selectbox("Selecione para editar ou excluir:", options=opcoes_editar)
            
            if escolha:
                id_selecionado = int(escolha.split(" -")[0])
                dados_atuais = df_fixas[df_fixas['id'] == id_selecionado].iloc[0]
                
                with st.form("form_edit_fixa"):
                    e_nome = st.text_input("Nome", value=dados_atuais['nome'])
                    ec1, ec2 = st.columns(2)
                    e_valor = ec1.number_input("Valor", value=float(dados_atuais['valor']))
                    e_dia = ec2.number_input("Dia", 1, 31, int(dados_atuais['dia_vencimento']))
                    
                    e_tipo = st.selectbox("Tipo", ["Despesa", "Receita"], index=0 if dados_atuais['tipo']=="Despesa" else 1)
                    e_cat_list = LISTA_CATEGORIAS_DESPESA if e_tipo == "Despesa" else LISTA_CATEGORIAS_RECEITA
                    
                    try: idx_c = e_cat_list.index(dados_atuais['categoria'])
                    except: idx_c = 0
                    e_cat = st.selectbox("Categoria", e_cat_list, index=idx_c)
                    
                    if st.form_submit_button("Atualizar Dados"):
                        atualizar_recorrencia(user_id, id_selecionado, e_nome, e_valor, e_cat, e_dia, e_tipo)
                        st.success("Atualizado!")
                        st.rerun()
                
                if st.button("🗑️ Excluir Definitivamente"):
                    excluir_recorrencia(user_id, id_selecionado)
                    st.rerun()