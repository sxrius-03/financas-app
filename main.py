import streamlit as st
import extra_streamlit_components as stx
from streamlit_option_menu import option_menu
from modules.database import init_db, criar_usuario, verificar_login, criar_sessao, validar_sessao, apagar_sessao
import modules.ui_lancamentos as ui_lancamentos
import modules.ui_dashboard as ui_dashboard
import modules.ui_investimentos as ui_investimentos
import modules.ui_orcamento as ui_orcamento
import time
import modules.ui_cartoes as ui_cartoes
import modules.ui_despesas_fixas as ui_despesas_fixas
import modules.ui_ferramentas as ui_ferramentas
import modules.notifications as notifications
import modules.ui_reserva as ui_reserva
import modules.ui_despesas_fixas as ui_despesas_fixas
import modules.ui_projecao as ui_projecao
import modules.ui_receitas_fixas as ui_receitas_fixas

# 1. Configuração da Página
st.set_page_config(page_title="Sistema Financeiro", page_icon="💰", layout="wide")

# CSS Personalizado
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    div[data-testid="stMetric"] { background-color: #1F2229; border: 1px solid #2E303E; padding: 15px; border-radius: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.5); }
    label[data-testid="stMetricLabel"] { color: #A3A8B8 !important; font-size: 1rem !important; }
    div[data-testid="stMetricValue"] { color: #00FF7F !important; font-size: 1.6rem !important; font-weight: 700; }
    [data-testid="stDataFrame"] { background-color: #1F2229; }
    div[data-baseweb="select"] > div { background-color: #1F2229; color: white; }
</style>
""", unsafe_allow_html=True)

# 2. Inicializar Gerenciador de Cookies
cookie_manager = stx.CookieManager(key="cookie_manager")

# Inicializar Estado de Sessão
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None
if 'user_name' not in st.session_state:
    st.session_state['user_name'] = ""

# 3. Lógica de Auto-Login (Verificar Cookie)
if not st.session_state['logged_in']:
    time.sleep(0.5) 
    
    cookie_token = cookie_manager.get(cookie="financas_token")
    
    if cookie_token:
        user_data = validar_sessao(cookie_token)
        if user_data:
            st.session_state['logged_in'] = True
            st.session_state['user_id'] = user_data['id']
            st.session_state['user_name'] = user_data['name']
            st.rerun() 

# --- TELA DE LOGIN / CADASTRO ---
if not st.session_state['logged_in']:
    try:
        init_db()
    except Exception as e:
        st.error(f"Erro de conexão. Verifique Secrets. {e}")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Acesso Seguro")
        tab_login, tab_cadastro = st.tabs(["Entrar", "Criar Conta"])
        
        with tab_login:
            with st.form("login_form"):
                user = st.text_input("Usuário")
                pw = st.text_input("Senha", type="password")
                manter_conectado = st.checkbox("Manter-me conectado")
                
                if st.form_submit_button("Entrar", type="primary"):
                    dados_user = verificar_login(user, pw)
                    if dados_user:
                        st.session_state['logged_in'] = True
                        st.session_state['user_id'] = dados_user['id']
                        st.session_state['user_name'] = dados_user['name']
                        
                        if manter_conectado:
                            token, validade = criar_sessao(dados_user['id'])
                            if token:
                                cookie_manager.set("financas_token", token, expires_at=validade)
                        
                        st.success(f"Bem-vindo, {dados_user['name']}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
        
        with tab_cadastro:
            with st.form("signup_form"):
                new_user = st.text_input("Novo Usuário")
                new_name = st.text_input("Seu Nome")
                new_pw = st.text_input("Nova Senha", type="password")
                if st.form_submit_button("Criar Conta"):
                    if criar_usuario(new_user, new_pw, new_name):
                        st.success("Conta criada! Faça login.")
                    else:
                        st.error("Erro: Usuário já existe.")

else:
    # --- ÁREA LOGADA ---
    with st.sidebar:
        st.write(f"👤 **{st.session_state['user_name']}**")
        
        if st.button("Sair (Logout)"):
            token_atual = cookie_manager.get("financas_token")
            if token_atual:
                apagar_sessao(token_atual)
                cookie_manager.delete("financas_token")
            
            st.session_state['logged_in'] = False
            st.session_state['user_id'] = None
            st.rerun()
            
        st.divider()

        if st.session_state['user_name'] == 'Eduardo': 
            from modules.database import contar_usuarios_ativos
            
            st.divider()
            st.caption("🔒 Área do Admin")
            qtd_ativos = contar_usuarios_ativos()
            
            # Mostra o número com um indicador visual
            st.metric(
                label="Usuários Logados", 
                value=qtd_ativos, 
                delta=None,
                help="Quantidade de usuários com sessão válida no momento."
            )

        st.divider()
        
        # --- EXIBIR NOTIFICAÇÕES (VOCÊ FEZ CORRETO) ---
        notifications.exibir_notificacoes_na_sidebar(st.session_state['user_id'])
        
        selected = option_menu(
            menu_title="Menu Principal",
            # --- CORREÇÃO AQUI: ADICIONEI "Reserva" ---
            options=["Dashboard", "Lançamentos", "Receitas Fixas","Despesas Fixas", "Projeção", "Cartões", "Investimentos", "Reserva", "Orçamento", "Ferramentas"],
            # --- CORREÇÃO AQUI: ADICIONEI ÍCONE "safe" ou "shield-lock" ---
            icons=["graph-up-arrow", "pencil-square", "cash-stack", "calendar-x", "activity", "credit-card", "bank", "safe", "calculator", "arrow-repeat", "tools"],
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"padding": "5!important", "background-color": "#1F2229"},
                "icon": {"color": "#9D9D9D", "font-size": "20px"}, 
                "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#2E303E"},
                "nav-link-selected": {"background-color": "#13442C", "color": "#0E1117", "font-weight": "bold"},
            }
        )

    # Roteamento
    if selected == "Lançamentos":
        ui_lancamentos.show_lancamentos()
    elif selected == "Dashboard":
        ui_dashboard.show_dashboard()
    elif selected == "Investimentos":
        ui_investimentos.show_investimentos()
    elif selected == "Orçamento":
        ui_orcamento.show_orcamento()
    elif selected == "Cartões":
        ui_cartoes.show_cartoes()
    elif selected == "Ferramentas":
        ui_ferramentas.show_ferramentas()
    elif selected == "Reserva":
        ui_reserva.show_reserva()
    elif selected == "Despesas Fixas":
        ui_despesas_fixas.show_despesas_fixas()
    elif selected == "Projeção":
        ui_projecao.show_projecao()
    elif selected == "Receitas Fixas":
        ui_receitas_fixas.show_receitas_fixas()