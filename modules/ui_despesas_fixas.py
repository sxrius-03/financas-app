import streamlit as st
import pandas as pd
from datetime import date
from modules.database import (
    salvar_recorrencia, carregar_recorrencias, excluir_recorrencia, 
    salvar_lancamento, atualizar_recorrencia, carregar_dados
)
from modules.constants import LISTA_CATEGORIAS_DESPESA

# ==============================================================================
# 🎛️ PAINEL DE CONTROLE (CONFIGURAÇÕES DE UI & DESIGN)
# ==============================================================================

CONFIG_UI = {
    "GERAL": {
        "titulo": "📉 Contas Fixas & Assinaturas",
        "caption": "Gerencie suas obrigações mensais recorrentes (Aluguel, Internet, Streaming).",
        "aba_controle": "✅ Controle do Mês",
        "aba_gerenciar": "⚙️ Gerenciar (Criar/Editar)"
    },
    "METRICAS": {
        "lbl_total": "Total Mensal",
        "lbl_pago": "Já Pago",
        "lbl_restante": "Falta Pagar"
    },
    "FORMULARIO": {
        "header_novo": "🆕 Nova Despesa Fixa",
        "header_edit": "✏️ Editando Despesa",
        "lbl_nome": "Nome da Despesa",
        "lbl_valor": "Valor Estimado (R$)",
        "lbl_dia": "Dia do Vencimento",
        "lbl_cat": "Categoria",
        "btn_salvar": "💾 Salvar Despesa",
        "btn_atualizar": "🔄 Atualizar Dados",
        "btn_excluir": "🗑️ Excluir Recorrência"
    }
}

# --- CORES (SISTEMA HSL) ---
CORES = {
    "despesa": "hsl(0, 87%, 50%)",          # Vermelho Principal
    "despesa_suave": "hsla(0, 87%, 50%, 0.1)", 
    "pago": "hsl(154, 65%, 55%)",           # Verde (Status Pago)
    "atrasado": "hsl(30, 100%, 50%)",       # Laranja (Status Atrasado)
    "pendente": "hsl(0, 0%, 50%)",          # Cinza
    "texto_destaque": "hsl(0, 0%, 100%)",
    "fundo_card": "hsl(220, 13%, 18%)"
}

# ==============================================================================
# 🛠️ FUNÇÕES LÓGICAS
# ==============================================================================

