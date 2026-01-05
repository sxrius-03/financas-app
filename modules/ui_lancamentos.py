import streamlit as st
from datetime import datetime, date
import pandas as pd
from modules.database import salvar_lancamento, carregar_dados, excluir_lancamento, atualizar_lancamento
from modules.constants import CATEGORIAS

# ==============================================================================
# 🎛️ PAINEL DE CONTROLE (CONFIGURAÇÕES DE UI & DESIGN)
# ==============================================================================

CONFIG_UI = {
    "GERAL": {
        "titulo_aba_novo": "➕ Novo Lançamento",
        "titulo_aba_gerenciar": "📝 Editor de Lançamentos (Tabela)",
        "header_novo": "📝 Registrar Movimentação (Caixa)",
        "caption_novo": "Use esta tela para movimentações que afetam seu saldo IMEDIATAMENTE (Débito, PIX, Dinheiro).",
        "header_gerenciar": "🗂️ Gerenciamento Rápido"
    },
    "FORMULARIO": {
        "lbl_data": "Data da Transação",
        "lbl_tipo": "Tipo de Movimento",
        "lbl_cat": "Categoria",
        "lbl_sub": "Subcategoria",
        "lbl_desc": "Descrição",
        "lbl_valor": "Valor (R$)",
        "lbl_forma": "Forma de Pagamento",
        "lbl_conta": "Conta / Instituição",
        "lbl_status": "Status Atual",
        "btn_salvar": "💾 Salvar Lançamento",
        "msg_sucesso": "Lançamento salvo com sucesso!"
    },
    "TABELA": {
        "col_excluir": "🗑️",
        "col_id": "ID",
        "col_data": "📅 Data",
        "col_tipo": "Tipo",
        "col_cat": "📂 Categoria",
        "col_sub": "Subcategoria",
        "col_desc": "📝 Descrição",
        "col_valor": "💲 Valor (R$)",
        "col_conta": "🏦 Conta",
        "col_forma": "💳 Forma Pagto",
        "col_status": "Estado",
        "help_excluir": "Marque para apagar este lançamento"
    },
    "FILTROS": {
        "lbl_ano": "Ano",
        "lbl_mes": "Mês",
        "lbl_tipo": "Tipo",
        "lbl_cat": "Categoria"
    }
}

# --- CORES (SISTEMA HSL) ---
CORES = {
    "receita": "hsl(154, 65%, 55%)",    
    "despesa": "hsl(0, 87%, 50%)",      
    "texto_geral": "hsl(0, 0%, 90%)",
}

# Listas Globais para Dropdowns da Tabela
LISTA_TIPOS = ["Receita", "Despesa"]
LISTA_CATEGORIAS = []
for k, v in CATEGORIAS.items():
    LISTA_CATEGORIAS.extend(list(v.keys()))
LISTA_CATEGORIAS = sorted(list(set(LISTA_CATEGORIAS))) # Remove duplicatas e ordena

LISTA_CONTAS = ["Nubank", "Sicredi", "Sicoob", "BNDES", "Banco do Brasil", "Bradesco", "Itaú", "Santander", "Caixa", "Inter", "C6 Bank", "Investimento", "Carteira", "Vale Alimentação", "Conta Principal"]
LISTA_FORMAS = ["PIX", "Transferência", "Cartão de Débito", "Boleto", "Dinheiro", "Cheque", "Vale Alimentação", "Depósito", "Boleto/Automático"]
LISTA_STATUS = ["Pago/Recebido", "Pendente", "Agendado"]

# ==============================================================================
# 🛠️ FUNÇÕES AUXILIARES
# ==============================================================================

def aplicar_estilo_editor(df):
    """
    Aplica estilo visual ao DataFrame.
    """
    def colorir_valor(row):
        # Define cores baseadas no tipo
        cor_fundo = CORES['receita'] if row['tipo'] == 'Receita' else CORES['despesa']
        cor_texto = "white"
        
        estilos = [''] * len(row)
        
        if 'valor' in row.index:
            idx = row.index.get_loc('valor')
            estilos[idx] = f'background-color: {cor_fundo}; color: {cor_texto}; font-weight: bold; border-radius: 5px; text-align: center;'
        
        return estilos

    # .set_properties centraliza o texto de todas as células
    styler = df.style.set_properties(**{'text-align': 'center'}).apply(colorir_valor, axis=1)
    return styler

