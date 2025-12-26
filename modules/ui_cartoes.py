import streamlit as st
import pandas as pd
from datetime import datetime, date
from modules.database import (
    salvar_cartao, carregar_cartoes, excluir_cartao, 
    salvar_compra_credito, carregar_fatura, atualizar_item_fatura,
    registrar_pagamento_fatura, obter_status_fatura, salvar_lancamento
)
from modules.constants import LISTA_CATEGORIAS_DESPESA

def show_cartoes():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']
    
    st.header("💳 Gestão de Cartões de Crédito")
    
    tab_fatura, tab_compra, tab_gerenciar = st.tabs(["📄 Ver Faturas", "🛍️ Nova Compra", "⚙️ Cadastrar Cartão"])
    
    df_cartoes = carregar_cartoes(user_id)

    # --- ABA 1: VER FATURAS E PAGAR ---
    with tab_fatura:
        if df_cartoes.empty:
            st.warning("Cadastre um cartão primeiro.")
        else:
            c1, c2 = st.columns(2)
            cartao_selecionado = c1.selectbox("Selecione o Cartão", df_cartoes['nome_cartao'].tolist())
            
            # Converte ID para int nativo
            id_raw = df_cartoes[df_cartoes['nome_cartao'] == cartao_selecionado]['id'].values[0]
            id_cartao = int(id_raw)
            
            # Filtro de Mês
            mes_atual = date.today().replace(day=1)
            opcoes_meses = [mes_atual.replace(month=m) for m in range(1, 13)]
            try: opcoes_meses += [mes_atual.replace(year=mes_atual.year+1, month=m) for m in range(1, 13)]
            except: pass
            
            idx_mes_atual = 0
            for i, m in enumerate(opcoes_meses):
                if m.month == mes_atual.month and m.year == mes_atual.year:
                    idx_mes_atual = i
                    break

            mes_escolhido = c2.selectbox(
                "Mês da Fatura", 
                opcoes_meses, 
                format_func=lambda x: x.strftime("%B/%Y"),
                index=idx_mes_atual
            )
            
            # Carregar Itens e Status
            df_fatura = carregar_fatura(user_id, id_cartao, mes_escolhido)
            status_info = obter_status_fatura(user_id, id_cartao, mes_escolhido)
            
            st.divider()
            
            if df_fatura.empty:
                st.info(f"Fatura vazia para este mês.")
            else:
                # --- CORREÇÃO DO ERRO AQUI ---
                # Convertemos explicitamente para float nativo do Python
                total_fatura = float(df_fatura['valor_parcela'].sum())
                
                # --- CABEÇALHO DA FATURA ---
                col_kpi1, col_kpi2, col_kpi3 = st.columns([2, 2, 3])
                col_kpi1.metric("Total da Fatura", f"R$ {total_fatura:,.2f}")
                
                if status_info and status_info['status'] in ['Paga', 'Paga Externo']:
                    col_kpi2.success(f"STATUS: {status_info['status'].upper()}")
                    if status_info['data']:
                        data_pg = datetime.strptime(str(status_info['data']), "%Y-%m-%d").strftime("%d/%m/%Y")
                        col_kpi3.caption(f"Pago em: {data_pg} | Valor: R$ {status_info['valor']:,.2f}")
                else:
                    if mes_escolhido < mes_atual:
                        col_kpi2.error("STATUS: PENDENTE (ATRASADA?)")
                    else:
                        col_kpi2.warning("STATUS: EM ABERTO")
                    
                    with col_kpi3:
                        with st.expander("💸 Opções de Pagamento"):
                            tab_pagar_sis, tab_pagar_ext = st.tabs(["Lançar no Caixa", "Já paguei antes"])
                            
                            with tab_pagar_sis:
                                with st.form(f"form_pagar_{id_cartao}"):
                                    st.write("Isso criará uma DESPESA no sistema.")
                                    conta_pag = st.selectbox("Conta de Saída", ["Nubank", "Bradesco", "Itaú", "Santander", "Caixa", "Inter", "Carteira"])
                                    data_pag = st.date_input("Data do Pagamento", date.today())
                                    if st.form_submit_button("Confirmar Pagamento"):
                                        dados_lanc = {
                                            "data": data_pag,
                                            "tipo": "Despesa",
                                            "categoria": "Financeiro",
                                            "subcategoria": "Pagamento de Fatura",
                                            "descricao": f"Fatura {cartao_selecionado} - {mes_escolhido.strftime('%m/%Y')}",
                                            "valor": total_fatura, # Agora é float puro, sem numpy
                                            "conta": conta_pag,
                                            "forma_pagamento": "Boleto/Automático",
                                            "status": "Pago/Recebido"
                                        }
                                        salvar_lancamento(user_id, dados_lanc)
                                        registrar_pagamento_fatura(user_id, id_cartao, mes_escolhido, "Paga", total_fatura, data_pag)
                                        st.success("Fatura paga e saldo atualizado!")
                                        st.rerun()

                            with tab_pagar_ext:
                                if st.button("Marcar como Paga (Sem alterar saldo)"):
                                    registrar_pagamento_fatura(user_id, id_cartao, mes_escolhido, "Paga Externo", total_fatura, date.today())
                                    st.success("Status atualizado.")
                                    st.rerun()

                st.markdown("---")
                st.dataframe(df_fatura[['data_compra', 'descricao', 'parcela_numero', 'qtd_parcelas', 'valor_parcela']], use_container_width=True)
                
                if not (status_info and status_info['status'] in ['Paga', 'Paga Externo']):
                    with st.expander("✏️ Editar Item desta Fatura"):
                        opcoes_item = df_fatura.apply(lambda r: f"Item {r['id']} | {r['descricao']} - R$ {r['valor_parcela']:.2f}", axis=1)
                        item_sel = st.selectbox("Selecione para corrigir:", ["Selecione..."] + list(opcoes_item))
                        
                        if item_sel != "Selecione...":
                            id_item = int(item_sel.split(" |")[0].replace("Item ", ""))
                            dados_item = df_fatura[df_fatura['id'] == id_item].iloc[0]
                            
                            with st.form(f"form_edit_item_{id_item}"):
                                ni_desc = st.text_input("Descrição", value=dados_item['descricao'])
                                c_val, c_dat = st.columns(2)
                                ni_valor = c_val.number_input("Valor da Parcela", value=float(dados_item['valor_parcela']))
                                ni_data = c_dat.date_input("Data Compra", value=pd.to_datetime(dados_item['data_compra']))
                                
                                if st.form_submit_button("Atualizar Item"):
                                    atualizar_item_fatura(user_id, id_item, ni_desc, ni_valor, ni_data)
                                    st.success("Item corrigido!")
                                    st.rerun()

    # --- ABA 2: NOVA COMPRA (Igual) ---
    with tab_compra:
        st.subheader("Registrar Gasto no Crédito")
        if not df_cartoes.empty:
            with st.form("form_compra_credito"):
                c1, c2 = st.columns(2)
                cartao_nome = c1.selectbox("Cartão Usado", df_cartoes['nome_cartao'].tolist())
                data_compra = c2.date_input("Data da Compra", date.today())
                desc = st.text_input("Descrição")
                cat = st.selectbox("Categoria", options=LISTA_CATEGORIAS_DESPESA)
                c3, c4 = st.columns(2)
                valor_total = c3.number_input("Valor TOTAL", min_value=0.01)
                parcelas = c4.number_input("Parcelas", min_value=1, step=1, value=1)
                
                if st.form_submit_button("Lançar"):
                    info_cartao = df_cartoes[df_cartoes['nome_cartao'] == cartao_nome].iloc[0]
                    salvar_compra_credito(user_id, int(info_cartao['id']), data_compra, desc, cat, valor_total, int(parcelas), int(info_cartao['dia_fechamento']))
                    st.success("Lançado!")

    # --- ABA 3: GERENCIAR (Igual) ---
    with tab_gerenciar:
        st.subheader("Cadastrar Novo Cartão")
        with st.form("form_novo_cartao"):
            nome = st.text_input("Apelido do Cartão")
            c1, c2 = st.columns(2)
            fechamento = c1.number_input("Dia Fechamento", 1, 31, 1)
            vencimento = c2.number_input("Dia Vencimento", 1, 31, 10)
            if st.form_submit_button("Salvar Cartão"):
                salvar_cartao(user_id, nome, fechamento, vencimento)
                st.success("Cartão cadastrado!")
                st.rerun()
        if not df_cartoes.empty:
            st.divider()
            cartao_del = st.selectbox("Excluir Cartão", df_cartoes['nome_cartao'].tolist(), key="del_cartao")
            if st.button("🗑️ Excluir Selecionado"):
                id_del = df_cartoes[df_cartoes['nome_cartao'] == cartao_del]['id'].values[0]
                excluir_cartao(user_id, int(id_del))
                st.rerun()