def show_despesas_fixas():
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
    df_fixas = df_all[df_all['tipo'] == 'Despesa'].copy() if not df_all.empty else pd.DataFrame()

    # ===================================================
    # ABA 1: CONTROLE (MÊS ATUAL)
    # ===================================================
    with tab_controle:
        if df_fixas.empty:
            st.info("Nenhuma despesa fixa cadastrada. Vá na aba 'Gerenciar' para adicionar.")
        else:
            mes_atual = date.today().month
            ano_atual = date.today().year
            dia_hoje = date.today().day
            
            st.subheader(f"Vencimentos: {mes_atual}/{ano_atual}")
            
            # Verifica pagamentos feitos no mês
            df_lancamentos = carregar_dados(user_id)
            itens_pagos = []
            if not df_lancamentos.empty:
                df_lancamentos['data'] = pd.to_datetime(df_lancamentos['data'])
                mask = (df_lancamentos['data'].dt.month == mes_atual) & \
                       (df_lancamentos['data'].dt.year == ano_atual) & \
                       (df_lancamentos['tipo'] == "Despesa")
                itens_pagos = df_lancamentos[mask]['descricao'].tolist()

            # Prepara dados visuais
            status_list = []
            for _, row in df_fixas.iterrows():
                # Lógica de "Está pago?": Verifica se o nome da fixa está contido na descrição do lançamento
                foi_pago = any(row['nome'] in item for item in itens_pagos)
                
                status_cod = "pendente"
                if foi_pago:
                    status_cod = "pago"
                elif dia_hoje > int(row['dia_vencimento']):
                    status_cod = "atrasado"
                
                status_list.append({
                    "id": row['id'], 
                    "Dia": row['dia_vencimento'],
                    "Nome": row['nome'], 
                    "Valor": row['valor'],
                    "Categoria": row['categoria'], # Necessário p/ o pagamento
                    "StatusCod": status_cod
                })
            
            df_status = pd.DataFrame(status_list).sort_values(by="Dia")
            
            # Cards de Métricas
            total_mes = df_status['Valor'].sum()
            total_pago = df_status[df_status['StatusCod'] == "pago"]['Valor'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric(CONFIG_UI["METRICAS"]["lbl_total"], f"R$ {total_mes:,.2f}")
            c2.metric(CONFIG_UI["METRICAS"]["lbl_pago"], f"R$ {total_pago:,.2f}")
            c3.metric(CONFIG_UI["METRICAS"]["lbl_restante"], f"R$ {total_mes - total_pago:,.2f}")
            
            st.divider()
            
            # Lista Visual de Contas
            for idx, row in df_status.iterrows():
                with st.container():
                    # Define ícone e cor
                    if row['StatusCod'] == "pago":
                        icon, cor_txt = "✅", CORES['pago']
                        lbl_btn = "Pago"
                    elif row['StatusCod'] == "atrasado":
                        icon, cor_txt = "🔥", CORES['atrasado']
                        lbl_btn = "Pagar Agora"
                    else:
                        icon, cor_txt = "📅", CORES['texto_destaque']
                        lbl_btn = "Registrar Pagamento"
                    
                    # Layout da Linha
                    c_icon, c_dia, c_info, c_val, c_btn = st.columns([0.5, 0.8, 3, 1.5, 2])
                    
                    c_icon.markdown(f"<h3 style='color:{cor_txt}'>{icon}</h3>", unsafe_allow_html=True)
                    c_dia.write(f"**Dia {row['Dia']}**")
                    c_info.markdown(f"**{row['Nome']}**<br><span style='color:grey;font-size:0.8em'>{row['Categoria']}</span>", unsafe_allow_html=True)
                    c_val.write(f"R$ {row['Valor']:,.2f}")
                    
                    if row['StatusCod'] != "pago":
                        if c_btn.button(lbl_btn, key=f"pay_{row['id']}"):
                            # Tenta criar data válida (cuidado com fev 30)
                            try: d_venc = date(ano_atual, mes_atual, int(row['Dia']))
                            except: d_venc = date(ano_atual, mes_atual, 28)
                            
                            dados = {
                                "data": d_venc, 
                                "tipo": "Despesa", 
                                "categoria": row['Categoria'], 
                                "subcategoria": "Conta Fixa", 
                                "descricao": f"{row['Nome']} (Ref. {mes_atual}/{ano_atual})",
                                "valor": row['Valor'], 
                                "conta": "Conta Corrente", 
                                "forma_pagamento": "Boleto/Débito",
                                "status": "Pago/Recebido"
                            }
                            salvar_lancamento(user_id, dados)
                            st.toast(f"Pagamento de {row['Nome']} registrado!", icon="💸")
                            st.rerun()
                    else:
                        c_btn.caption("✅ Quitado")
                    st.markdown("---")

    # ===================================================
    # ABA 2: GERENCIAR (NOVO + EDITAR)
    # ===================================================
    with tab_gerenciar:
        # Seletor de Modo
        opcoes_edit = ["✨ Criar Nova Conta"]
        
        mapa_objs = {}
        if not df_fixas.empty:
            for _, row in df_fixas.iterrows():
                lbl = f"{row['nome']} (Dia {row['dia_vencimento']} - R$ {row['valor']:.2f})"
                opcoes_edit.append(lbl)
                mapa_objs[lbl] = row
        
        selecao = st.selectbox("Selecione uma ação:", options=opcoes_edit)
        
        modo_edicao = selecao != "✨ Criar Nova Conta"
        dados_form = mapa_objs.get(selecao) if modo_edicao else None

        st.divider()

        # Formulário Unificado
        with st.form("form_gerenciar_despesa"):
            st.subheader(CONFIG_UI["FORMULARIO"]["header_edit"] if modo_edicao else CONFIG_UI["FORMULARIO"]["header_novo"])
            
            nome_padrao = dados_form['nome'] if modo_edicao else ""
            val_padrao = float(dados_form['valor']) if modo_edicao else 0.0
            dia_padrao = int(dados_form['dia_vencimento']) if modo_edicao else 10
            
            # Tenta achar index da categoria
            idx_cat = 0
            if modo_edicao and dados_form['categoria'] in LISTA_CATEGORIAS_DESPESA:
                idx_cat = LISTA_CATEGORIAS_DESPESA.index(dados_form['categoria'])

            nome = st.text_input(CONFIG_UI["FORMULARIO"]["lbl_nome"], value=nome_padrao, placeholder="Ex: Netflix, Aluguel")
            
            c1, c2 = st.columns(2)
            valor = c1.number_input(CONFIG_UI["FORMULARIO"]["lbl_valor"], min_value=0.0, value=val_padrao, step=10.0)
            dia = c2.number_input(CONFIG_UI["FORMULARIO"]["lbl_dia"], min_value=1, max_value=31, value=dia_padrao)
            
            cat = st.selectbox(CONFIG_UI["FORMULARIO"]["lbl_cat"], LISTA_CATEGORIAS_DESPESA, index=idx_cat)
            
            # Botões de Ação
            col_save, col_del = st.columns([2, 1])
            
            if modo_edicao:
                submitted = col_save.form_submit_button(CONFIG_UI["FORMULARIO"]["btn_atualizar"], type="primary")
                delete = col_del.form_submit_button(CONFIG_UI["FORMULARIO"]["btn_excluir"], type="secondary")
                
                if delete:
                    excluir_recorrencia(user_id, int(dados_form['id']))
                    st.success("Conta recorrente removida!")
                    st.rerun()
                
                if submitted:
                    atualizar_recorrencia(user_id, int(dados_form['id']), nome, valor, cat, dia, "Despesa")
                    st.success("Dados atualizados com sucesso!")
                    st.rerun()
            else:
                # Modo Criação
                submitted = st.form_submit_button(CONFIG_UI["FORMULARIO"]["btn_salvar"], type="primary")
                if submitted:
                    if nome and valor > 0:
                        salvar_recorrencia(user_id, nome, valor, cat, dia, "Despesa")
                        st.success("Nova conta fixa cadastrada!")
                        st.rerun()
                    else:
                        st.warning("Preencha o nome e um valor maior que zero.")