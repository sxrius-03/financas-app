import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from modules.database import (
    salvar_cartao, carregar_cartoes, excluir_cartao, 
    salvar_compra_credito, carregar_fatura, atualizar_item_fatura,
    registrar_pagamento_fatura, obter_status_fatura, salvar_lancamento,
    excluir_pagamento_fatura, listar_meses_fatura, atualizar_cartao,
    buscar_historico_compras, excluir_compra_agrupada
)
from modules.constants import LISTA_CATEGORIAS_DESPESA

# ==============================================================================
# 🎛️ PAINEL DE CONTROLE (CONFIGURAÇÕES DE UI & DESIGN)
# ==============================================================================

CONFIG_UI = {
    "GERAL": {
        "titulo": "💳 Gestão de Cartões de Crédito",
        "tabs": ["📄 Ver Faturas", "🛍️ Nova Compra", "📜 Histórico/Editar", "⚙️ Gerenciar Cartões"]
    },
    "FATURAS": {
        "lbl_selecao": "Selecione o Cartão",
        "lbl_mes": "Mês da Fatura",
        "msg_vazia": "Fatura vazia ou inexistente para este mês.",
        "msg_sem_meses": "Nenhuma fatura encontrada para este cartão.",
        "kpi_total": "Total da Fatura"
    },
    "TABELA_FATURA": {
        "col_data": "📅 Data Compra",
        "col_desc": "📝 Descrição",
        "col_parc": "🔢 Parc.",
        "col_qtd": "Total Parc.",
        "col_valor": "💲 Valor Parcela (R$)"
    },
    "HISTORICO": {
        "header": "📜 Histórico de Compras (Edição Completa)",
        "caption": "Aqui você vê as compras originais e pode editar ou excluir a compra inteira (todas as parcelas de uma vez).",
        "col_data": "Data",
        "col_desc": "Descrição",
        "col_cartao": "Cartão",
        "col_total": "Valor Total",
        "col_parcelas": "Parcelas"
    },
    "GERENCIAR": {
        "header_novo": "🆕 Cadastrar Novo Cartão",
        "header_edit": "✏️ Editar Cartão Existente",
        "lbl_nome": "Apelido do Cartão",
        "lbl_fech": "Dia Fechamento",
        "lbl_venc": "Dia Vencimento",
        "btn_save": "💾 Salvar Cartão",
        "btn_update": "🔄 Atualizar Dados",
        "btn_del": "🗑️ Excluir Cartão"
    }
}

# --- CORES (SISTEMA HSL) ---
CORES = {
    "status_pago": "hsl(140, 100%, 40%)",   # Verde
    "status_aberto": "hsl(200, 100%, 50%)", # Azul
    "status_fechado": "hsl(30, 100%, 50%)", # Laranja (Pendente)
    "status_atrasado": "hsl(0, 100%, 60%)", # Vermelho
    "card_bg": "hsl(220, 13%, 18%)",
    "texto_destaque": "hsl(0, 0%, 100%)"
}

# ==============================================================================
# 🛠️ LÓGICA DE CARTÕES
# ==============================================================================

