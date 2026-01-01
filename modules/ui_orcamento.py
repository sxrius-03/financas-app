import streamlit as st
import pandas as pd
from datetime import datetime, date
# ATENÇÃO: Verifique se carregar_reservas está exportado no seu database.py, senão adicione-o.
from modules.database import (
    carregar_dados, salvar_meta, carregar_metas, excluir_meta, 
    listar_meses_com_metas
)
# Tente importar listas de investimento, caso não existam, use listas genéricas
try:
    from modules.constants import LISTA_CATEGORIAS_DESPESA, LISTA_CATEGORIAS_INVESTIMENTO
except ImportError:
    from modules.constants import LISTA_CATEGORIAS_DESPESA
    LISTA_CATEGORIAS_INVESTIMENTO = ["Reserva de Emergência", "Aposentadoria", "Viagem", "Carro Novo"]

def show_orcamento():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']

    st.header("🎯 Gestão de Metas e Orçamento")

    # Layout de Abas atualizado
    tab_monitor, tab_mensal, tab_anual = st.tabs([
        "📊 Monitoramento", 
        "🗓️ Metas Mensais", 
        "📅 Metas Anuais"
    ])
    
    # ===================================================
    # ABA 1: MONITORAMENTO GERAL
    # ===================================================
    with tab_monitor:
        st.caption("Acompanhe o progresso das suas metas (Despesas e Reservas).")
        
        meses_com_metas = listar_meses_com_metas(user_id)
        
        if not meses_com_metas:
            st.warning("Nenhuma meta definida ainda.")
        else:
            # Filtro de Período
            mapa_meses = {0: "Anual", 1:"Jan", 2:"Fev", 3:"Mar", 4:"Abr", 5:"Mai", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Set", 10:"Out", 11:"Nov", 12:"Dez"}
            
            # Formata opções visualmente. Mes=0 indica meta anual.
            opcoes_formatadas = []
            dados_originais = []
            
            for m, a in meses_com_metas:
                lbl = f"Ano {a}" if m == 0 else f"{mapa_meses[m]} / {a}"
                opcoes_formatadas.append(lbl)
                dados_originais.append((m, a))

            # Tenta selecionar o mês atual
            hj = date.today()
            lbl_atual = f"{mapa_meses[hj.month]} / {hj.year}"
            idx_padrao = opcoes_formatadas.index(lbl_atual) if lbl_atual in opcoes_formatadas else 0
            
            escolha = st.selectbox("📅 Selecione o Período:", opcoes_formatadas, index=idx_padrao)
            mes_sel, ano_sel = dados_originais[opcoes_formatadas.index(escolha)]
            
            st.divider()

            # --- Carregamento de Dados ---
            df_metas = carregar_metas(user_id, mes=mes_sel, ano=ano_sel)
            df_lancamentos = carregar_dados(user_id) # Assume que traz tudo (Despesas e Receitas/Investimentos)
            
            # Garante datetime
            if not df_lancamentos.empty:
                df_lancamentos['data'] = pd.to_datetime(df_lancamentos['data'])

            # Função auxiliar para calcular progresso
            def calcular_progresso(df_metas_filtrada, tipo_meta):
                if df_metas_filtrada.empty: return pd.DataFrame()

                # Filtra lançamentos pelo período
                mask_periodo = (df_lancamentos['data'].dt.year == ano_sel)
                if mes_sel != 0: # Se não for anual, filtra mês
                    mask_periodo = mask_periodo & (df_lancamentos['data'].dt.month == mes_sel)
                
                df_periodo = df_lancamentos[mask_periodo]

                # Define filtro por tipo (Despesa vs Reserva/Investimento)
                if tipo_meta == 'Despesa':
                    df_filtrado = df_periodo[df_periodo['tipo'] == 'Despesa']
                else:
                    # Ajuste conforme seu banco de dados (ex: 'Investimento' ou 'Transferência')
                    df_filtrado = df_periodo[df_periodo['tipo'].isin(['Investimento', 'Reserva', 'Aplicação'])]

                gastos = df_filtrado.groupby('categoria')['valor'].sum().reset_index()
                
                merged = pd.merge(df_metas_filtrada, gastos, on='categoria', how='left')
                merged['valor'] = merged['valor'].fillna(0)
                
                # Lógica de Saldo/Progresso
                if tipo_meta == 'Despesa':
                    merged['Saldo'] = merged['valor_meta'] - merged['valor']
                    merged['Progresso'] = (merged['valor'] / merged['valor_meta']).clip(0, 1)
                else:
                    # Para reservas: Saldo é quanto falta para atingir a meta
                    merged['Saldo'] = merged['valor_meta'] - merged['valor']
                    # Progresso é quanto já guardou
                    merged['Progresso'] = (merged['valor'] / merged['valor_meta']).clip(0, 1)

                return merged

            # Separa metas de Despesa e Reserva (assumindo que você tem uma coluna 'tipo' na tabela metas ou deduz pela categoria)
            # Como o schema atual de 'metas' pode não ter 'tipo', vamos deduzir pelas listas de categorias
            
            # Identifica quais metas são de Investimento
            df_metas['tipo_meta'] = df_metas['categoria'].apply(lambda x: 'Reserva' if x in LISTA_CATEGORIAS_INVESTIMENTO else 'Despesa')
            
            metas_despesa = df_metas[df_metas['tipo_meta'] == 'Despesa']
            metas_reserva = df_metas[df_metas['tipo_meta'] == 'Reserva']

            # --- Exibição Despesas ---
            if not metas_despesa.empty:
                st.subheader("💸 Orçamento de Gastos")
                df_res_desp = calcular_progresso(metas_despesa, 'Despesa')
                
                st.dataframe(
                    df_res_desp[['categoria', 'valor_meta', 'valor', 'Saldo', 'Progresso']],
                    use_container_width=True,
                    column_config={
                        "valor_meta": st.column_config.NumberColumn("Limite", format="R$ %.2f"),
                        "valor": st.column_config.NumberColumn("Gasto", format="R$ %.2f"),
                        "Saldo": st.column_config.NumberColumn("Disponível", format="R$ %.2f"),
                        "Progresso": st.column_config.ProgressColumn("Consumo", format="%.0f%%", min_value=0, max_value=1),
                    },
                    hide_index=True
                )
                
                # Alertas de estouro
                for _, row in df_res_desp[df_res_desp['valor'] > df_res_desp['valor_meta']].iterrows():
                    st.error(f"🚨 Você estourou **{row['categoria']}** em R$ {abs(row['Saldo']):.2f}!")

            # --- Exibição Reservas ---
            if not metas_reserva.empty:
                st.subheader("💰 Metas de Economia/Reserva")
                df_res_invest = calcular_progresso(metas_reserva, 'Reserva')
                
                st.dataframe(
                    df_res_invest[['categoria', 'valor_meta', 'valor', 'Saldo', 'Progresso']],
                    use_container_width=True,
                    column_config={
                        "valor_meta": st.column_config.NumberColumn("Meta", format="R$ %.2f"),
                        "valor": st.column_config.NumberColumn("Aportado", format="R$ %.2f"),
                        "Saldo": st.column_config.NumberColumn("Falta", format="R$ %.2f"),
                        "Progresso": st.column_config.ProgressColumn("Atingido", format="%.0f%%", min_value=0, max_value=1),
                    },
                    hide_index=True
                )

    # ===================================================
    # FUNÇÃO AUXILIAR DE FORMULÁRIO (USADA EM MENSAL E ANUAL)
    # ===================================================
    def renderizar_gerenciador_metas(tipo_periodo="mensal"):
        """
        tipo_periodo: 'mensal' ou 'anual'
        """
        is_anual = (tipo_periodo == "anual")
        mes_fixo = 0 if is_anual else None
        
        # 1. Carregar metas existentes para edição
        # Se for anual, carrega metas com mes=0. Se mensal, carrega todas menos as 0.
        all_metas = carregar_metas(user_id)
        
        if is_anual:
            metas_filtradas = all_metas[all_metas['mes'] == 0]
            label_periodo = f"Meta para o Ano de {date.today().year}"
        else:
            metas_filtradas = all_metas[all_metas['mes'] != 0]
            label_periodo = "Meta para Mês/Ano Específico"

        # Criar lista de seleção para Edição
        opcoes_edicao = ["✨ Criar Nova Meta"]
        
        # Dicionário para mapear seleção -> dados
        mapa_dados = {}
        
        for idx, row in metas_filtradas.iterrows():
            if is_anual:
                lbl = f"{row['ano']} - {row['categoria']} (R$ {row['valor_meta']:.2f})"
            else:
                lbl = f"{row['mes']:02d}/{row['ano']} - {row['categoria']} (R$ {row['valor_meta']:.2f})"
            
            opcoes_edicao.append(lbl)
            mapa_dados[lbl] = row

        col_sel, col_del = st.columns([3, 1])
        with col_sel:
            selecao = st.selectbox(f"Selecione uma meta ({tipo_periodo}) para editar:", options=opcoes_edicao, key=f"sel_{tipo_periodo}")
        
        # Variáveis de controle do formulário
        modo_edicao = selecao != "✨ Criar Nova Meta"
        dados_edit = mapa_dados.get(selecao) if modo_edicao else None

        # Botão de excluir (só aparece se estiver editando)
        with col_del:
            st.write("") # Espaçamento
            st.write("") 
            if modo_edicao:
                if st.button("🗑️ Excluir", key=f"del_{tipo_periodo}", type="primary"):
                    # CORREÇÃO DO BUG AQUI: Convertendo para int() nativo
                    excluir_meta(
                        user_id, 
                        str(dados_edit['categoria']), 
                        int(dados_edit['mes']), 
                        int(dados_edit['ano'])
                    )
                    st.success("Meta excluída!")
                    st.rerun()

        st.divider()

        # Formulário Unificado
        with st.form(f"form_meta_{tipo_periodo}"):
            st.subheader(f"{'✏️ Editando' if modo_edicao else '➕ Nova'} Meta {tipo_periodo.capitalize()}")
            
            c1, c2, c3 = st.columns(3)
            
            # Campo 1: Categoria e Tipo
            tipo_lancamento = c1.radio("Tipo", ["Despesa", "Reserva/Investimento"], 
                                     index=0 if not modo_edicao or dados_edit['categoria'] in LISTA_CATEGORIAS_DESPESA else 1)
            
            lista_cats = LISTA_CATEGORIAS_DESPESA if tipo_lancamento == "Despesa" else LISTA_CATEGORIAS_INVESTIMENTO
            
            # Tenta encontrar o index da categoria atual
            try:
                idx_cat = lista_cats.index(dados_edit['categoria']) if modo_edicao and dados_edit['categoria'] in lista_cats else 0
            except:
                idx_cat = 0

            cat_selecionada = c1.selectbox("Categoria", options=lista_cats, index=idx_cat)

            # Campo 2: Data (Mês/Ano)
            if is_anual:
                val_ano = int(dados_edit['ano']) if modo_edicao else date.today().year
                ano_form = c2.number_input("Ano de Referência", min_value=2023, max_value=2030, value=val_ano)
                mes_form = 0 # 0 representa Anual no banco
            else:
                val_mes = int(dados_edit['mes']) if modo_edicao else date.today().month
                val_ano = int(dados_edit['ano']) if modo_edicao else date.today().year
                
                mes_form = c2.selectbox("Mês", range(1, 13), index=val_mes-1)
                ano_form = c3.number_input("Ano", min_value=2023, max_value=2030, value=val_ano)

            # Campo 3: Valor
            val_meta = float(dados_edit['valor_meta']) if modo_edicao else 0.0
            valor_meta = st.number_input("Valor da Meta (R$)", min_value=0.0, value=val_meta, step=50.0)

            submitted = st.form_submit_button("💾 Salvar Meta")
            
            if submitted:
                if valor_meta > 0:
                    # Se estiver editando, tecnicamente precisaríamos deletar a antiga se a chave (cat/mes/ano) mudou, 
                    # mas o 'salvar_meta' geralmente faz um INSERT ou UPDATE. 
                    # Como simplificação, se mudou a chave primária, excluímos a anterior.
                    if modo_edicao:
                        # Verifica se mudou a chave composta
                        mudou_chave = (dados_edit['categoria'] != cat_selecionada) or \
                                      (int(dados_edit['mes']) != mes_form) or \
                                      (int(dados_edit['ano']) != ano_form)
                        
                        if mudou_chave:
                             excluir_meta(user_id, str(dados_edit['categoria']), int(dados_edit['mes']), int(dados_edit['ano']))
                    
                    # Salva (se já existir com mesma chave, seu database deve fazer update, senão insert)
                    salvar_meta(user_id, cat_selecionada, valor_meta, mes_form, ano_form)
                    st.success(f"Meta de {cat_selecionada} salva com sucesso!")
                    st.rerun()
                else:
                    st.warning("O valor deve ser maior que zero.")

    # ===================================================
    # ABA 2: METAS MENSAIS
    # ===================================================
    with tab_mensal:
        renderizar_gerenciador_metas("mensal")

    # ===================================================
    # ABA 3: METAS ANUAIS
    # ===================================================
    with tab_anual:
        st.info("ℹ️ Metas anuais são úteis para grandes objetivos (ex: Viagem de fim de ano, IPVA, Reserva Total).")
        renderizar_gerenciador_metas("anual")