import streamlit as st
import pandas as pd
from datetime import datetime, date
from modules.database import salvar_cartao, carregar_cartoes, excluir_cartao, salvar_compra_credito, carregar_fatura, atualizar_item_fatura
from modules.constants import LISTA_CATEGORIAS_DESPESA

def show_cartoes():
    if 'user_id' not in st.session_state: return
    user_id = st.session_state['user_id']
    
    st.header("💳 Gestão de Cartões de Crédito")
    
    tab_fatura, tab_compra, tab_gerenciar = st.tabs(["📄 Ver Faturas", "🛍️ Nova Compra", "⚙️ Cadastrar Cartão"])
    
    df_cartoes = carregar_cartoes(user_id)

    # ABA 1: VER FATURAS (Com Edição)
    with tab_fatura:
        if df_cartoes.empty:
            st.warning("Cadastre um cartão primeiro.")
        else:
            c1, c2 = st.columns(2)
            cartao_selecionado = c1.selectbox("Selecione o Cartão", df_cartoes['nome_cartao'].tolist())
            id_cartao = int(df_cartoes[df_cartoes['nome_cartao'] == cartao_selecionado]['id'].values[0])
            
            mes_atual = date.today().replace(day=1)
            opcoes_meses = [mes_atual.replace(month=m) for m in range(1, 13)]
            try: opcoes_meses += [mes_atual.replace(year=mes_atual.year+1, month=m) for m in range(1, 13)]
            except: pass
            
            mes_escolhido = c2.selectbox("Mês da Fatura", opcoes_meses, format_func=lambda x: x.strftime("%B/%Y"), index=mes_atual.month - 1)
            
            df_fatura = carregar_fatura(user_id, id_cartao, mes_escolhido)
            st.divider()
            
            if df_fatura.empty:
                st.info(f"Fatura vazia.")
            else:
                total_fatura = df_fatura['valor_parcela'].sum()
                st.metric(f"Total da Fatura", f"R$ {total_fatura:,.2f}")
                st.dataframe(df_fatura[['data_compra', 'descricao', 'parcela_numero', 'qtd_parcelas', 'valor_parcela']], use_container_width=True)
                
                # --- ÁREA DE EDIÇÃO DO ITEM ---
                st.markdown("### ✏️ Editar Item desta Fatura")
                opcoes_item = df_fatura.apply(lambda r: f"Item {r['id']} | {r['descricao']} - R$ {r['valor_parcela']:.2f}", axis=1)
                item_sel = st.selectbox("Selecione um item para corrigir:", ["Selecione..."] + list(opcoes_item))
                
                if item_sel != "Selecione...":
                    id_item = int(item_sel.split(" |")[0].replace("Item ", ""))
                    dados_item = df_fatura[df_fatura['id'] == id_item].iloc[0]
                    
                    with st.form(f"form_edit_item_{id_item}"):
                        st.caption("Nota: Alterar aqui afeta apenas ESTA parcela.")
                        ni_desc = st.text_input("Descrição", value=dados_item['descricao'])
                        c_val, c_dat = st.columns(2)
                        ni_valor = c_val.number_input("Valor da Parcela", value=float(dados_item['valor_parcela']))
                        ni_data = c_dat.date_input("Data Compra", value=pd.to_datetime(dados_item['data_compra']))
                        
                        if st.form_submit_button("Atualizar Item"):
                            atualizar_item_fatura(user_id, id_item, ni_desc, ni_valor, ni_data)
                            st.success("Item corrigido!")
                            st.rerun()

    # ABA 2: NOVA COMPRA (Igual)
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

    # ABA 3: GERENCIAR (Igual)
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