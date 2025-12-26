import streamlit as st
from datetime import date, timedelta
from modules.database import carregar_cartoes, obter_status_fatura, buscar_pendencias_proximas

def verificar_notificacoes(user_id):
    """
    Retorna uma lista de tuplas: (tipo_alerta, mensagem).
    Tipos: 'error' (Urgente), 'warning' (Atenção), 'info' (Informativo).
    """
    alertas = []
    hoje = date.today()
    amanha = hoje + timedelta(days=1)
    
    # 1. VERIFICAR LANÇAMENTOS (Agendados/Pendentes)
    # Usa a função nova que adicionamos no database.py
    df_pend = buscar_pendencias_proximas(user_id)
    if not df_pend.empty:
        for _, row in df_pend.iterrows():
            data_lanc = row['data'].date()
            if data_lanc == hoje:
                alertas.append(("warning", f"🔔 **Hoje:** {row['descricao']} (R$ {row['valor']:.2f}) na conta {row['conta']}."))
            elif data_lanc == amanha:
                alertas.append(("info", f"📅 **Amanhã:** {row['descricao']} (R$ {row['valor']:.2f}) vence ou está agendado."))

    # 2. VERIFICAR FATURAS DE CARTÃO
    df_cartoes = carregar_cartoes(user_id)
    if not df_cartoes.empty:
        for _, cartao in df_cartoes.iterrows():
            cartao_id = int(cartao['id'])
            dia_venc = int(cartao['dia_vencimento'])
            nome = cartao['nome_cartao']
            
            # Define a data de vencimento deste mês
            try:
                data_vencimento_atual = hoje.replace(day=dia_venc)
            except ValueError:
                # Caso vença dia 31 e o mês só tenha 30
                data_vencimento_atual = hoje.replace(day=28) 

            # Se o vencimento deste mês já passou (ex: hoje 15, venceu 10),
            # olhamos para o mês que vem.
            if data_vencimento_atual < hoje:
                # Mas antes, checamos se a fatura passada ficou em aberto (Atrasada!)
                mes_ref_passado = data_vencimento_atual.replace(day=1)
                status_passado = obter_status_fatura(user_id, cartao_id, mes_ref_passado)
                if not (status_passado and status_passado['status'] in ['Paga', 'Paga Externo']):
                     alertas.append(("error", f"🔥 **ATRASADO:** A fatura do {nome} venceu dia {data_vencimento_atual.strftime('%d/%m')}!"))
                
                # Avança para o próximo mês
                mes_proximo = (hoje.replace(day=1) + timedelta(days=32)).replace(day=dia_venc)
                data_vencimento_atual = mes_proximo

            # Data base para buscar no banco (Sempre dia 1 do mês do vencimento)
            mes_ref = data_vencimento_atual.replace(day=1)
            
            # Verifica se já pagou a fatura vigente
            status_info = obter_status_fatura(user_id, cartao_id, mes_ref)
            ja_pagou = status_info and status_info['status'] in ['Paga', 'Paga Externo']
            
            if not ja_pagou:
                dias_para_vencer = (data_vencimento_atual - hoje).days
                
                # Regras de Notificação:
                if dias_para_vencer <= 3:
                    alertas.append(("error", f"🚨 **Urgente:** Fatura do {nome} vence em {dias_para_vencer} dias (Dia {dia_venc})!"))
                elif dias_para_vencer <= 10:
                    alertas.append(("info", f"💳 Fatura do {nome} próxima do vencimento ({dia_venc}). Já fechou?"))

    return alertas

def exibir_notificacoes_na_sidebar(user_id):
    """Função visual para chamar no main.py"""
    alertas = verificar_notificacoes(user_id)
    
    if alertas:
        st.sidebar.divider()
        st.sidebar.subheader(f"🔔 Notificações ({len(alertas)})")
        for tipo, msg in alertas:
            if tipo == "error":
                st.sidebar.error(msg, icon="🚨")
            elif tipo == "warning":
                st.sidebar.warning(msg, icon="⚠️")
            else:
                st.sidebar.info(msg, icon="ℹ️")