def show_cartoes():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']
    
    st.header(CONFIG_UI["GERAL"]["titulo"])
    
    tab_fatura, tab_compra, tab_historico, tab_gerenciar = st.tabs(CONFIG_UI["GERAL"]["tabs"])
    
    df_cartoes = carregar_cartoes(user_id)

    # ===================================================
    # ABA 1: VER FATURAS
    # ===================================================
    with tab_fatura:
        if df_cartoes.empty:
            st.warning("Cadastre um cartão primeiro na aba 'Gerenciar Cartões'.")
        else:
            c1, c2 = st.columns(2)
            cartao_selecionado = c1.selectbox(CONFIG_UI["FATURAS"]["lbl_selecao"], df_cartoes['nome_cartao'].tolist())
            
            # Dados do cartão selecionado
            info_cartao = df_cartoes[df_cartoes['nome_cartao'] == cartao_selecionado].iloc[0]
            id_cartao = int(info_cartao['id'])
            dia_venc = int(info_cartao['dia_vencimento'])
            dia_fech = int(info_cartao['dia_fechamento'])
            
            # --- FILTRO DINÂMICO DE MESES ---
            meses_disponiveis = listar_meses_fatura(user_id, id_cartao)
            
            if not meses_disponiveis:
                st.info(CONFIG_UI["FATURAS"]["msg_sem_meses"])
            else:
                mes_atual = date.today().replace(day=1)
                idx_padrao = 0
                for i, m in enumerate(meses_disponiveis):
                    if m.year == mes_atual.year and m.month == mes_atual.month:
                        idx_padrao = i
                        break
                
                mes_escolhido = c2.selectbox(
                    CONFIG_UI["FATURAS"]["lbl_mes"], 
                    meses_disponiveis, 
                    format_func=lambda x: x.strftime("%B/%Y"),
                    index=idx_padrao
                )
                
                # Carregar Itens e Status
                df_fatura = carregar_fatura(user_id, id_cartao, mes_escolhido)
                status_info = obter_status_fatura(user_id, id_cartao, mes_escolhido)
                
                st.divider()
                
                if df_fatura.empty:
                    st.info(CONFIG_UI["FATURAS"]["msg_vazia"])
                else:
                    total_fatura = float(df_fatura['valor_parcela'].sum())
                    
                    # --- LÓGICA DE STATUS REFINADA ---
                    # 1. Calcula Data Real de Vencimento
                    try: 
                        dt_vencimento = date(mes_escolhido.year, mes_escolhido.month, dia_venc)
                    except ValueError: 
                        # Caso dia 31 em mês de 30 dias, joga para o último dia
                        dt_vencimento = date(mes_escolhido.year, mes_escolhido.month, 1) + relativedelta(months=1) - timedelta(days=1)

                    # 2. Calcula Data Real de Fechamento
                    # Lógica: Se fecha dia 8 e vence dia 15, fecha no mesmo mês.
                    # Se fecha dia 25 e vence dia 5, fecha no mês anterior.
                    if dia_fech < dia_venc:
                        dt_fechamento = date(mes_escolhido.year, mes_escolhido.month, dia_fech)
                    else:
                        dt_fechamento = dt_vencimento - relativedelta(months=1)
                        # Ajusta o dia
                        try:
                            dt_fechamento = dt_fechamento.replace(day=dia_fech)
                        except ValueError:
                            dt_fechamento = (dt_fechamento + relativedelta(months=1)).replace(day=1) - timedelta(days=1)

                    hoje = date.today()
                    esta_paga = status_info and status_info['status'] in ['Paga', 'Paga Externo']
                    
                    # Definição Visual do Status
                    if esta_paga:
                        txt_status = "✅ PAGA"
                        cor_status = CORES['status_pago']
                    elif hoje < dt_fechamento:
                        txt_status = "📅 ABERTA"
                        cor_status = CORES['status_aberto']
                    elif dt_fechamento <= hoje <= dt_vencimento:
                        txt_status = "⚠️ FECHADA"
                        cor_status = CORES['status_fechado'] # Laranja
                    else:
                        txt_status = "🔥 ATRASADA"
                        cor_status = CORES['status_atrasado']

                    # KPI
                    col_kpi1, col_kpi2, col_kpi3 = st.columns([2, 2, 3])
                    col_kpi1.metric(CONFIG_UI["FATURAS"]["kpi_total"], f"R$ {total_fatura:,.2f}")
                    col_kpi2.markdown(f"<h3 style='color:{cor_status}'>{txt_status}</h3>", unsafe_allow_html=True)
                    
                    # Ações de Pagamento
                    with col_kpi3:
                        if esta_paga:
                            if status_info['data']:
                                data_pg = datetime.strptime(str(status_info['data']), "%Y-%m-%d").strftime("%d/%m/%Y")
                                st.caption(f"Pago em: {data_pg} | Valor: R$ {status_info['valor']:,.2f}")
                            if st.button("🔓 Reabrir Fatura", type="secondary"):
                                excluir_pagamento_fatura(user_id, id_cartao, mes_escolhido)
                                st.rerun()
                        else:
                            # Se não estiver paga, mostra as opções
                            with st.expander("💸 Pagar Fatura"):
                                c_pay1, c_pay2 = st.columns(2)
                                
                                # Opção 1: Lançar no Caixa (Oficial)
                                if c_pay1.button("Lançar no Caixa", help="Cria uma despesa no extrato e baixa a fatura."):
                                    dados_lanc = {
                                        "data": date.today(), "tipo": "Despesa", "categoria": "Financeiro",
                                        "subcategoria": "Pagamento de Fatura",
                                        "descricao": f"Fatura {cartao_selecionado} - {mes_escolhido.strftime('%m/%Y')}",
                                        "valor": total_fatura, "conta": "Conta Corrente",
                                        "forma_pagamento": "Boleto", "status": "Pago/Recebido"
                                    }
                                    salvar_lancamento(user_id, dados_lanc)
                                    registrar_pagamento_fatura(user_id, id_cartao, mes_escolhido, "Paga", total_fatura, date.today())
                                    st.success("Pago e Lançado!")
                                    st.rerun()
                                
                                # Opção 2: Baixar sem lançar (Externo)
                                if c_pay2.button("Já Paguei por Fora", help="Apenas marca como paga, sem mexer no saldo."):
                                    registrar_pagamento_fatura(user_id, id_cartao, mes_escolhido, "Paga Externo", total_fatura, date.today())
                                    st.success("Fatura baixada manualmente!")
                                    st.rerun()

                    # Tabela
                    st.dataframe(
                        df_fatura[['data_compra', 'descricao', 'parcela_numero', 'qtd_parcelas', 'valor_parcela']], 
                        use_container_width=True,
                        column_config={
                            "data_compra": st.column_config.DateColumn(CONFIG_UI["TABELA_FATURA"]["col_data"], format="DD/MM/YYYY"),
                            "descricao": CONFIG_UI["TABELA_FATURA"]["col_desc"],
                            "parcela_numero": CONFIG_UI["TABELA_FATURA"]["col_parc"],
                            "qtd_parcelas": CONFIG_UI["TABELA_FATURA"]["col_qtd"],
                            "valor_parcela": st.column_config.NumberColumn(CONFIG_UI["TABELA_FATURA"]["col_valor"], format="R$ %.2f")
                        },
                        hide_index=True
                    )
                    
                    # Edição Rápida
                    with st.expander("✏️ Corrigir Item Específico"):
                        opcoes_item = df_fatura.apply(lambda r: f"Item {r['id']} | {r['descricao']} - R$ {r['valor_parcela']:.2f}", axis=1)
                        item_sel = st.selectbox("Selecione:", ["Selecione..."] + list(opcoes_item))
                        if item_sel != "Selecione...":
                            id_item = int(item_sel.split(" |")[0].replace("Item ", ""))
                            dados_item = df_fatura[df_fatura['id'] == id_item].iloc[0]
                            with st.form(f"edit_item_{id_item}"):
                                n_desc = st.text_input("Descrição", value=dados_item['descricao'])
                                n_val = st.number_input("Valor da Parcela", value=float(dados_item['valor_parcela']))
                                if st.form_submit_button("Salvar Correção"):
                                    atualizar_item_fatura(user_id, id_item, n_desc, n_val, pd.to_datetime(dados_item['data_compra']))
                                    st.success("Corrigido!")
                                    st.rerun()

    # ===================================================
    # ABA 2: NOVA COMPRA
    # ===================================================
    with tab_compra:
        st.subheader("🛍️ Registrar Gasto")
        if not df_cartoes.empty:
            with st.form("form_compra_credito"):
                c1, c2 = st.columns(2)
                cartao_nome = c1.selectbox("Cartão Usado", df_cartoes['nome_cartao'].tolist())
                data_compra = c2.date_input("Data da Compra", date.today())
                desc = st.text_input("Descrição (Ex: Notebook Dell)")
                cat = st.selectbox("Categoria", options=LISTA_CATEGORIAS_DESPESA)
                c3, c4 = st.columns(2)
                valor_total = c3.number_input("Valor TOTAL da Compra", min_value=0.01)
                parcelas = c4.number_input("Qtd. Parcelas", min_value=1, step=1, value=1)
                
                if st.form_submit_button("Lançar Compra"):
                    info_cartao = df_cartoes[df_cartoes['nome_cartao'] == cartao_nome].iloc[0]
                    salvar_compra_credito(user_id, int(info_cartao['id']), data_compra, desc, cat, valor_total, int(parcelas), int(info_cartao['dia_fechamento']))
                    st.toast("Compra lançada com sucesso!", icon="✅")

    # ===================================================
    # ABA 3: HISTÓRICO / EDITAR COMPRAS
    # ===================================================
    with tab_historico:
        st.subheader(CONFIG_UI["HISTORICO"]["header"])
        st.caption(CONFIG_UI["HISTORICO"]["caption"])
        
        if not df_cartoes.empty:
            filtro_card = st.selectbox("Filtrar por Cartão:", ["Todos"] + df_cartoes['nome_cartao'].tolist())
            id_card_filter = None
            if filtro_card != "Todos":
                id_card_filter = int(df_cartoes[df_cartoes['nome_cartao'] == filtro_card]['id'].values[0])
            
            df_hist = buscar_historico_compras(user_id, id_card_filter)
            
            if df_hist.empty:
                st.info("Nenhuma compra encontrada.")
            else:
                opcoes_compra = df_hist.apply(
                    lambda r: f"{r['data_compra']} | {r['descricao']} | R$ {r['valor_total']:.2f} ({r['qtd_parcelas']}x) - {r['nome_cartao']}", 
                    axis=1
                )
                compra_sel = st.selectbox("Selecione uma compra para editar/excluir:", ["Selecione..."] + list(opcoes_compra))
                
                if compra_sel != "Selecione...":
                    idx_sel = list(opcoes_compra).index(compra_sel)
                    dados_compra = df_hist.iloc[idx_sel]
                    
                    st.divider()
                    st.write(f"**Editando:** {dados_compra['descricao']}")
                    
                    with st.form("form_edit_compra_full"):
                        ec1, ec2 = st.columns(2)
                        novo_desc = ec1.text_input("Descrição", value=dados_compra['descricao'])
                        nova_data = ec2.date_input("Data Compra", value=dados_compra['data_compra'])
                        
                        ec3, ec4 = st.columns(2)
                        novo_total = ec3.number_input("Valor Total (Recalcula parcelas)", value=float(dados_compra['valor_total']), min_value=0.01)
                        novas_parc = ec4.number_input("Qtd Parcelas", value=int(dados_compra['qtd_parcelas']), min_value=1)
                        
                        col_save, col_del = st.columns([2, 1])
                        
                        atualizar = col_save.form_submit_button("💾 Salvar Alterações (Recriar)", type="primary")
                        excluir = col_del.form_submit_button("🗑️ Excluir Compra Inteira", type="secondary")
                        
                        if excluir:
                            excluir_compra_agrupada(user_id, int(dados_compra['cartao_id']), dados_compra['data_compra'], dados_compra['descricao'], int(dados_compra['qtd_parcelas']))
                            st.success("Compra excluída!")
                            st.rerun()
                        
                        if atualizar:
                            excluir_compra_agrupada(user_id, int(dados_compra['cartao_id']), dados_compra['data_compra'], dados_compra['descricao'], int(dados_compra['qtd_parcelas']))
                            info_cartao = df_cartoes[df_cartoes['id'] == dados_compra['cartao_id']].iloc[0]
                            salvar_compra_credito(
                                user_id, int(dados_compra['cartao_id']), 
                                nova_data, novo_desc, dados_compra['categoria'], 
                                novo_total, int(novas_parc), int(info_cartao['dia_fechamento'])
                            )
                            st.success("Compra atualizada com sucesso!")
                            st.rerun()

    # ===================================================
    # ABA 4: GERENCIAR CARTÕES
    # ===================================================
    with tab_gerenciar:
        opcoes_ger = ["✨ Cadastrar Novo"]
        mapa_cartoes = {}
        if not df_cartoes.empty:
            for _, row in df_cartoes.iterrows():
                lbl = row['nome_cartao']
                opcoes_ger.append(lbl)
                mapa_cartoes[lbl] = row
        
        sel_ger = st.selectbox("Ação:", opcoes_ger)
        modo_edit_card = sel_ger != "✨ Cadastrar Novo"
        dados_card = mapa_cartoes.get(sel_ger) if modo_edit_card else None
        
        st.divider()
        
        with st.form("form_cartao"):
            st.subheader(CONFIG_UI["GERENCIAR"]["header_edit"] if modo_edit_card else CONFIG_UI["GERENCIAR"]["header_novo"])
            
            nome_c = st.text_input(CONFIG_UI["GERENCIAR"]["lbl_nome"], value=dados_card['nome_cartao'] if modo_edit_card else "")
            c1, c2 = st.columns(2)
            fech_c = c1.number_input(CONFIG_UI["GERENCIAR"]["lbl_fech"], 1, 31, int(dados_card['dia_fechamento']) if modo_edit_card else 1)
            venc_c = c2.number_input(CONFIG_UI["GERENCIAR"]["lbl_venc"], 1, 31, int(dados_card['dia_vencimento']) if modo_edit_card else 10)
            
            col_s, col_d = st.columns([2, 1])
            
            if modo_edit_card:
                if col_s.form_submit_button(CONFIG_UI["GERENCIAR"]["btn_update"], type="primary"):
                    atualizar_cartao(user_id, int(dados_card['id']), nome_c, fech_c, venc_c)
                    st.success("Cartão atualizado!")
                    st.rerun()
                if col_d.form_submit_button(CONFIG_UI["GERENCIAR"]["btn_del"], type="secondary"):
                    excluir_cartao(user_id, int(dados_card['id']))
                    st.success("Cartão excluído!")
                    st.rerun()
            else:
                if st.form_submit_button(CONFIG_UI["GERENCIAR"]["btn_save"], type="primary"):
                    if nome_c:
                        salvar_cartao(user_id, nome_c, fech_c, venc_c)
                        st.success("Cartão criado!")
                        st.rerun()