import streamlit as st
import pandas as pd
from datetime import datetime
from modules.database import salvar_lancamento, carregar_dados, excluir_lancamento, atualizar_lancamento
from modules.constants import CATEGORIAS

# Tenta importar o AgGrid (com tratamento de erro amigável)
try:
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode
except ImportError:
    st.error("⚠️ Biblioteca 'streamlit-aggrid' não detectada. Por favor, adicione ao requirements.txt.")
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
        # Nomes das colunas para exibição
        "data": "📅 Data",
        "tipo": "Tipo",
        "hierarquia": "📂 Categoria Completa (Tipo > Cat > Sub)",
        "descricao": "📝 Descrição",
        "valor": "💲 Valor (R$)",
        "conta": "🏦 Conta",
        "forma_pagamento": "💳 Forma Pagto",
        "status": "Estado",
        "delete": "🗑️"
    }
}

# Listas Auxiliares
LISTA_CONTAS = ["Nubank", "Sicredi", "Sicoob", "BNDES", "Banco do Brasil", "Bradesco", "Itaú", "Santander", "Caixa", "Inter", "C6 Bank", "Investimento", "Carteira", "Vale Alimentação", "Conta Principal"]
LISTA_FORMAS = ["PIX", "Transferência", "Cartão de Débito", "Boleto", "Dinheiro", "Cheque", "Vale Alimentação", "Depósito", "Boleto/Automático"]
LISTA_STATUS = ["Pago/Recebido", "Pendente", "Agendado"]

# Gerador de Lista Hierárquica (Resolve a confusão visual)
# Cria strings como: "Despesa > Moradia > Aluguel"
LISTA_HIERARQUICA = []
for tipo, cats in CATEGORIAS.items():
    for cat, subs in cats.items():
        for sub in subs:
            LISTA_HIERARQUICA.append(f"{tipo} > {cat} > {sub}")