def show_lancamentos():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']

    tab_novo, tab_gerenciar = st.tabs([
        CONFIG_UI["GERAL"]["titulo_aba_novo"], 
        CONFIG_UI["GERAL"]["titulo_aba_gerenciar"]
    ])

    # ===================================================
    # ABA 1: ADICIONAR NOVO (MANTIDA ORIGINAL)
    # ===================================================
    with tab_novo:
        st.header(CONFIG_UI["GERAL"]["header_novo"])
        st.caption(CONFIG_UI["GERAL"]["caption_novo"])

        mapa_categorias = CATEGORIAS

        col1, col2 = st.columns(2)
        data = col1.date_input(CONFIG_UI["FORMULARIO"]["lbl_data"], datetime.today())
        tipo = col2.selectbox(CONFIG_UI["FORMULARIO"]["lbl_tipo"], options=list(mapa_categorias.keys()), key="sb_tipo_novo")
        
        col3, col4 = st.columns(2)
        opcoes_categoria = list(mapa_categorias[tipo].keys())
        categoria = col3.selectbox(CONFIG_UI["FORMULARIO"]["lbl_cat"], options=opcoes_categoria, key="sb_cat_novo")
        
        opcoes_subcategoria = mapa_categorias[tipo][categoria]
        subcategoria = col4.selectbox(CONFIG_UI["FORMULARIO"]["lbl_sub"], options=opcoes_subcategoria, key="sb_sub_novo")
        
        descricao = st.text_input(CONFIG_UI["FORMULARIO"]["lbl_desc"], placeholder="Ex: Jantar no Outback")
        
        col5, col6, col7 = st.columns(3)
        valor = col5.number_input(CONFIG_UI["FORMULARIO"]["lbl_valor"], min_value=0.01, format="%.2f", step=10.00)
        
        with col6:
            metodo_pagamento = st.selectbox(CONFIG_UI["FORMULARIO"]["lbl_forma"], LISTA_FORMAS, key="sb_metodo_novo")
            conta_final = st.selectbox(CONFIG_UI["FORMULARIO"]["lbl_conta"], LISTA_CONTAS, key="sb_conta_novo")

        status = col7.selectbox(CONFIG_UI["FORMULARIO"]["lbl_status"], LISTA_STATUS, key="sb_status_novo")
        
        st.markdown("---")
        
        if st.button(CONFIG_UI["FORMULARIO"]["btn_salvar"], type="primary", use_container_width=True):
            novo_dado = {
                "data": data.strftime("%Y-%m-%d"), "tipo": tipo, "categoria": categoria,
                "subcategoria": subcategoria, "descricao": descricao, "valor": valor,
                "conta": conta_final, "forma_pagamento": metodo_pagamento, "status": status
            }
            salvar_lancamento(user_id, novo_dado)
            st.toast(CONFIG_UI["FORMULARIO"]["msg_sucesso"], icon="✅")

    # ===================================================
    # ABA 2: GERENCIAR (TABELA 100% EDITÁVEL)
    # ===================================================
    with tab_gerenciar:
        st.header(CONFIG_UI["GERAL"]["header_gerenciar"])
        
        # 1. Carrega Dados
        df = carregar_dados(user_id)
        
        if df.empty:
            st.info("Nenhum lançamento encontrado.")
        else:
            # Prepara filtros
            df['data'] = pd.to_datetime(df['data'])
            df['Ano'] = df['data'].dt.year
            df['Mes'] = df['data'].dt.month
            
            with st.expander("🔍 Filtros Rápidos", expanded=False):
                c_ano, c_mes, c_tipo, c_cat = st.columns(4)
                
                anos = sorted(df['Ano'].unique())
                f_ano = c_ano.selectbox(CONFIG_UI["FILTROS"]["lbl_ano"], ["Todos"] + list(map(str, anos)))
                
                f_mes = "Todos"
                if f_ano != "Todos":
                    meses = sorted(df[df['Ano'] == int(f_ano)]['Mes'].unique())
                    f_mes = c_mes.selectbox(CONFIG_UI["FILTROS"]["lbl_mes"], ["Todos"] + list(map(str, meses)))
                
                f_tipo = c_tipo.selectbox(CONFIG_UI["FILTROS"]["lbl_tipo"], ["Todos"] + LISTA_TIPOS)
                
                cats_disp = sorted(df['categoria'].unique())
                f_cat = c_cat.selectbox(CONFIG_UI["FILTROS"]["lbl_cat"], ["Todos"] + list(cats_disp))

            # Aplica Filtros
            df_view = df.copy()
            if f_ano != "Todos": df_view = df_view[df_view['Ano'] == int(f_ano)]
            if f_mes != "Todos": df_view = df_view[df_view['Mes'] == int(f_mes)]
            if f_tipo != "Todos": df_view = df_view[df_view['tipo'] == f_tipo]
            if f_cat != "Todos": df_view = df_view[df_view['categoria'] == f_cat]

            # 2. Prepara Dataframe para Edição
            # Movemos a lógica de exclusão para dentro da tabela usando uma coluna booleana
            if "Excluir" not in df_view.columns:
                df_view["Excluir"] = False
            
            # Reordena colunas para colocar Excluir no final
            colunas_ordem = ['id', 'data', 'tipo', 'categoria', 'subcategoria', 'descricao', 'valor', 'conta', 'forma_pagamento', 'status', 'Excluir']
            df_editor = df_view[colunas_ordem].copy()

            # 3. Configuração da Tabela Editável (DROPDOWNS AQUI)
            col_config = {
                "id": st.column_config.NumberColumn(CONFIG_UI["TABELA"]["col_id"], disabled=True, width="small"),
                "data": st.column_config.DateColumn(CONFIG_UI["TABELA"]["col_data"], format="DD/MM/YYYY"),
                "tipo": st.column_config.SelectboxColumn(
                    CONFIG_UI["TABELA"]["col_tipo"], 
                    options=LISTA_TIPOS, 
                    required=True,
                    width="medium"
                ),
                "categoria": st.column_config.SelectboxColumn(
                    CONFIG_UI["TABELA"]["col_cat"], 
                    options=LISTA_CATEGORIAS,
                    required=True,
                    width="medium"
                ),
                "subcategoria": st.column_config.TextColumn(CONFIG_UI["TABELA"]["col_sub"]),
                "descricao": st.column_config.TextColumn(CONFIG_UI["TABELA"]["col_desc"], width="large"),
                "valor": st.column_config.NumberColumn(CONFIG_UI["TABELA"]["col_valor"], format="R$ %.2f", min_value=0.01),
                "conta": st.column_config.SelectboxColumn(
                    CONFIG_UI["TABELA"]["col_conta"],
                    options=LISTA_CONTAS,
                    required=True
                ),
                "forma_pagamento": st.column_config.SelectboxColumn(
                    CONFIG_UI["TABELA"]["col_forma"],
                    options=LISTA_FORMAS,
                    required=True
                ),
                "status": st.column_config.SelectboxColumn(
                    CONFIG_UI["TABELA"]["col_status"],
                    options=LISTA_STATUS,
                    required=True
                ),
                "Excluir": st.column_config.CheckboxColumn(
                    CONFIG_UI["TABELA"]["col_excluir"],
                    help=CONFIG_UI["TABELA"]["help_excluir"],
                    default=False
                )
            }

            # Aplica Cores apenas para visualização inicial (o editor sobrescreve parcialmente)
            # Nota: O data_editor não suporta colorização dinâmica de linhas editadas em tempo real facilmente,
            # mas vamos passar o styler para colorir a carga inicial.
            styler = aplicar_estilo_editor(df_editor)

            st.caption("📝 Edite diretamente nas células abaixo. Para apagar, marque a caixa '🗑️' e clique em Salvar.")
            
            # --- RENDERIZA O EDITOR ---
            edited_df = st.data_editor(
                styler,
                column_config=col_config,
                use_container_width=True,
                hide_index=True,
                num_rows="fixed", # Não permite adicionar linhas, apenas editar existentes
                key="editor_lancamentos_geral"
            )

            # 4. Botão de Salvar Processamento
            # O Streamlit só detecta a mudança no edited_df. Precisamos comparar e salvar.
            
            col_btn, _ = st.columns([1, 4])
            if col_btn.button("💾 Salvar Alterações na Tabela", type="primary"):
                # Lógica de Comparação e Salvamento
                
                # 1. Detectar Exclusões
                itens_excluir = edited_df[edited_df['Excluir'] == True]
                count_del = 0
                for index, row in itens_excluir.iterrows():
                    excluir_lancamento(user_id, int(row['id']))
                    count_del += 1
                
                # 2. Detectar Edições (Onde Excluir é False)
                # Para ser eficiente, poderíamos comparar com o original, mas para simplificar e garantir,
                # atualizamos os itens visíveis que não foram excluídos.
                # (Num sistema maior, compararíamos row a row para update seletivo)
                
                itens_editar = edited_df[edited_df['Excluir'] == False]
                count_edit = 0
                
                # Vamos comparar com o DF original (df_view) para só fazer update no que mudou
                # Precisamos garantir que o índice alinhe ou usar o ID
                
                for i, row_new in itens_editar.iterrows():
                    # Busca linha original pelo ID
                    id_atual = int(row_new['id'])
                    row_old = df[df['id'] == id_atual]
                    
                    if not row_old.empty:
                        row_old = row_old.iloc[0]
                        # Verifica se algo mudou
                        mudou = (
                            row_new['data'] != pd.to_datetime(row_old['data']) or
                            row_new['tipo'] != row_old['tipo'] or
                            row_new['categoria'] != row_old['categoria'] or
                            row_new['subcategoria'] != row_old['subcategoria'] or
                            row_new['descricao'] != row_old['descricao'] or
                            float(row_new['valor']) != float(row_old['valor']) or
                            row_new['conta'] != row_old['conta'] or
                            row_new['forma_pagamento'] != row_old['forma_pagamento'] or
                            row_new['status'] != row_old['status']
                        )
                        
                        if mudou:
                            dados_update = {
                                "data": row_new['data'],
                                "tipo": row_new['tipo'],
                                "categoria": row_new['categoria'],
                                "subcategoria": row_new['subcategoria'],
                                "descricao": row_new['descricao'],
                                "valor": float(row_new['valor']),
                                "conta": row_new['conta'],
                                "forma_pagamento": row_new['forma_pagamento'],
                                "status": row_new['status']
                            }
                            atualizar_lancamento(user_id, id_atual, dados_update)
                            count_edit += 1

                if count_del > 0 or count_edit > 0:
                    st.success(f"Sucesso! {count_edit} editados e {count_del} excluídos.")
                    st.rerun()
                else:
                    st.info("Nenhuma alteração detectada.")