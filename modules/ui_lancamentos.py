import streamlit as st
import pandas as pd
import json
from datetime import datetime
from modules.database import salvar_lancamento, carregar_dados, excluir_lancamento, atualizar_lancamento
from modules.constants import CATEGORIAS

# Tratamento de erro se a lib não estiver instalada
try:
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode
except ImportError:
    st.error("⚠️ Biblioteca 'streamlit-aggrid' necessária. Adicione ao requirements.txt")
    st.stop()

# ==============================================================================
# 🎛️ PAINEL DE CONTROLE
# ==============================================================================

CONFIG_UI = {
    "GERAL": {
        "titulo_aba_novo": "➕ Novo Lançamento",
        "titulo_aba_gerenciar": "📊 Editor Avançado (Tabela Dinâmica)",
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

# Listas Estáticas
LISTA_CONTAS = ["Nubank", "Sicredi", "Sicoob", "BNDES", "Banco do Brasil", "Bradesco", "Itaú", "Santander", "Caixa", "Inter", "C6 Bank", "Investimento", "Carteira", "Vale Alimentação", "Conta Principal"]
LISTA_FORMAS = ["PIX", "Transferência", "Cartão de Débito", "Boleto", "Dinheiro", "Cheque", "Vale Alimentação", "Depósito", "Boleto/Automático"]
LISTA_STATUS = ["Pago/Recebido", "Pendente", "Agendado"]
LISTA_TIPOS = ["Receita", "Despesa"]

# ==============================================================================
# 🧠 LÓGICA JAVASCRIPT (O Segredo do Dinamismo)
# ==============================================================================

# 1. Converte o dicionário Python para JSON para o JavaScript ler
categorias_json = json.dumps(CATEGORIAS)

# 2. JS para filtrar Categoria baseado no Tipo
js_categoria_renderer = JsCode(f"""
function(params) {{
    const map = {categorias_json};
    const tipo = params.data.tipo;
    if (tipo && map[tipo]) {{
        return Object.keys(map[tipo]);
    }}
    return ["Selecione o Tipo"];
}}
""")

# 3. JS para filtrar Subcategoria baseado no Tipo E Categoria
js_subcategoria_renderer = JsCode(f"""
function(params) {{
    const map = {categorias_json};
    const tipo = params.data.tipo;
    const cat = params.data.categoria;
    
    if (tipo && cat && map[tipo] && map[tipo][cat]) {{
        return map[tipo][cat];
    }}
    return ["Selecione a Categoria"];
}}
""")

# 4. JS para Limpar colunas filhas se o Pai mudar
js_on_cell_change = JsCode("""
function(params) {
    // Se mudar Tipo -> Limpa Categoria e Sub
    if (params.colDef.field === 'tipo') {
        params.node.setDataValue('categoria', '');
        params.node.setDataValue('subcategoria', '');
    }
    // Se mudar Categoria -> Limpa Sub
    if (params.colDef.field === 'categoria') {
        params.node.setDataValue('subcategoria', '');
    }
}
""")

# ==============================================================================
# 🛠️ FUNÇÕES DO MÓDULO
# ==============================================================================

def show_lancamentos():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']

    tab_novo, tab_gerenciar = st.tabs([
        CONFIG_UI["GERAL"]["titulo_aba_novo"], 
        CONFIG_UI["GERAL"]["titulo_aba_gerenciar"]
    ])

    # ===================================================
    # ABA 1: ADICIONAR NOVO (MANTIDO)
    # ===================================================
    with tab_novo:
        st.header("📝 Registrar Movimentação")
        
        col1, col2 = st.columns(2)
        data = col1.date_input("Data", datetime.today())
        tipo = col2.selectbox("Tipo", list(CATEGORIAS.keys()))
        
        col3, col4 = st.columns(2)
        # Dropdowns nativos do Streamlit (já são dinâmicos por padrão)
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
    # ABA 2: GERENCIAR (TABELA DINÂMICA)
    # ===================================================
    with tab_gerenciar:
        st.caption("💡 A tabela abaixo é inteligente: As opções de Categoria mudam conforme o Tipo escolhido.")
        
        df = carregar_dados(user_id)
        
        if df.empty:
            st.info("Sem dados.")
            return

        # 1. Preparação
        df['data'] = pd.to_datetime(df['data']).dt.strftime('%Y-%m-%d')
        cols = ['id', 'data', 'tipo', 'categoria', 'subcategoria', 'descricao', 'valor', 'conta', 'forma_pagamento', 'status']
        df_grid = df[cols].copy()

        # 2. Configuração do Grid
        gb = GridOptionsBuilder.from_dataframe(df_grid)
        
        gb.configure_default_column(editable=True, resizable=True, filterable=True, sortable=True)
        gb.configure_column("id", hide=True)
        gb.configure_column("data", headerName=CONFIG_UI["TABELA"]["data"], cellEditor="agDateStringCellEditor", width=110)
        
        # --- COLUNAS DINÂMICAS (USANDO agRichSelectCellEditor) ---
        # Nota: RichSelectCellEditor é mais robusto para listas dinâmicas via JS
        
        # Coluna Tipo (Pai)
        gb.configure_column(
            "tipo", 
            headerName=CONFIG_UI["TABELA"]["tipo"], 
            cellEditor="agSelectCellEditor", 
            cellEditorParams={"values": LISTA_TIPOS},
            width=100
        )
        
        # Coluna Categoria (Filha de Tipo) - USA RICH SELECT
        gb.configure_column(
            "categoria", 
            headerName=CONFIG_UI["TABELA"]["categoria"], 
            cellEditor="agRichSelectCellEditor", 
            cellEditorParams={"values": js_categoria_renderer}, # JS decide as opções
            width=150
        )
        
        # Coluna Subcategoria (Filha de Categoria) - USA RICH SELECT
        gb.configure_column(
            "subcategoria", 
            headerName=CONFIG_UI["TABELA"]["subcategoria"], 
            cellEditor="agRichSelectCellEditor", 
            cellEditorParams={"values": js_subcategoria_renderer}, # JS decide as opções
            width=150
        )
        
        # -------------------------------

        gb.configure_column("descricao", headerName=CONFIG_UI["TABELA"]["descricao"], width=200)
        
        gb.configure_column(
            "valor", 
            headerName=CONFIG_UI["TABELA"]["valor"], 
            type=["numericColumn"], 
            valueFormatter="x.toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'})",
            width=120
        )
        
        gb.configure_column("conta", headerName=CONFIG_UI["TABELA"]["conta"], cellEditor="agSelectCellEditor", cellEditorParams={"values": LISTA_CONTAS}, width=130)
        gb.configure_column("forma_pagamento", headerName=CONFIG_UI["TABELA"]["forma_pagamento"], cellEditor="agSelectCellEditor", cellEditorParams={"values": LISTA_FORMAS}, width=140)
        gb.configure_column("status", headerName=CONFIG_UI["TABELA"]["status"], cellEditor="agSelectCellEditor", cellEditorParams={"values": LISTA_STATUS}, width=130)

        # Configurações de Seleção e Eventos
        gb.configure_selection(selection_mode="multiple", use_checkbox=True)
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
        
        # Injeta o evento de limpeza automática
        gridOptions = gb.build()
        gridOptions['onCellValueChanged'] = js_on_cell_change

        # 3. Renderiza
        grid_response = AgGrid(
            df_grid,
            gridOptions=gridOptions,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            fit_columns_on_grid_load=False,
            height=500,
            allow_unsafe_jscode=True, # Obrigatório para o JS funcionar
            theme="streamlit",
            key='grid_lancamentos_dynamic_v2'
        )

        # 4. Ações (Salvar e Excluir)
        c_del, c_save = st.columns([1, 4])
        
        with c_del:
            selected_rows = grid_response.get('selected_rows')
            if selected_rows is not None and len(selected_rows) > 0:
                if st.button(f"🗑️ Excluir {len(selected_rows)} Itens", type="primary"):
                    if isinstance(selected_rows, pd.DataFrame):
                        ids_to_delete = selected_rows['id'].tolist()
                    else:
                        ids_to_delete = [row['id'] for row in selected_rows]
                        
                    for pid in ids_to_delete:
                        excluir_lancamento(user_id, int(pid)) # Converte para int nativo
                    
                    st.success("Excluído!")
                    st.rerun()
        
        with c_save:
            # Botão de salvar alterações
            if st.button("💾 Salvar Alterações da Tabela"):
                df_edited = grid_response['data']
                count_updates = 0
                
                # Itera e salva
                for index, row in df_edited.iterrows():
                    id_row = int(row['id'])
                    original = df[df['id'] == id_row]
                    
                    if not original.empty:
                        orig = original.iloc[0]
                        val_novo = float(row['valor'])
                        val_orig = float(orig['valor'])
                        
                        # Compara tudo
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
                                "data": row['data'], "tipo": row['tipo'], "categoria": row['categoria'],
                                "subcategoria": row['subcategoria'], "descricao": row['descricao'],
                                "valor": val_novo, "conta": row['conta'],
                                "forma_pagamento": row['forma_pagamento'], "status": row['status']
                            }
                            atualizar_lancamento(user_id, id_row, dados_up)
                            count_updates += 1
                
                if count_updates > 0:
                    st.success(f"{count_updates} atualizados!")
                    st.rerun()
                else:
                    st.info("Nenhuma alteração encontrada.")