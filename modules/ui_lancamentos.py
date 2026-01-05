import streamlit as st
import pandas as pd
from datetime import datetime
from modules.database import salvar_lancamento, carregar_dados, excluir_lancamento, atualizar_lancamento
from modules.constants import CATEGORIAS

# Tenta importar o AgGrid
try:
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode
except ImportError:
    st.error("⚠️ Biblioteca 'streamlit-aggrid' não detectada.")
    st.stop()

# ==============================================================================
# 🎛️ PAINEL DE CONTROLE
# ==============================================================================

CONFIG_UI = {
    "GERAL": {
        "titulo_aba_novo": "➕ Novo Lançamento",
        "titulo_aba_gerenciar": "📊 Editor Avançado (AgGrid)",
    },
    "TABELA": {
        "data": "📅 Data",
        "tipo": "Tipo",
        "categoria": "📂 Categoria",
        "subcategoria": "🗂️ Subcategoria",
        "descricao": "📝 Descrição",
        "valor": "💲 Valor (R$)",
        "conta": "🏦 Conta",
        "forma_pagamento": "💳 Forma Pagto",
        "status": "Estado",
        "delete": "🗑️"
    }
}

# --- LISTAS PARA DROPDOWNS ---
LISTA_CONTAS = ["Nubank", "Sicredi", "Sicoob", "BNDES", "Banco do Brasil", "Bradesco", "Itaú", "Santander", "Caixa", "Inter", "C6 Bank", "Investimento", "Carteira", "Vale Alimentação", "Conta Principal"]
LISTA_FORMAS = ["PIX", "Transferência", "Cartão de Débito", "Boleto", "Dinheiro", "Cheque", "Vale Alimentação", "Depósito", "Boleto/Automático"]
LISTA_STATUS = ["Pago/Recebido", "Pendente", "Agendado"]
LISTA_TIPOS = ["Receita", "Despesa"]

# --- GERAR LISTAS DE CATEGORIAS E SUBCATEGORIAS (FLAT) ---
# Extrai todas as categorias e subcategorias únicas do dicionário CATEGORIAS
todas_categorias = set()
todas_subcategorias = set()

for tipo, cats in CATEGORIAS.items():
    for cat, subs in cats.items():
        todas_categorias.add(cat)
        for sub in subs:
            todas_subcategorias.add(sub)

LISTA_CATEGORIAS = sorted(list(todas_categorias))
LISTA_SUBCATEGORIAS = sorted(list(todas_subcategorias))

# ==============================================================================
# 🛠️ FUNÇÕES
# ==============================================================================

