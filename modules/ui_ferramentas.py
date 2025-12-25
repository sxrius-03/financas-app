<<<<<<< HEAD
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

def show_ferramentas():
    st.header("🧰 Ferramentas Financeiras")
    
    tab_fire, tab_finan = st.tabs(["🔥 Simulador FIRE", "🏠 Calculadora Financiamento"])

    # --- SIMULADOR FIRE (Independência Financeira) ---
    with tab_fire:
        st.subheader("Quanto falta para sua liberdade?")
        
        c1, c2, c3 = st.columns(3)
        patrimonio_atual = c1.number_input("Patrimônio Atual (R$)", value=0.0, step=1000.0)
        aporte_mensal = c2.number_input("Aporte Mensal (R$)", value=1000.0, step=100.0)
        custo_vida = c3.number_input("Custo de Vida Mensal Desejado (R$)", value=5000.0)
        
        c4, c5 = st.columns(2)
        taxa_anual = c4.number_input("Rentabilidade Anual Esperada (%)", value=10.0) / 100
        taxa_retirada = c5.number_input("Taxa Segura de Retirada (SWR)", value=4.0, help="Padrão é 4%") / 100
        
        st.divider()
        
        # Cálculos
        numero_magico = (custo_vida * 12) / taxa_retirada
        taxa_mensal = (1 + taxa_anual)**(1/12) - 1
        
        if st.button("Simular Futuro", type="primary"):
            st.metric("Seu Número Mágico (Meta)", f"R$ {numero_magico:,.2f}")
            
            saldo = patrimonio_atual
            meses = 0
            dados_grafico = []
            
            # Projeção de até 50 anos
            while saldo < numero_magico and meses < 600:
                rendimento = saldo * taxa_mensal
                saldo += rendimento + aporte_mensal
                meses += 1
                if meses % 12 == 0: # Grava ano a ano p/ grafico nao ficar pesado
                    dados_grafico.append({"Ano": meses/12, "Saldo": saldo, "Meta": numero_magico})
            
            anos = meses / 12
            if saldo >= numero_magico:
                st.success(f"🎉 Você atingirá a liberdade financeira em **{anos:.1f} anos**!")
                
                df_proj = pd.DataFrame(dados_grafico)
                fig = px.line(df_proj, x="Ano", y=["Saldo", "Meta"], title="Evolução Patrimonial")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Com esses parâmetros, vai demorar mais de 50 anos.")

    # --- CALCULADORA FINANCIAMENTO (Amortização) ---
    with tab_finan:
        st.subheader("Simulador de Dívida (Tabela SAC)")
        
        val_divida = st.number_input("Valor do Empréstimo", value=200000.0)
        prazo_anos = st.number_input("Prazo (Anos)", value=30)
        juros_anual = st.number_input("Juros Anuais (%)", value=9.0)
        
        amort_extra = st.number_input("Amortização Extra Mensal (Opcional)", value=0.0)
        
        if st.button("Calcular Economia"):
            meses = prazo_anos * 12
            taxa_mensal = (juros_anual / 100) / 12
            amortizacao_fixa = val_divida / meses
            
            saldo_devedor = val_divida
            total_pago = 0
            total_juros = 0
            evolucao = []
            
            mes_atual = 1
            while saldo_devedor > 0:
                juros = saldo_devedor * taxa_mensal
                parcela = amortizacao_fixa + juros
                
                # Abate parcela normal
                saldo_devedor -= amortizacao_fixa
                total_pago += parcela
                total_juros += juros
                
                # Amortização Extra
                if amort_extra > 0 and saldo_devedor > 0:
                    abatimento = min(amort_extra, saldo_devedor)
                    saldo_devedor -= abatimento
                    total_pago += abatimento
                
                evolucao.append({"Mês": mes_atual, "Saldo Devedor": max(0, saldo_devedor)})
                mes_atual += 1
                
                if saldo_devedor <= 0: break
            
            tempo_reduzido = (prazo_anos * 12) - (mes_atual - 1)
            
            col_a, col_b = st.columns(2)
            col_a.metric("Total Pago", f"R$ {total_pago:,.2f}")
            col_a.metric("Total Juros", f"R$ {total_juros:,.2f}")
            col_b.metric("Tempo Total", f"{(mes_atual-1)/12:.1f} anos")
            if amort_extra > 0:
                col_b.success(f"Você economizou {tempo_reduzido} meses pagando extra!")
            
=======
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