LISTA_HIERARQUICA.sort()

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
    # ABA 1: ADICIONAR NOVO (MANTIDO IGUAL)
    # ===================================================
    with tab_novo:
        st.header("📝 Registrar Movimentação")
        
        col1, col2 = st.columns(2)
        data = col1.date_input("Data", datetime.today())
        tipo = col2.selectbox("Tipo", list(CATEGORIAS.keys()))
        
        col3, col4 = st.columns(2)
        cats = list(CATEGORIAS[tipo].keys())
        categoria = col3.selectbox("Categoria", cats)
        subs = CATEGORIAS[tipo][categoria]
        subcategoria = col4.selectbox("Subcategoria", subs)
        
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
    # ABA 2: GERENCIAR COM AG-GRID
    # ===================================================
    with tab_gerenciar:
        st.caption("💡 Dica: Clique na célula para editar. Use a coluna da direita para selecionar itens para exclusão.")
        
        df = carregar_dados(user_id)
        
        if df.empty:
            st.info("Sem dados.")
            return

        # 1. Preparação dos Dados (Criar coluna hierárquica para facilitar edição)
        df['data'] = pd.to_datetime(df['data']).dt.strftime('%Y-%m-%d')
        # Cria a coluna combinada para o dropdown inteligente
        df['hierarquia'] = df.apply(lambda x: f"{x['tipo']} > {x['categoria']} > {x['subcategoria']}", axis=1)
        
        # Seleciona colunas úteis
        cols = ['id', 'data', 'hierarquia', 'descricao', 'valor', 'conta', 'forma_pagamento', 'status']
        df_grid = df[cols].copy()

        # 2. Configuração do AgGrid
        gb = GridOptionsBuilder.from_dataframe(df_grid)
        
        # Configurações Globais
        gb.configure_default_column(
            editable=True, 
            resizable=True, 
            filterable=True, 
            sortable=True,
            minWidth=100
        )
        
        # Coluna ID (Oculta ou travada)
        gb.configure_column("id", hide=True)
        
        # Coluna Data
        gb.configure_column(
            "data", 
            headerName=CONFIG_UI["TABELA"]["data"],
            cellEditor="agDateStringCellEditor",
            width=120
        )
        
        # Coluna Hierarquia (O PULO DO GATO 🐱)
        # Dropdown único que resolve Tipo/Cat/Sub
        gb.configure_column(
            "hierarquia",
            headerName=CONFIG_UI["TABELA"]["hierarquia"],
            cellEditor="agSelectCellEditor",
            cellEditorParams={"values": LISTA_HIERARQUICA},
            width=300
        )
        
        # Outras Colunas com Dropdowns
        gb.configure_column("descricao", headerName=CONFIG_UI["TABELA"]["descricao"], width=250)
        gb.configure_column(
            "valor", 
            headerName=CONFIG_UI["TABELA"]["valor"], 
            type=["numericColumn", "numberColumnFilter"], 
            valueFormatter="x.toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'})",
            width=130
        )
        gb.configure_column("conta", headerName=CONFIG_UI["TABELA"]["conta"], cellEditor="agSelectCellEditor", cellEditorParams={"values": LISTA_CONTAS})
        gb.configure_column("forma_pagamento", headerName=CONFIG_UI["TABELA"]["forma_pagamento"], cellEditor="agSelectCellEditor", cellEditorParams={"values": LISTA_FORMAS})
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
            """)
        )

        # Configuração de Seleção (Para Excluir)
        gb.configure_selection(selection_mode="multiple", use_checkbox=True)
        
        # Paginação (Opcional, remove se quiser scroll infinito)
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
        
        gridOptions = gb.build()

        # 3. Renderiza a Grid
        # key='grid1' é importante para manter o estado
        grid_response = AgGrid(
            df_grid,
            gridOptions=gridOptions,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            fit_columns_on_grid_load=False,
            height=500,
            allow_unsafe_jscode=True, # Necessário para o formatador de moeda e cores
            theme="streamlit", # Tema dark nativo
            key='grid_lancamentos'
        )

        # 4. Lógica de Atualização e Exclusão
        
        # Botões de Ação Fora da Grid (Mais seguro e performático que botão na linha)
        c_del, c_save = st.columns([1, 4])
        
        with c_del:
            # Pega as linhas selecionadas pelo checkbox
            selected_rows = grid_response.get('selected_rows')
            
            # --- CORREÇÃO DO BUG AQUI ---
            # Verifica se não é None antes de checar o len()
            if selected_rows is not None and len(selected_rows) > 0:
                if st.button(f"🗑️ Excluir {len(selected_rows)} Selecionados", type="primary"):
                    # Como selected_rows pode vir como DataFrame ou Lista de Dicts dependendo da versão
                    if isinstance(selected_rows, pd.DataFrame):
                        ids_to_delete = selected_rows['id'].tolist()
                    else:
                        ids_to_delete = [row['id'] for row in selected_rows]
                        
                    for pid in ids_to_delete:
                        excluir_lancamento(user_id, int(pid))
                    
                    st.success("Itens excluídos!")
                    st.rerun()
        
        with c_save:
            # Detecta edições comparando com o original
            # O grid_response['data'] contém o estado atual da tabela visual
            df_edited = grid_response['data']
            
            if df_edited is not None and not df_edited.empty:
                if st.button("💾 Salvar Alterações da Tabela"):
                    count_updates = 0
                    
                    # Itera sobre o DF editado
                    # Nota: df_edited é um DataFrame pandas
                    for index, row in df_edited.iterrows():
                        # Recupera o original para comparar
                        id_row = int(row['id'])
                        original = df[df['id'] == id_row]
                        
                        if not original.empty:
                            orig = original.iloc[0]
                            
                            # Reconstrói Tipo/Cat/Sub da string hierárquica
                            # Formato: "Tipo > Categoria > Sub"
                            try:
                                parts = row['hierarquia'].split(" > ")
                                if len(parts) == 3:
                                    new_tipo, new_cat, new_sub = parts[0], parts[1], parts[2]
                                else:
                                    # Fallback se algo der errado na string
                                    new_tipo, new_cat, new_sub = orig['tipo'], orig['categoria'], orig['subcategoria']
                            except:
                                new_tipo, new_cat, new_sub = orig['tipo'], orig['categoria'], orig['subcategoria']

                            # Checa mudanças
                            # Convertemos para string/float garantindo compatibilidade
                            val_novo = float(row['valor'])
                            val_orig = float(orig['valor'])
                            
                            mudou = (
                                str(row['descricao']) != str(orig['descricao']) or
                                abs(val_novo - val_orig) > 0.001 or
                                str(row['data'])[:10] != str(orig['data'])[:10] or 
                                str(row['conta']) != str(orig['conta']) or
                                str(row['status']) != str(orig['status']) or
                                str(row['forma_pagamento']) != str(orig['forma_pagamento']) or
                                str(new_cat) != str(orig['categoria']) or
                                str(new_sub) != str(orig['subcategoria'])
                            )
                            
                            if mudou:
                                dados_up = {
                                    "data": row['data'],
                                    "tipo": new_tipo,
                                    "categoria": new_cat,
                                    "subcategoria": new_sub,
                                    "descricao": row['descricao'],
                                    "valor": val_novo,
                                    "conta": row['conta'],
                                    "forma_pagamento": row['forma_pagamento'],
                                    "status": row['status']
                                }
                                atualizar_lancamento(user_id, id_row, dados_up)
                                count_updates += 1
                    
                    if count_updates > 0:
                        st.success(f"{count_updates} lançamentos atualizados com sucesso!")
                        st.rerun()
                    else:
                        st.info("Nenhuma alteração encontrada para salvar.")