def show_lancamentos():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']

    tab_novo, tab_gerenciar = st.tabs([
        CONFIG_UI["GERAL"]["titulo_aba_novo"], 
        CONFIG_UI["GERAL"]["titulo_aba_gerenciar"]
    ])

    # ===================================================
    # ABA 1: ADICIONAR NOVO (PADRÃO)
    # ===================================================
    with tab_novo:
        st.header("📝 Registrar Movimentação")
        
        col1, col2 = st.columns(2)
        data = col1.date_input("Data", datetime.today())
        tipo = col2.selectbox("Tipo", list(CATEGORIAS.keys()))
        
        col3, col4 = st.columns(2)
        # Aqui os dropdowns são dinâmicos (um depende do outro) pois é Streamlit nativo
        cats_disponiveis = list(CATEGORIAS[tipo].keys())
        categoria = col3.selectbox("Categoria", cats_disponiveis)
        
        subs_disponiveis = CATEGORIAS[tipo][categoria]
        subcategoria = col4.selectbox("Subcategoria", subs_disponiveis)
        
        descricao = st.text_input("Descrição", placeholder="Ex: Mercado Semanal")
        
        c5, c6, c7 = st.columns(3)
        valor = c5.number_input("Valor (R$)", min_value=0.01, step=10.0)
        conta = c6.selectbox("Conta", LISTA_CONTAS)
        forma = c7.selectbox("Forma", LISTA_FORMAS)
        status = st.selectbox("Status", LISTA_STATUS)
        
        st.markdown("---")
        if st.button("💾 Salvar Lançamento", type="primary", use_container_width=True):
            novo = {
                "data": data, "tipo": tipo, "categoria": categoria, "subcategoria": subcategoria,
                "descricao": descricao, "valor": valor, "conta": conta, "forma_pagamento": forma, "status": status
            }
            salvar_lancamento(user_id, novo)
            st.success("Lançamento salvo!")

    # ===================================================
    # ABA 2: GERENCIAR COM AG-GRID (3 COLUNAS)
    # ===================================================
    with tab_gerenciar:
        st.caption("💡 Edite clicando nas células. Use a caixa de seleção à esquerda para excluir.")
        
        df = carregar_dados(user_id)
        
        if df.empty:
            st.info("Sem dados.")
            return

        # 1. Preparação
        df['data'] = pd.to_datetime(df['data']).dt.strftime('%Y-%m-%d')
        
        # Seleciona colunas na ordem desejada
        cols = ['id', 'data', 'tipo', 'categoria', 'subcategoria', 'descricao', 'valor', 'conta', 'forma_pagamento', 'status']
        df_grid = df[cols].copy()

        # 2. Configuração do AgGrid
        gb = GridOptionsBuilder.from_dataframe(df_grid)
        
        gb.configure_default_column(
            editable=True, resizable=True, filterable=True, sortable=True, minWidth=100
        )
        
        gb.configure_column("id", hide=True)
        
        gb.configure_column("data", headerName=CONFIG_UI["TABELA"]["data"], cellEditor="agDateStringCellEditor", width=110)
        
        # --- AS 3 COLUNAS DE CATEGORIZAÇÃO ---
        gb.configure_column(
            "tipo", 
            headerName=CONFIG_UI["TABELA"]["tipo"], 
            cellEditor="agSelectCellEditor", 
            cellEditorParams={"values": LISTA_TIPOS},
            width=100
        )
        gb.configure_column(
            "categoria", 
            headerName=CONFIG_UI["TABELA"]["categoria"], 
            cellEditor="agSelectCellEditor", 
            cellEditorParams={"values": LISTA_CATEGORIAS},
            width=150
        )
        gb.configure_column(
            "subcategoria", 
            headerName=CONFIG_UI["TABELA"]["subcategoria"], 
            cellEditor="agSelectCellEditor", 
            cellEditorParams={"values": LISTA_SUBCATEGORIAS},
            width=150
        )
        # -------------------------------------

        gb.configure_column("descricao", headerName=CONFIG_UI["TABELA"]["descricao"], width=200)
        
        gb.configure_column(
            "valor", 
            headerName=CONFIG_UI["TABELA"]["valor"], 
            type=["numericColumn", "numberColumnFilter"], 
            valueFormatter="x.toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'})",
            width=120
        )
        
        gb.configure_column("conta", headerName=CONFIG_UI["TABELA"]["conta"], cellEditor="agSelectCellEditor", cellEditorParams={"values": LISTA_CONTAS}, width=130)
        gb.configure_column("forma_pagamento", headerName=CONFIG_UI["TABELA"]["forma_pagamento"], cellEditor="agSelectCellEditor", cellEditorParams={"values": LISTA_FORMAS}, width=140)
        
        gb.configure_column(
            "status", 
            headerName=CONFIG_UI["TABELA"]["status"], 
            cellEditor="agSelectCellEditor", 
            cellEditorParams={"values": LISTA_STATUS},
            cellStyle=JsCode("""
                function(params) {
                    if (params.value == 'Pago/Recebido') { return {'color': '#00FF7F', 'fontWeight': 'bold'}; }
                    if (params.value == 'Atrasado') { return {'color': '#FF4B4B'}; }
                    return null;
                }
            """),
            width=130
        )

        gb.configure_selection(selection_mode="multiple", use_checkbox=True)
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
        
        gridOptions = gb.build()

        # 3. Renderiza
        grid_response = AgGrid(
            df_grid,
            gridOptions=gridOptions,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            fit_columns_on_grid_load=False,
            height=500,
            allow_unsafe_jscode=True,
            theme="streamlit",
            key='grid_lancamentos_v2'
        )

        # 4. Ações
        c_del, c_save = st.columns([1, 4])
        
        with c_del:
            selected_rows = grid_response.get('selected_rows')
            # CORREÇÃO DO ERRO NoneType
            if selected_rows is not None and len(selected_rows) > 0:
                if st.button(f"🗑️ Excluir {len(selected_rows)} Itens", type="primary"):
                    if isinstance(selected_rows, pd.DataFrame):
                        ids_to_delete = selected_rows['id'].tolist()
                    else:
                        ids_to_delete = [row['id'] for row in selected_rows]
                        
                    for pid in ids_to_delete:
                        excluir_lancamento(user_id, int(pid))
                    
                    st.success("Excluído!")
                    st.rerun()
        
        with c_save:
            df_edited = grid_response['data']
            
            if df_edited is not None and not df_edited.empty:
                if st.button("💾 Salvar Alterações da Tabela"):
                    count_updates = 0
                    
                    for index, row in df_edited.iterrows():
                        id_row = int(row['id'])
                        # Busca original para comparar
                        original = df[df['id'] == id_row]
                        
                        if not original.empty:
                            orig = original.iloc[0]
                            
                            val_novo = float(row['valor'])
                            val_orig = float(orig['valor'])
                            
                            # Compara mudanças (agora com as 3 colunas separadas)
                            mudou = (
                                str(row['descricao']) != str(orig['descricao']) or
                                abs(val_novo - val_orig) > 0.001 or
                                str(row['data'])[:10] != str(orig['data'])[:10] or 
                                str(row['conta']) != str(orig['conta']) or
                                str(row['status']) != str(orig['status']) or
                                str(row['forma_pagamento']) != str(orig['forma_pagamento']) or
                                str(row['tipo']) != str(orig['tipo']) or
                                str(row['categoria']) != str(orig['categoria']) or
                                str(row['subcategoria']) != str(orig['subcategoria'])
                            )
                            
                            if mudou:
                                dados_up = {
                                    "data": row['data'],
                                    "tipo": row['tipo'],
                                    "categoria": row['categoria'],
                                    "subcategoria": row['subcategoria'],
                                    "descricao": row['descricao'],
                                    "valor": val_novo,
                                    "conta": row['conta'],
                                    "forma_pagamento": row['forma_pagamento'],
                                    "status": row['status']
                                }
                                atualizar_lancamento(user_id, id_row, dados_up)
                                count_updates += 1
                    
                    if count_updates > 0:
                        st.success(f"{count_updates} atualizados!")
                        st.rerun()
                    else:
                        st.info("Nenhuma alteração encontrada.")