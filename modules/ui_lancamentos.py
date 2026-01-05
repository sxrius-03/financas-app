import streamlit as st
from datetime import datetime
import pandas as pd
from modules.database import salvar_lancamento, carregar_dados, excluir_lancamento, atualizar_lancamento
from modules.constants import CATEGORIAS

# ==============================================================================
# 🎛️ PAINEL DE CONTROLE
# ==============================================================================

CONFIG_UI = {
    "GERAL": {
        "titulo_aba_novo": "➕ Novo Lançamento",
        "titulo_aba_gerenciar": "🔍 Gerenciar e Editar",
        "header_novo": "📝 Registrar Movimentação",
    },
    "TABELA": {
        "col_selecao": "Editar",
        "col_data": "📅 Data",
        "col_tipo": "Tipo",
        "col_cat": "📂 Categoria",
        "col_sub": "🗂️ Sub",
        "col_desc": "📝 Descrição",
        "col_valor": "💲 Valor",
        "col_conta": "🏦 Conta",
        "col_forma": "💳 Forma",
        "col_status": "Status"
    }
}

# Cores para o Styler
CORES = {
    "receita": "#2ecc71",    
    "despesa": "#e74c3c",      
    "texto": "white"
}

LISTA_CONTAS = ["Nubank", "Sicredi", "Sicoob", "BNDES", "Banco do Brasil", "Bradesco", "Itaú", "Santander", "Caixa", "Inter", "C6 Bank", "Investimento", "Carteira", "Vale Alimentação", "Conta Principal"]
LISTA_FORMAS = ["PIX", "Transferência", "Cartão de Débito", "Boleto", "Dinheiro", "Cheque", "Vale Alimentação", "Depósito", "Boleto/Automático"]
LISTA_STATUS = ["Pago/Recebido", "Pendente", "Agendado"]

# ==============================================================================
# 🛠️ FUNÇÕES
# ==============================================================================

def aplicar_estilo(df):
    def colorir(row):
        cor = CORES['receita'] if row['tipo'] == 'Receita' else CORES['despesa']
        estilos = [''] * len(row)
        if 'valor' in row.index:
            idx = row.index.get_loc('valor')
            estilos[idx] = f'background-color: {cor}; color: {CORES["texto"]}; font-weight: bold; text-align: center'
        return estilos
    
    return df.style.apply(colorir, axis=1).format({'valor': "R$ {:,.2f}", 'data': "{:%d/%m/%Y}"})

