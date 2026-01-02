import streamlit as st
import pandas as pd
from datetime import date
from modules.database import (
    salvar_recorrencia, carregar_recorrencias, excluir_recorrencia, 
    salvar_lancamento, atualizar_recorrencia, carregar_dados
)
from modules.constants import LISTA_CATEGORIAS_RECEITA

# ==============================================================================
# 🎛️ PAINEL DE CONTROLE (CONFIGURAÇÕES DE UI & DESIGN)
# ==============================================================================

CONFIG_UI = {
    "GERAL": {
        "titulo": "💰 Rendas Fixas & Salários",
        "caption": "Gerencie suas entradas recorrentes (Salário, Aluguéis, Pró-labore).",
        "aba_controle": "✅ Recebimentos do Mês",
        "aba_gerenciar": "⚙️ Gerenciar (Criar/Editar)"
    },
    "METRICAS": {
        "lbl_total": "Renda Prevista",
        "lbl_recebido": "Já Recebido",
        "lbl_restante": "A Receber"
    },
    "FORMULARIO": {
        "header_novo": "🆕 Nova Renda Recorrente",
        "header_edit": "✏️ Editando Renda",
        "lbl_nome": "Nome (Ex: Salário)",
        "lbl_valor": "Valor Líquido (R$)",
        "lbl_dia": "Dia do Depósito",
        "lbl_cat": "Categoria",
        "btn_salvar": "💾 Salvar Renda",
        "btn_atualizar": "🔄 Atualizar Dados",
        "btn_excluir": "🗑️ Remover Renda"
    }
}

# --- CORES (SISTEMA HSL) ---
CORES = {
    "receita": "hsl(154, 65%, 55%)",    # Verde Principal
    "recebido": "hsl(154, 65%, 55%)",   # Verde (Status Recebido)
    "pendente": "hsl(0, 0%, 50%)",      # Cinza
    "texto_destaque": "hsl(0, 0%, 100%)"
}

# ==============================================================================
# 🛠️ FUNÇÕES LÓGICAS
# ==============================================================================