def show_ferramentas():
    st.header("🧰 Ferramentas Financeiras")
    
    tab_fire, tab_finan = st.tabs(["🔥 Simulador FIRE", "🏠 Calculadora Financiamento"])

    # --- SIMULADOR FIRE (Independência Financeira) ---
    with tab_fire:
        st.subheader("Quanto falta para sua liberdade?")
        
        c1, c2, c3 = st.columns(3)
        patrimonio_atual = c1.number_input("Patrimônio Atual (R$)", value=0.0, step=1000.0)
        aporte_mensal = c2.number_input("Aporte Mensal (R$)", value=1000.0, step=100.0)
        custo_vida = c3.number_input("Custo de Vida Mensal Desejado (R$)", value=5000.0)
        
        c4, c5 = st.columns(2)
        taxa_anual = c4.number_input("Rentabilidade Anual Esperada (%)", value=10.0) / 100
        taxa_retirada = c5.number_input("Taxa Segura de Retirada (SWR)", value=4.0, help="Padrão é 4%") / 100
        
        st.divider()
        
        # Cálculos
        numero_magico = (custo_vida * 12) / taxa_retirada
        taxa_mensal = (1 + taxa_anual)**(1/12) - 1
        
        if st.button("Simular Futuro", type="primary"):
            st.metric("Seu Número Mágico (Meta)", f"R$ {numero_magico:,.2f}")
            
            saldo = patrimonio_atual
            meses = 0
            dados_grafico = []
            
            # Projeção de até 50 anos
            while saldo < numero_magico and meses < 600:
                rendimento = saldo * taxa_mensal
                saldo += rendimento + aporte_mensal
                meses += 1
                if meses % 12 == 0: # Grava ano a ano p/ grafico nao ficar pesado
                    dados_grafico.append({"Ano": meses/12, "Saldo": saldo, "Meta": numero_magico})
            
            anos = meses / 12
            if saldo >= numero_magico:
                st.success(f"🎉 Você atingirá a liberdade financeira em **{anos:.1f} anos**!")
                
                df_proj = pd.DataFrame(dados_grafico)
                fig = px.line(df_proj, x="Ano", y=["Saldo", "Meta"], title="Evolução Patrimonial")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Com esses parâmetros, vai demorar mais de 50 anos.")

    # --- CALCULADORA FINANCIAMENTO (Amortização) ---
    with tab_finan:
        st.subheader("Simulador de Dívida (Tabela SAC)")
        
        val_divida = st.number_input("Valor do Empréstimo", value=200000.0)
        prazo_anos = st.number_input("Prazo (Anos)", value=30)
        juros_anual = st.number_input("Juros Anuais (%)", value=9.0)
        
        amort_extra = st.number_input("Amortização Extra Mensal (Opcional)", value=0.0)
        
        if st.button("Calcular Economia"):
            meses = prazo_anos * 12
            taxa_mensal = (juros_anual / 100) / 12
            amortizacao_fixa = val_divida / meses
            
            saldo_devedor = val_divida
            total_pago = 0
            total_juros = 0
            evolucao = []
            
            mes_atual = 1
            while saldo_devedor > 0:
                juros = saldo_devedor * taxa_mensal
                parcela = amortizacao_fixa + juros
                
                # Abate parcela normal
                saldo_devedor -= amortizacao_fixa
                total_pago += parcela
                total_juros += juros
                
                # Amortização Extra
                if amort_extra > 0 and saldo_devedor > 0:
                    abatimento = min(amort_extra, saldo_devedor)
                    saldo_devedor -= abatimento
                    total_pago += abatimento
                
                evolucao.append({"Mês": mes_atual, "Saldo Devedor": max(0, saldo_devedor)})
                mes_atual += 1
                
                if saldo_devedor <= 0: break
            
            tempo_reduzido = (prazo_anos * 12) - (mes_atual - 1)
            
            col_a, col_b = st.columns(2)
            col_a.metric("Total Pago", f"R$ {total_pago:,.2f}")
            col_a.metric("Total Juros", f"R$ {total_juros:,.2f}")
            col_b.metric("Tempo Total", f"{(mes_atual-1)/12:.1f} anos")
            if amort_extra > 0:
                col_b.success(f"Você economizou {tempo_reduzido} meses pagando extra!")
            
>>>>>>> 1fad148ea27bba7506d08963bb63dfb23e82c4e5
            st.line_chart(pd.DataFrame(evolucao).set_index("Mês"))