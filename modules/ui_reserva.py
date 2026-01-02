import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from modules.database import (
    salvar_reserva_conta, carregar_reservas, salvar_transacao_reserva, 
    carregar_extrato_reserva, migrar_dados_antigos_para_reserva, 
    salvar_lancamento, excluir_reserva_conta, carregar_dados,
    excluir_transacao_reserva, atualizar_transacao_reserva
)

# ==============================================================================
# 🎛️ PAINEL DE CONTROLE (CONFIGURAÇÕES DE UI & DESIGN)
# ==============================================================================

CONFIG_UI = {
    "GERAL": {
        "titulo": "🛡️ Reserva & Segurança Financeira",
        "migracao_titulo": "🔧 Ferramentas de Sistema (Correção de Saldo)",
        "migracao_desc": "Esta ferramenta busca lançamentos antigos de Aporte (Despesa) e Resgate (Receita) e recalcula o saldo das reservas."
    },
    "TABELA_POTES": {
        # Configure aqui os nomes das colunas da tabela de reservas
        "col_nome": "Nome do Pote",
        "col_tipo": "Tipo",
        "col_saldo": "💰 Saldo Atual",
        "col_meta": "🎯 Meta",
        "col_rentab": "📈 Rendimento Base"
    },
    "TABELA_EXTRATO": {
        # Configure aqui os nomes das colunas do extrato
        "col_data": "📅 Data",
        "col_desc": "📝 Descrição",
        "col_valor": "💲 Valor (R$)",
        "col_tipo": "Tipo Movimento",
        "col_reserva": "Pote Relacionado"
    },
    "FORMULARIO": {
        "header_novo": "Nova Movimentação",
        "lbl_acao": "Ação",
        "lbl_reserva": "Selecione a Reserva",
        "lbl_data": "Data",
        "lbl_valor": "Valor (R$)",
        "lbl_desc": "Descrição",
        "btn_confirmar": "Confirmar Transação"
    }
}

# --- CORES (SISTEMA HSL) ---
CORES = {
    "positivo": "hsl(140, 100%, 30%)", # Verde Escuro
    "negativo": "hsl(0, 100%, 60%)",   # Vermelho
    "neutro": "hsl(220, 13%, 80%)",    # Cinza Claro
    "card_bg": "hsl(220, 13%, 18%)"
}

# ==============================================================================
# 🛠️ LÓGICA DE RESERVA
# ==============================================================================