def show_lancamentos():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']

    tab_novo, tab_gerenciar = st.tabs([
        CONFIG_UI["GERAL"]["titulo_aba_novo"], 
        CONFIG_UI["GERAL"]["titulo_aba_gerenciar"]
    ])

    # ===================================================
    # ABA 1: NOVO LANCAMENTO
    # ===================================================
    with tab_novo:
        st.header(CONFIG_UI["GERAL"]["header_novo"])
        
        c1, c2 = st.columns(2)
        data = c1.date_input("Data", datetime.today(), key="n_data")
        tipo = c2.selectbox("Tipo", list(CATEGORIAS.keys()), key="n_tipo")
        
        c3, c4 = st.columns(2)
        # Dinâmico nativo do Streamlit
        cat_ops = list(CATEGORIAS[tipo].keys())
        categoria = c3.selectbox("Categoria", cat_ops, key="n_cat")
        
        sub_ops = CATEGORIAS[tipo][categoria]
        subcategoria = c4.selectbox("Subcategoria", sub_ops, key="n_sub")
        
        desc = st.text_input("Descrição", placeholder="Ex: Compra Mercado", key="n_desc")
        
        c5, c6, c7 = st.columns(3)
        val = c5.number_input("Valor (R$)", min_value=0.01, step=10.0, key="n_val")
        conta = c6.selectbox("Conta", LISTA_CONTAS, key="n_conta")
        status = c7.selectbox("Status", LISTA_STATUS, key="n_stat")
        
        forma = st.selectbox("Forma Pagto", LISTA_FORMAS, key="n_forma")
        
        if st.button("💾 Salvar", type="primary", use_container_width=True):
            novo = {
                "data": data, "tipo": tipo, "categoria": categoria, "subcategoria": subcategoria,
                "descricao": desc, "valor": val, "conta": conta, "forma_pagamento": forma, "status": status
            }
            salvar_lancamento(user_id, novo)
            st.success("Salvo com sucesso!")

    # ===================================================
    # ABA 2: GERENCIAR (SELEÇÃO + FORMULÁRIO)
    # ===================================================
    with tab_gerenciar:
        st.header("Gerenciar Lançamentos")
        
        df = carregar_dados(user_id)
        if df.empty:
            st.info("Sem dados.")
            return

        # 1. Filtros Rápidos
        with st.expander("🔍 Filtros"):
            c_f1, c_f2 = st.columns(2)
            f_tipo = c_f1.selectbox("Filtrar Tipo", ["Todos", "Receita", "Despesa"])
            if f_tipo != "Todos":
                df = df[df['tipo'] == f_tipo]
        
        # 2. Tabela de Seleção
        # Adiciona coluna de seleção
        df_view = df.copy()
        df_view.insert(0, "Selecionar", False)
        
        # Configuração das Colunas
        col_cfg = {
            "Selecionar": st.column_config.CheckboxColumn("Editar?", width="small"),
            "data": st.column_config.DateColumn(CONFIG_UI["TABELA"]["col_data"], format="DD/MM/YYYY"),
            "valor": st.column_config.NumberColumn(CONFIG_UI["TABELA"]["col_valor"], format="R$ %.2f"),
            "tipo": st.column_config.TextColumn(CONFIG_UI["TABELA"]["col_tipo"]),
            "categoria": st.column_config.TextColumn(CONFIG_UI["TABELA"]["col_cat"]),
            "subcategoria": st.column_config.TextColumn(CONFIG_UI["TABELA"]["col_sub"]),
            "descricao": st.column_config.TextColumn(CONFIG_UI["TABELA"]["col_desc"]),
            "conta": st.column_config.TextColumn(CONFIG_UI["TABELA"]["col_conta"]),
            "forma_pagamento": st.column_config.TextColumn(CONFIG_UI["TABELA"]["col_forma"]),
            "status": st.column_config.TextColumn(CONFIG_UI["TABELA"]["col_status"])
        }
        
        # Tabela (Data Editor usado apenas para selecionar a linha)
        edited_df = st.data_editor(
            df_view,
            column_config=col_cfg,
            hide_index=True,
            use_container_width=True,
            disabled=["id", "data", "tipo", "categoria", "subcategoria", "descricao", "valor", "conta", "forma_pagamento", "status"]
        )
        
        # 3. Identifica Seleção Única
        selecionados = edited_df[edited_df["Selecionar"] == True]
        
        st.divider()
        
        if len(selecionados) == 0:
            st.info("Selecione um item na tabela acima para editar ou excluir.")
            
        elif len(selecionados) > 1:
            st.warning("⚠️ Selecione apenas UM item por vez para editar.")
            # Opção de excluir em massa
            if st.button(f"🗑️ Excluir {len(selecionados)} itens selecionados", type="primary"):
                for idx, row in selecionados.iterrows():
                    excluir_lancamento(user_id, int(row['id']))
                st.success("Itens excluídos!")
                st.rerun()
                
        elif len(selecionados) == 1:
            # --- FORMULÁRIO DE EDIÇÃO ---
            row = selecionados.iloc[0]
            id_edit = int(row['id'])
            
            st.subheader(f"✏️ Editando: {row['descricao']}")
            
            with st.form(f"form_edit_{id_edit}"):
                ec1, ec2 = st.columns(2)
                e_data = ec1.date_input("Data", pd.to_datetime(row['data']))
                e_tipo = ec2.selectbox("Tipo", list(CATEGORIAS.keys()), index=list(CATEGORIAS.keys()).index(row['tipo']))
                
                ec3, ec4 = st.columns(2)
                # Dropdowns dinâmicos REAIS (aqui funcionam 100%)
                e_cats = list(CATEGORIAS[e_tipo].keys())
                # Tenta manter a categoria atual se compatível
                idx_cat = e_cats.index(row['categoria']) if row['categoria'] in e_cats else 0
                e_cat = ec3.selectbox("Categoria", e_cats, index=idx_cat)
                
                e_subs = CATEGORIAS[e_tipo][e_cat]
                idx_sub = e_subs.index(row['subcategoria']) if row['subcategoria'] in e_subs else 0
                e_sub = ec4.selectbox("Subcategoria", e_subs, index=idx_sub)
                
                e_desc = st.text_input("Descrição", value=row['descricao'])
                
                ec5, ec6, ec7 = st.columns(3)
                e_val = ec5.number_input("Valor", value=float(row['valor']), min_value=0.01)
                
                idx_conta = LISTA_CONTAS.index(row['conta']) if row['conta'] in LISTA_CONTAS else 0
                e_conta = ec6.selectbox("Conta", LISTA_CONTAS, index=idx_conta)
                
                idx_stat = LISTA_STATUS.index(row['status']) if row['status'] in LISTA_STATUS else 0
                e_stat = ec7.selectbox("Status", LISTA_STATUS, index=idx_stat)
                
                idx_forma = LISTA_FORMAS.index(row['forma_pagamento']) if row['forma_pagamento'] in LISTA_FORMAS else 0
                e_forma = st.selectbox("Forma Pagto", LISTA_FORMAS, index=idx_forma)
                
                c_save, c_del_single = st.columns([4, 1])
                
                if c_save.form_submit_button("💾 Salvar Alterações", type="primary"):
                    dados_up = {
                        "data": e_data, "tipo": e_tipo, "categoria": e_cat, "subcategoria": e_sub,
                        "descricao": e_desc, "valor": e_val, "conta": e_conta,
                        "forma_pagamento": e_forma, "status": e_stat
                    }
                    atualizar_lancamento(user_id, id_edit, dados_up)
                    st.success("Atualizado com sucesso!")
                    st.rerun()
            
            # Botão de excluir fora do form para não submeter
            if st.button("🗑️ Excluir este item", type="secondary"):
                excluir_lancamento(user_id, id_edit)
                st.success("Item excluído.")
                st.rerun()