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
        "titulo_aba_gerenciar": "📊 Editor Avançado (Tabela)",
    },
    "TABELA": {
        "excluir": "🗑️ Excluir?",
        "data": "📅 Data",
        "tipo": "Tipo",
        "categoria": "📂 Categoria",
        "subcategoria": "🗂️ Subcategoria",
        "descricao": "📝 Descrição",
        "valor": "💲 Valor (R$)",
        "conta": "🏦 Conta",
        "forma_pagamento": "💳 Forma Pagto",
        "status": "Estado"
    }
}

# --- LISTAS COMPLETAS (Para garantir que o dropdown sempre abra) ---
LISTA_CONTAS = ["Nubank", "Sicredi", "Sicoob", "BNDES", "Banco do Brasil", "Bradesco", "Itaú", "Santander", "Caixa", "Inter", "C6 Bank", "Investimento", "Carteira", "Vale Alimentação", "Conta Principal"]
LISTA_FORMAS = ["PIX", "Transferência", "Cartão de Débito", "Boleto", "Dinheiro", "Cheque", "Vale Alimentação", "Depósito", "Boleto/Automático"]
LISTA_STATUS = ["Pago/Recebido", "Pendente", "Agendado"]
LISTA_TIPOS = ["Receita", "Despesa"]

# Gera listas planas e ordenadas
todas_cats = set()
todas_subs = set()
for t, cats in CATEGORIAS.items():
    for c, subs in cats.items():
        todas_cats.add(c)
        for s in subs:
            todas_subs.add(s)

LISTA_CATEGORIAS = sorted(list(todas_cats))
LISTA_SUBCATEGORIAS = sorted(list(todas_subs))

# ==============================================================================
# 🧠 JAVASCRIPT PARA VALIDAÇÃO VISUAL
# ==============================================================================
# Já que não podemos filtrar a lista, vamos pintar de VERMELHO se estiver errado.

mapa_json = json.dumps(CATEGORIAS)

js_valida_categoria = JsCode(f"""
function(params) {{
    const map = {mapa_json};
    const tipo = params.data.tipo;
    const cat = params.value;
    
    // Se a categoria não existir dentro do Tipo selecionado -> Vermelho
    if (tipo && map[tipo]) {{
        if (!map[tipo][cat]) {{
            return {{'backgroundColor': '#ffcccc', 'color': 'red', 'fontWeight': 'bold'}}; 
        }}
    }}
    return null; // Normal
}}
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
    # ABA 1: ADICIONAR NOVO (MANTIDO IGUAL)
    # ===================================================
    with tab_novo:
        st.header("📝 Registrar Movimentação")
        
        col1, col2 = st.columns(2)
        data = col1.date_input("Data", datetime.today())
        tipo = col2.selectbox("Tipo", list(CATEGORIAS.keys()))
        
        col3, col4 = st.columns(2)
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
    # ABA 2: GERENCIAR (TABELA COM EXCLUSÃO INTEGRADA)
    # ===================================================
    with tab_gerenciar:
        st.info("💡 Marque a caixa '🗑️' para excluir. Categorias inválidas ficarão vermelhas.")
        
        df = carregar_dados(user_id)
        
        if df.empty:
            st.warning("Sem dados.")
            return

        # 1. Preparação dos Dados
        df['data'] = pd.to_datetime(df['data']).dt.strftime('%Y-%m-%d')
        
        # Adiciona coluna de controle de exclusão (padrão False)
        if 'excluir' not in df.columns:
            df.insert(0, 'excluir', False)
            
        cols = ['excluir', 'id', 'data', 'tipo', 'categoria', 'subcategoria', 'descricao', 'valor', 'conta', 'forma_pagamento', 'status']
        df_grid = df[cols].copy()

        # 2. Configuração do AgGrid
        gb = GridOptionsBuilder.from_dataframe(df_grid)
        
        gb.configure_default_column(editable=True, resizable=True, filterable=True, sortable=True)
        gb.configure_column("id", hide=True)
        
        # Coluna EXCLUIR (Checkbox)
        gb.configure_column(
            "excluir", 
            headerName=CONFIG_UI["TABELA"]["excluir"], 
            cellEditor="agCheckboxCellEditor", 
            width=90,
            pinned="left" # Fixa na esquerda
        )

        gb.configure_column("data", headerName=CONFIG_UI["TABELA"]["data"], cellEditor="agDateStringCellEditor", width=110)
        
        # --- COLUNAS DE CATEGORIZAÇÃO (Listas Fixas + Validação Visual) ---
        gb.configure_column("tipo", headerName="Tipo", cellEditor="agSelectCellEditor", cellEditorParams={"values": LISTA_TIPOS}, width=100)
        
        gb.configure_column(
            "categoria", 
            headerName="Categoria", 
            cellEditor="agSelectCellEditor", 
            cellEditorParams={"values": LISTA_CATEGORIAS}, 
            cellStyle=js_valida_categoria, # Fica vermelho se incoerente
            width=150
        )
        
        gb.configure_column(
            "subcategoria", 
            headerName="Subcategoria", 
            cellEditor="agSelectCellEditor", 
            cellEditorParams={"values": LISTA_SUBCATEGORIAS}, 
            width=150
        )
        # ------------------------------------------------------------------

        gb.configure_column("descricao", headerName="Descrição", width=200)
        gb.configure_column("valor", headerName="Valor", type=["numericColumn"], width=120)
        gb.configure_column("conta", headerName="Conta", cellEditor="agSelectCellEditor", cellEditorParams={"values": LISTA_CONTAS}, width=130)
        gb.configure_column("forma_pagamento", headerName="Forma", cellEditor="agSelectCellEditor", cellEditorParams={"values": LISTA_FORMAS}, width=140)
        gb.configure_column("status", headerName="Status", cellEditor="agSelectCellEditor", cellEditorParams={"values": LISTA_STATUS}, width=130)

        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        
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
            key='grid_lancamentos_final'
        )

        # 4. Botão Único de Salvar (Processa Edições e Exclusões)
        st.write("")
        if st.button("💾 PROCESSAR ALTERAÇÕES (Salvar Edições e Excluir Marcados)", type="primary", use_container_width=True):
            df_edited = grid_response['data']
            
            if df_edited is not None and not df_edited.empty:
                count_edit = 0
                count_del = 0
                
                for index, row in df_edited.iterrows():
                    id_row = int(row['id'])
                    
                    # 1. Checa Exclusão
                    if row['excluir'] == True:
                        excluir_lancamento(user_id, id_row)
                        count_del += 1
                        continue # Pula para o próximo, pois esse foi deletado
                    
                    # 2. Checa Edição
                    original = df[df['id'] == id_row]
                    if not original.empty:
                        orig = original.iloc[0]
                        val_novo = float(row['valor'])
                        val_orig = float(orig['valor'])
                        
                        mudou = (
                            str(row['descricao']) != str(orig['descricao']) or
                            abs(val_novo - val_orig) > 0.001 or
                            str(row['data'])[:10] != str(orig['data'])[:10] or 
                            str(row['conta']) != str(orig['conta']) or
                            str(row['status']) != str(orig['status']) or
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
                            count_edit += 1
                
                if count_del > 0 or count_edit > 0:
                    st.success(f"✅ Sucesso! {count_del} excluídos e {count_edit} atualizados.")
                    st.rerun()
                else:
                    st.info("Nenhuma alteração pendente.")