def show_receitas_fixas():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']
    
    st.header(CONFIG_UI["GERAL"]["titulo"])
    st.caption(CONFIG_UI["GERAL"]["caption"])
    
    tab_controle, tab_gerenciar = st.tabs([
        CONFIG_UI["GERAL"]["aba_controle"], 
        CONFIG_UI["GERAL"]["aba_gerenciar"]
    ])
    
    # Carrega recorrencias e filtra
    df_all = carregar_recorrencias(user_id)
    df_fixas = df_all[df_all['tipo'] == 'Receita'].copy() if not df_all.empty else pd.DataFrame()

    # ===================================================
    # ABA 1: CONTROLE (MÊS ATUAL)
    # ===================================================
    with tab_controle:
        if df_fixas.empty:
            st.info("Nenhuma renda fixa cadastrada. Vá na aba 'Gerenciar' para adicionar.")
        else:
            mes_atual = date.today().month
            ano_atual = date.today().year
            
            st.subheader(f"Competência: {mes_atual}/{ano_atual}")
            
            # Verifica recebimentos feitos no mês
            df_lancamentos = carregar_dados(user_id)
            itens_recebidos = []
            if not df_lancamentos.empty:
                df_lancamentos['data'] = pd.to_datetime(df_lancamentos['data'])
                mask = (df_lancamentos['data'].dt.month == mes_atual) & \
                       (df_lancamentos['data'].dt.year == ano_atual) & \
                       (df_lancamentos['tipo'] == "Receita")
                itens_recebidos = df_lancamentos[mask]['descricao'].tolist()

            # Prepara dados visuais
            status_list = []
            for _, row in df_fixas.iterrows():
                ja_recebeu = any(row['nome'] in item for item in itens_recebidos)
                
                status_list.append({
                    "id": row['id'], 
                    "Dia": row['dia_vencimento'],
                    "Nome": row['nome'], 
                    "Valor": row['valor'],
                    "Categoria": row['categoria'],
                    "Recebido": ja_recebeu
                })
            
            df_status = pd.DataFrame(status_list).sort_values(by="Dia")
            
            # Métricas
            total_previsto = df_status['Valor'].sum()
            total_recebido = df_status[df_status['Recebido'] == True]['Valor'].sum()
            
            c1, c2 = st.columns(2)
            c1.metric(CONFIG_UI["METRICAS"]["lbl_total"], f"R$ {total_previsto:,.2f}")
            c2.metric(CONFIG_UI["METRICAS"]["lbl_recebido"], f"R$ {total_recebido:,.2f}", delta=f"Restam R$ {total_previsto-total_recebido:,.2f}")
            
            st.divider()
            
            # Lista Visual
            for idx, row in df_status.iterrows():
                with st.container():
                    # Visual
                    if row['Recebido']:
                        icon, cor_txt = "💰", CORES['recebido']
                    else:
                        icon, cor_txt = "⚪", CORES['pendente']
                    
                    c_icon, c_dia, c_info, c_val, c_btn = st.columns([0.5, 0.8, 3, 1.5, 2])
                    
                    c_icon.markdown(f"<h3 style='color:{cor_txt}'>{icon}</h3>", unsafe_allow_html=True)
                    c_dia.write(f"**Dia {row['Dia']}**")
                    c_info.markdown(f"**{row['Nome']}**<br><span style='color:grey;font-size:0.8em'>{row['Categoria']}</span>", unsafe_allow_html=True)
                    c_val.write(f"R$ {row['Valor']:,.2f}")
                    
                    if not row['Recebido']:
                        if c_btn.button("Confirmar Entrada", key=f"btn_rec_{row['id']}"):
                            try: d_venc = date(ano_atual, mes_atual, int(row['Dia']))
                            except: d_venc = date(ano_atual, mes_atual, 28)
                            
                            dados = {
                                "data": d_venc, 
                                "tipo": "Receita", 
                                "categoria": row['Categoria'],
                                "subcategoria": "Salário/Fixa", 
                                "descricao": f"{row['Nome']} (Ref. {mes_atual}/{ano_atual})",
                                "valor": row['Valor'], 
                                "conta": "Conta Principal", 
                                "forma_pagamento": "Depósito/PIX",
                                "status": "Pago/Recebido"
                            }
                            salvar_lancamento(user_id, dados)
                            st.toast("Entrada registrada!", icon="💰")
                            st.rerun()
                    else:
                        c_btn.caption("✅ Registrado")
                    st.markdown("---")

    # ===================================================
    # ABA 2: GERENCIAR (NOVO + EDITAR)
    # ===================================================
    with tab_gerenciar:
        # Seletor de Modo
        opcoes_edit = ["✨ Nova Renda Recorrente"]
        
        mapa_objs = {}
        if not df_fixas.empty:
            for _, row in df_fixas.iterrows():
                lbl = f"{row['nome']} (Dia {row['dia_vencimento']} - R$ {row['valor']:.2f})"
                opcoes_edit.append(lbl)
                mapa_objs[lbl] = row
        
        selecao = st.selectbox("Selecione uma ação:", options=opcoes_edit)
        
        modo_edicao = selecao != "✨ Nova Renda Recorrente"
        dados_form = mapa_objs.get(selecao) if modo_edicao else None

        st.divider()

        # Formulário Unificado
        with st.form("form_gerenciar_receita"):
            st.subheader(CONFIG_UI["FORMULARIO"]["header_edit"] if modo_edicao else CONFIG_UI["FORMULARIO"]["header_novo"])
            
            nome_padrao = dados_form['nome'] if modo_edicao else ""
            val_padrao = float(dados_form['valor']) if modo_edicao else 0.0
            dia_padrao = int(dados_form['dia_vencimento']) if modo_edicao else 5
            
            idx_cat = 0
            if modo_edicao and dados_form['categoria'] in LISTA_CATEGORIAS_RECEITA:
                idx_cat = LISTA_CATEGORIAS_RECEITA.index(dados_form['categoria'])

            nome = st.text_input(CONFIG_UI["FORMULARIO"]["lbl_nome"], value=nome_padrao, placeholder="Ex: Salário, Aluguel Apt")
            
            c1, c2 = st.columns(2)
            valor = c1.number_input(CONFIG_UI["FORMULARIO"]["lbl_valor"], min_value=0.0, value=val_padrao, step=50.0)
            dia = c2.number_input(CONFIG_UI["FORMULARIO"]["lbl_dia"], min_value=1, max_value=31, value=dia_padrao)
            
            cat = st.selectbox(CONFIG_UI["FORMULARIO"]["lbl_cat"], LISTA_CATEGORIAS_RECEITA, index=idx_cat)
            
            # Botões
            col_save, col_del = st.columns([2, 1])
            
            if modo_edicao:
                submitted = col_save.form_submit_button(CONFIG_UI["FORMULARIO"]["btn_atualizar"], type="primary")
                delete = col_del.form_submit_button(CONFIG_UI["FORMULARIO"]["btn_excluir"], type="secondary")
                
                if delete:
                    excluir_recorrencia(user_id, int(dados_form['id']))
                    st.success("Renda removida!")
                    st.rerun()
                
                if submitted:
                    atualizar_recorrencia(user_id, int(dados_form['id']), nome, valor, cat, dia, "Receita")
                    st.success("Dados atualizados!")
                    st.rerun()
            else:
                submitted = st.form_submit_button(CONFIG_UI["FORMULARIO"]["btn_salvar"], type="primary")
                if submitted:
                    if nome and valor > 0:
                        salvar_recorrencia(user_id, nome, valor, cat, dia, "Receita")
                        st.success("Nova renda cadastrada!")
                        st.rerun()
                    else:
                        st.warning("Preencha nome e valor corretamente.")