def show_reserva():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']

    st.header(CONFIG_UI["GERAL"]["titulo"])
    
    # Ferramenta de Migração
    with st.expander(CONFIG_UI["GERAL"]["migracao_titulo"], expanded=False):
        st.write(CONFIG_UI["GERAL"]["migracao_desc"])
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
            
            # Cálculo Runway
            df_dash = carregar_dados(user_id)
            media_gastos = 0
            if not df_dash.empty:
                df_dash['data'] = pd.to_datetime(df_dash['data'])
                mask = (df_dash['data'] > pd.Timestamp.now() - pd.DateOffset(days=90)) & (df_dash['tipo'] == 'Despesa')
                total_90d = df_dash[mask]['valor'].sum()
                media_gastos = total_90d / 3 if total_90d > 0 else 0
            
            meses_sobrevivencia = saldo_total / media_gastos if media_gastos > 0 else 0
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Saldo Total", f"R$ {saldo_total:,.2f}")
            c2.metric("Meta Total", f"R$ {meta_total:,.2f}")
            c3.metric("Gasto Médio Mensal", f"R$ {media_gastos:,.2f}")
            c4.metric("Autonomia", f"{meses_sobrevivencia:.1f} Meses", delta="Runway")
            
            if meta_total > 0:
                st.progress(min(saldo_total / meta_total, 1.0), text=f"Progresso da Meta: {saldo_total/meta_total*100:.1f}%")
            
            st.divider()
            
            st.subheader("Meus Potes de Reserva")
            
            # Prepara Tabela com Nomes Customizados
            cols_to_show = ['nome', 'tipo_aplicacao', 'saldo_atual', 'meta_valor']
            if 'rentabilidade' in df_reservas.columns:
                cols_to_show.insert(2, 'rentabilidade')
            
            st.dataframe(
                df_reservas[cols_to_show],
                use_container_width=True,
                column_config={
                    "nome": st.column_config.TextColumn(CONFIG_UI["TABELA_POTES"]["col_nome"]),
                    "tipo_aplicacao": st.column_config.TextColumn(CONFIG_UI["TABELA_POTES"]["col_tipo"]),
                    "saldo_atual": st.column_config.NumberColumn(CONFIG_UI["TABELA_POTES"]["col_saldo"], format="R$ %.2f"),
                    "meta_valor": st.column_config.NumberColumn(CONFIG_UI["TABELA_POTES"]["col_meta"], format="R$ %.2f"),
                    "rentabilidade": st.column_config.TextColumn(CONFIG_UI["TABELA_POTES"]["col_rentab"])
                },
                hide_index=True
            )

    # --- ABA 2: OPERAÇÕES (NOVA E EDIÇÃO) ---
    with tab_operar:
        c_novo, c_edit = st.columns([1, 1], gap="large")
        
        # --- COLUNA ESQUERDA: NOVA MOVIMENTAÇÃO ---
        with c_novo:
            st.subheader(CONFIG_UI["FORMULARIO"]["header_novo"])
            if df_reservas.empty:
                st.warning("Sem reservas cadastradas.")
            else:
                tipo_mov = st.radio(CONFIG_UI["FORMULARIO"]["lbl_acao"], ["➕ Aportar (Guardar)", "➖ Resgatar (Usar)", "📈 Render Juros (Atualizar)"], horizontal=True)
                
                with st.form("form_mov"):
                    reserva_nome = st.selectbox(CONFIG_UI["FORMULARIO"]["lbl_reserva"], df_reservas['nome'].tolist())
                    res_id = int(df_reservas[df_reservas['nome'] == reserva_nome]['id'].values[0])
                    
                    c_data, c_val = st.columns(2)
                    d_mov = c_data.date_input(CONFIG_UI["FORMULARIO"]["lbl_data"], date.today())
                    val = c_val.number_input(CONFIG_UI["FORMULARIO"]["lbl_valor"], min_value=0.01)
                    desc = st.text_input(CONFIG_UI["FORMULARIO"]["lbl_desc"], value="Rendimento Mensal" if "Render" in tipo_mov else "")
                    
                    conta_cx = None
                    if "Aportar" in tipo_mov:
                        st.caption("ℹ️ Isso lançará automaticamente uma DESPESA no seu Caixa.")
                        conta_cx = st.selectbox("Saiu de qual conta?", ["Nubank", "Bradesco", "Itaú", "Santander", "Caixa", "Carteira", "Inter"])
                    elif "Resgatar" in tipo_mov:
                        st.caption("ℹ️ Isso lançará automaticamente uma RECEITA no seu Caixa.")
                        conta_cx = st.selectbox("Entrou em qual conta?", ["Nubank", "Bradesco", "Itaú", "Santander", "Caixa", "Carteira", "Inter"])
                    
                    if st.form_submit_button(CONFIG_UI["FORMULARIO"]["btn_confirmar"]):
                        tipo_db = 'Rendimento'
                        if "Aportar" in tipo_mov: tipo_db = 'Aporte'
                        elif "Resgatar" in tipo_mov: tipo_db = 'Resgate'
                        
                        # 1. Salva na Reserva
                        salvar_transacao_reserva(user_id, res_id, d_mov, tipo_db, val, desc)
                        
                        # 2. Espelha no Caixa
                        if tipo_db == 'Aporte':
                            l_dados = {"data": d_mov, "tipo": "Despesa", "categoria": "Financeiro", "subcategoria": "Transf. Reserva", "descricao": f"Aporte: {reserva_nome}", "valor": val, "conta": conta_cx, "forma_pagamento": "Transferência", "status": "Pago/Recebido"}
                            salvar_lancamento(user_id, l_dados)
                        elif tipo_db == 'Resgate':
                            l_dados = {"data": d_mov, "tipo": "Receita", "categoria": "Financeiro", "subcategoria": "Resgate Reserva", "descricao": f"Resgate: {reserva_nome}", "valor": val, "conta": conta_cx, "forma_pagamento": "Transferência", "status": "Pago/Recebido"}
                            salvar_lancamento(user_id, l_dados)
                            
                        st.success("Sucesso! Saldo atualizado.")
                        st.rerun()
        
        # --- COLUNA DIREITA: EDITAR MOVIMENTAÇÕES ---
        with c_edit:
            st.subheader("✏️ Editar Movimentações Antigas")
            st.caption("Alterar uma transação aqui recalcula o saldo da reserva automaticamente.")
            
            df_extrato = carregar_extrato_reserva(user_id)
            if df_extrato.empty:
                st.info("Nenhuma movimentação para editar.")
            else:
                # Cria lista de seleção
                opcoes_trans = df_extrato.apply(
                    lambda x: f"{x['data']} | {x['tipo']} | R$ {x['valor']:.2f} | {x['nome_reserva']}", axis=1
                )
                sel_trans = st.selectbox("Selecione para Editar/Excluir:", ["Selecione..."] + list(opcoes_trans))
                
                if sel_trans != "Selecione...":
                    idx = list(opcoes_trans).index(sel_trans)
                    # Ajuste de índice pois o primeiro item é "Selecione..."
                    item_edit = df_extrato.iloc[idx-1] 
                    
                    with st.form("form_edit_trans"):
                        st.write(f"Editando: **{item_edit['descricao']}**")
                        
                        nd = st.date_input("Nova Data", pd.to_datetime(item_edit['data']))
                        nv = st.number_input("Novo Valor", value=float(item_edit['valor']), min_value=0.01)
                        ndesc = st.text_input("Nova Descrição", value=item_edit['descricao'])
                        
                        c_s, c_d = st.columns([2, 1])
                        if c_s.form_submit_button("💾 Atualizar"):
                            atualizar_transacao_reserva(user_id, int(item_edit['id']), nd, ndesc, nv)
                            st.success("Atualizado!")
                            st.rerun()
                            
                        if c_d.form_submit_button("🗑️ Excluir"):
                            excluir_transacao_reserva(user_id, int(item_edit['id']))
                            st.success("Excluído!")
                            st.rerun()

        st.divider()
        st.subheader("Extrato Geral")
        
        # Tabela Extrato com Nomes Customizados
        st.dataframe(
            df_extrato[['data', 'nome_reserva', 'tipo', 'descricao', 'valor']], 
            use_container_width=True,
            column_config={
                "data": st.column_config.DateColumn(CONFIG_UI["TABELA_EXTRATO"]["col_data"], format="DD/MM/YYYY"),
                "nome_reserva": st.column_config.TextColumn(CONFIG_UI["TABELA_EXTRATO"]["col_reserva"]),
                "tipo": st.column_config.TextColumn(CONFIG_UI["TABELA_EXTRATO"]["col_tipo"]),
                "descricao": st.column_config.TextColumn(CONFIG_UI["TABELA_EXTRATO"]["col_desc"]),
                "valor": st.column_config.NumberColumn(CONFIG_UI["TABELA_EXTRATO"]["col_valor"], format="R$ %.2f")
            },
            hide_index=True
        )

    # --- ABA 3: CONFIGURAR (CRIAR/EXCLUIR RESERVAS) ---
    with tab_config:
        st.subheader("Criar Nova Reserva")
        
        with st.form("form_new"):
            nome = st.text_input("Nome da Reserva (Ex: Fundo de Emergência)")
            
            c1, c2 = st.columns(2)
            tipo = c1.selectbox("Tipo de Aplicação", ["CDB", "LCI/LCA", "Tesouro Direto", "Poupança", "Fundo DI", "Caixinha/Cofre", "Outro"])
            meta = c2.number_input("Meta para este pote (R$)", min_value=0.0)
            
            st.markdown("### 📊 Rentabilidade")
            c3, c4 = st.columns(2)
            indice = c3.selectbox("Índice Base", ["CDI", "Selic", "IPCA", "Pré-fixado", "TR", "Poupança", "Outro"])
            taxa = c4.number_input("Taxa (%)", min_value=0.0, value=100.0, step=0.1)
            
            if st.form_submit_button("Salvar Nova Reserva"):
                salvar_reserva_conta(user_id, nome, tipo, indice, taxa, meta)
                st.success("Reserva criada com sucesso!")
                st.rerun()
        
        if not df_reservas.empty:
            st.divider()
            st.subheader("🗑️ Zona de Perigo")
            del_sel = st.selectbox("Selecione uma Reserva para EXCLUIR PERMANENTEMENTE:", df_reservas['nome'].tolist())
            
            st.warning("Atenção: Excluir a reserva apagará todo o histórico de transações dela.")
            if st.button("Confirmar Exclusão da Reserva"):
                rid = int(df_reservas[df_reservas['nome'] == del_sel]['id'].values[0])
                excluir_reserva_conta(user_id, rid)
                st.success("Reserva apagada.")
                st.rerun()