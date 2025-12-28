import streamlit as st
from datetime import datetime
import pandas as pd
from modules.database import salvar_lancamento, carregar_dados, excluir_lancamento, atualizar_lancamento
from modules.constants import CATEGORIAS

def show_lancamentos():
    if 'user_id' not in st.session_state:
        st.error("Erro: Usuário não identificado.")
        return
    user_id = st.session_state['user_id']

    # Abas principais
    tab_novo, tab_gerenciar = st.tabs(["➕ Novo Lançamento", "🔍 Gerenciar / Filtros & Exclusão"])

    # ===================================================
    # ABA 1: ADICIONAR NOVO (MANTIDA ORIGINAL)
    # ===================================================
    with tab_novo:
        st.header("📝 Registrar Movimentação (Caixa)")
        st.caption("Use esta tela para movimentações que afetam seu saldo IMEDIATAMENTE (Débito, PIX, Dinheiro).")

        mapa_categorias = CATEGORIAS

        col1, col2 = st.columns(2)
        data = col1.date_input("Data", datetime.today())
        tipo = col2.selectbox("Tipo", options=list(mapa_categorias.keys()), key="sb_tipo")
        
        col3, col4 = st.columns(2)
        opcoes_categoria = list(mapa_categorias[tipo].keys())
        categoria = col3.selectbox("Categoria", options=opcoes_categoria, key="sb_categoria")
        
        opcoes_subcategoria = mapa_categorias[tipo][categoria]
        subcategoria = col4.selectbox("Subcategoria", options=opcoes_subcategoria, key="sb_subcategoria")
        
        descricao = st.text_input("Descrição", placeholder="Ex: Jantar no Outback")
        
        col5, col6, col7 = st.columns(3)
        valor = col5.number_input("Valor (R$)", min_value=0.01, format="%.2f", step=10.00)
        
        with col6:
            metodo_pagamento = st.selectbox(
                "Forma de Pagamento", 
                ["PIX", "Transferência Bancária", "Cartão de Débito", "Boleto", "Dinheiro", "Cheque", "Vale Alimentação"],
                key="sb_metodo"
            )
            bancos_disponiveis = ["Nubank", "Sicredi", "Sicoob", "BNDES", "Banco do Brasil", "Bradesco", "Itaú", "Santander", "Caixa", "Inter", "C6 Bank", "Investimento"]
            
            if metodo_pagamento in ["PIX", "Transferência Bancária", "Cartão de Débito", "Boleto"]:
                conta_final = st.selectbox("Instituição Financeira", bancos_disponiveis, key="sb_instituicao")
            elif metodo_pagamento == "Vale Alimentação":
                conta_final = "Vale Alimentação"
            else:
                conta_final = "Carteira"

        status = col7.selectbox("Status", ["Pago/Recebido", "Pendente", "Agendado"], key="sb_status")
        
        st.markdown("---")
        
        if st.button("💾 Salvar Lançamento", type="primary", use_container_width=True):
            novo_dado = {
                "data": data.strftime("%Y-%m-%d"),
                "tipo": tipo,
                "categoria": categoria,
                "subcategoria": subcategoria,
                "descricao": descricao,
                "valor": valor,
                "conta": conta_final,
                "forma_pagamento": metodo_pagamento,
                "status": status
            }
            salvar_lancamento(user_id, novo_dado)
            st.toast("Lançamento salvo com sucesso!", icon="✅")

    # ===================================================
    # ABA 2: GERENCIAR (NOVA VERSÃO COM FILTROS E BULK DELETE)
    # ===================================================
    with tab_gerenciar:
        st.header("🗂️ Gerenciamento Avançado")
        
        df = carregar_dados(user_id)
        
        if df.empty:
            st.info("Nenhum lançamento encontrado.")
        else:
            # Prepara dados para filtros
            df['data'] = pd.to_datetime(df['data'])
            df['Ano'] = df['data'].dt.year
            df['Mes'] = df['data'].dt.month
            df['Dia'] = df['data'].dt.day
            
            # --- ÁREA DE FILTROS ---
            with st.expander("🔍 Filtros de Visualização", expanded=True):
                # Linha 1: Filtros de Tempo
                c_ano, c_mes, c_dia = st.columns(3)
                
                anos_disp = sorted(df['Ano'].unique())
                sel_ano = c_ano.selectbox("Ano", ["Todos"] + list(map(str, anos_disp)))
                
                sel_mes = "Todos"
                sel_dia = "Todos"
                
                if sel_ano != "Todos":
                    meses_disp = sorted(df[df['Ano'] == int(sel_ano)]['Mes'].unique())
                    sel_mes = c_mes.selectbox("Mês", ["Todos"] + list(map(str, meses_disp)))
                    
                    if sel_mes != "Todos":
                        dias_disp = sorted(df[(df['Ano'] == int(sel_ano)) & (df['Mes'] == int(sel_mes))]['Dia'].unique())
                        sel_dia = c_dia.selectbox("Dia", ["Todos"] + list(map(str, dias_disp)))

                st.divider()
                
                # Linha 2: Filtros de Categoria
                c_tipo, c_cat, c_sub = st.columns(3)
                
                sel_tipo = c_tipo.selectbox("Tipo", ["Todos", "Receita", "Despesa"])
                
                sel_cat = "Todos"
                sel_sub = "Todos"
                
                if sel_tipo != "Todos":
                    cats_disp = sorted(df[df['tipo'] == sel_tipo]['categoria'].unique())
                    sel_cat = c_cat.selectbox("Categoria", ["Todos"] + cats_disp)
                    
                    if sel_cat != "Todos":
                        subs_disp = sorted(df[(df['tipo'] == sel_tipo) & (df['categoria'] == sel_cat)]['subcategoria'].unique())
                        sel_sub = c_sub.selectbox("Subcategoria", ["Todos"] + subs_disp)

            # --- APLICAÇÃO DOS FILTROS ---
            df_filtro = df.copy()
            
            if sel_ano != "Todos": df_filtro = df_filtro[df_filtro['Ano'] == int(sel_ano)]
            if sel_mes != "Todos": df_filtro = df_filtro[df_filtro['Mes'] == int(sel_mes)]
            if sel_dia != "Todos": df_filtro = df_filtro[df_filtro['Dia'] == int(sel_dia)]
            
            if sel_tipo != "Todos": df_filtro = df_filtro[df_filtro['tipo'] == sel_tipo]
            if sel_cat != "Todos": df_filtro = df_filtro[df_filtro['categoria'] == sel_cat]
            if sel_sub != "Todos": df_filtro = df_filtro[df_filtro['subcategoria'] == sel_sub]

            # --- TABELA INTERATIVA (DATA EDITOR) ---
            st.markdown(f"### Resultados: {len(df_filtro)} lançamentos")
            
            # Adiciona coluna de seleção para o usuário interagir
            df_filtro.insert(0, "Selecionar", False)
            
            # Configuração das colunas para o editor
            column_config = {
                "Selecionar": st.column_config.CheckboxColumn("✅", help="Selecione para excluir", default=False),
                "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                "Ano": None, "Mes": None, "Dia": None, "user_id": None # Esconde colunas auxiliares
            }
            
            # Tabela editável
            df_editado = st.data_editor(
                df_filtro,
                column_config=column_config,
                hide_index=True,
                use_container_width=True,
                disabled=["id", "data", "tipo", "categoria", "subcategoria", "descricao", "valor", "conta", "forma_pagamento", "status"] # Trava edição direta, libera só checkbox
            )
            
            # --- AÇÃO EM MASSA: EXCLUIR ---
            itens_selecionados = df_editado[df_editado["Selecionar"] == True]
            
            if not itens_selecionados.empty:
                qtd_sel = len(itens_selecionados)
                total_sel = itens_selecionados['valor'].sum()
                
                st.warning(f"⚠️ Você selecionou **{qtd_sel} itens** somando **R$ {total_sel:,.2f}**.")
                
                col_del_btn, _ = st.columns([1, 4])
                if col_del_btn.button(f"🗑️ Excluir {qtd_sel} Lançamentos Selecionados", type="primary"):
                    sucessos = 0
                    with st.status("Processando exclusões...", expanded=True) as status:
                        for index, row in itens_selecionados.iterrows():
                            st.write(f"Excluindo: {row['descricao']}...")
                            if excluir_lancamento(user_id, int(row['id'])):
                                sucessos += 1
                        status.update(label="Concluído!", state="complete", expanded=False)
                    
                    if sucessos > 0:
                        st.success(f"{sucessos} itens excluídos com sucesso!")
                        st.rerun()
            
            # --- EDIÇÃO INDIVIDUAL (PRESERVADA E MELHORADA) ---
            st.divider()
            st.caption("Para editar um item específico (mudar valor, data, etc.), selecione-o abaixo:")
            
            opcoes_editar = df_filtro.apply(lambda row: f"ID: {row['id']} | {row['data'].strftime('%d/%m/%Y')} | {row['descricao']} | R$ {row['valor']:.2f}", axis=1)
            escolha_editar = st.selectbox("Selecione para editar:", options=["Selecione..."] + list(opcoes_editar))
            
            if escolha_editar != "Selecione...":
                id_edit = int(escolha_editar.split(" |")[0].replace("ID: ", ""))
                dados_atuais = df[df['id'] == id_edit].iloc[0]
                
                with st.form(f"form_edit_{id_edit}"):
                    st.write(f"**Editando:** {dados_atuais['descricao']}")
                    ec1, ec2 = st.columns(2)
                    e_data = ec1.date_input("Data", value=dados_atuais['data'])
                    e_val = ec2.number_input("Valor", value=float(dados_atuais['valor']), min_value=0.01)
                    
                    e_desc = st.text_input("Descrição", value=dados_atuais['descricao'])
                    
                    ec3, ec4 = st.columns(2)
                    e_cat = ec3.selectbox("Categoria", list(CATEGORIAS[dados_atuais['tipo']].keys()), index=list(CATEGORIAS[dados_atuais['tipo']].keys()).index(dados_atuais['categoria']) if dados_atuais['categoria'] in CATEGORIAS[dados_atuais['tipo']] else 0)
                    e_status = ec4.selectbox("Status", ["Pago/Recebido", "Pendente", "Agendado"], index=["Pago/Recebido", "Pendente", "Agendado"].index(dados_atuais['status']))

                    if st.form_submit_button("💾 Salvar Alterações"):
                        novos_dados = {
                            "data": e_data, "tipo": dados_atuais['tipo'], "categoria": e_cat, 
                            "subcategoria": dados_atuais['subcategoria'], # Mantém subcategoria simples por enquanto
                            "descricao": e_desc, "valor": e_val, "conta": dados_atuais['conta'], 
                            "forma_pagamento": dados_atuais['forma_pagamento'], "status": e_status
                        }
                        atualizar_lancamento(user_id, id_edit, novos_dados)
                        st.success("Atualizado!")
                        st.rerun()