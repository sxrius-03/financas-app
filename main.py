import streamlit as st
from streamlit_option_menu import option_menu
from modules.database import init_db, criar_usuario, verificar_login
import modules.ui_lancamentos as ui_lancamentos
import modules.ui_dashboard as ui_dashboard
import modules.ui_investimentos as ui_investimentos
import modules.ui_orcamento as ui_orcamento
import time

# 1. Configuração da Página
st.set_page_config(page_title="Sistema Financeiro", page_icon="💰", layout="wide")

# CSS Personalizado (Mantenha seu CSS aqui...)
st.markdown(""" <style> ... SEU CSS ... </style> """, unsafe_allow_html=True)

# Inicializar Estado de Sessão
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None
if 'user_name' not in st.session_state:
    st.session_state['user_name'] = ""

# --- TELA DE LOGIN / CADASTRO ---
if not st.session_state['logged_in']:
    # Tenta inicializar o banco (só funciona se secrets estiverem ok)
    try:
        init_db()
    except Exception as e:
        st.error(f"Erro de conexão com banco de dados. Verifique as Secrets. {e}")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Acesso Seguro")
        tab_login, tab_cadastro = st.tabs(["Entrar", "Criar Conta"])
        
        with tab_login:
            with st.form("login_form"):
                user = st.text_input("Usuário")
                pw = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar", type="primary"):
                    dados_user = verificar_login(user, pw)
                    if dados_user:
                        st.session_state['logged_in'] = True
                        st.session_state['user_id'] = dados_user['id']
                        st.session_state['user_name'] = dados_user['name']
                        st.success(f"Bem-vindo, {dados_user['name']}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
        
        with tab_cadastro:
            with st.form("signup_form"):
                new_user = st.text_input("Escolha um Usuário")
                new_name = st.text_input("Seu Nome")
                new_pw = st.text_input("Escolha uma Senha", type="password")
                if st.form_submit_button("Criar Conta"):
                    if criar_usuario(new_user, new_pw, new_name):
                        st.success("Conta criada! Vá para a aba 'Entrar' e faça login.")
                    else:
                        st.error("Erro: Usuário já existe.")

else:
    # --- ÁREA LOGADA (O SEU APP ANTIGO) ---
    
    # Sidebar com Logout
    with st.sidebar:
        st.write(f"👤 Olá, **{st.session_state['user_name']}**")
        if st.button("Sair"):
            st.session_state['logged_in'] = False
            st.session_state['user_id'] = None
            st.rerun()
            
        st.divider()
        
        selected = option_menu(
            menu_title="Menu Principal",
            options=["Dashboard", "Lançamentos", "Investimentos", "Orçamento"],
            icons=["graph-up-arrow", "pencil-square", "bank", "calculator"],
            menu_icon="cast",
            default_index=0,
        )

    # Roteamento (IMPORTANTE: As funções dentro dos módulos devem aceitar user_id se você alterou)
    # Como sugerido no passo 4, você deve alterar os arquivos ui_*.py para usarem st.session_state['user_id']
    # ou passar como argumento. Vou assumir que você vai alterar os UI para pegar da session_state
    # OU passar explicitamente. 
    
    # Exemplo passando explicitamente (Requer alteração nos módulos):
    # ui_lancamentos.show_lancamentos() -> Dentro do modulo, ele pega st.session_state['user_id']
    
    if selected == "Lançamentos":
        ui_lancamentos.show_lancamentos() # Certifique-se de atualizar este arquivo!

    elif selected == "Dashboard":
        ui_dashboard.show_dashboard()

    elif selected == "Investimentos":
        ui_investimentos.show_investimentos()

    elif selected == "Orçamento":
        ui_orcamento.show_orcamento()