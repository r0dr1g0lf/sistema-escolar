import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import time

SHEET_ID = "153ohv6YsmfOZHjoLpb8He2VM2P-DYTVGh9zDVNRBdS0"

def conectar_google_sheets():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(credentials)
    return client.open_by_key(SHEET_ID)

@st.cache_data(ttl=60)
def carregar_dados():
    sh = conectar_google_sheets()
    df_p = pd.DataFrame(sh.worksheet("Config_Professores").get_all_records())
    df_a = pd.DataFrame(sh.worksheet("Config_Alunos").get_all_records())
    
    try:
        df_d = pd.DataFrame(sh.worksheet("Config_Disciplinas").get_all_records())
    except:
        df_d = pd.DataFrame(columns=["Disciplina"])
        
    try:
        df_per = pd.DataFrame(sh.worksheet("Config_Periodos").get_all_records())
    except:
        df_per = pd.DataFrame(columns=["Bimestre", "Inicio", "Fim"])
        
    return df_p, df_a, df_d, df_per

st.set_page_config(page_title="Sistema Escola Diva Lima", layout="wide")

# CSS para centralização absoluta e remoção de scroll na tela de login
if 'logado' not in st.session_state or not st.session_state.logado:
    st.markdown("""
        <style>
        /* Remove o header e o padding padrão do Streamlit */
        header {visibility: hidden;}
        .main .block-container {
            padding: 0;
            max-width: 100%;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        /* Esconde a barra de rolagem lateral se houver */
        .main {
            overflow: hidden;
        }
        .login-header {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
            margin-bottom: 20px;
        }
        .stForm {
            width: 350px !important;
            margin: 0 auto;
        }
        </style>
        """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        </style>
        """, unsafe_allow_html=True)

try:
    df_profs, df_alunos, df_discs, df_periodos = carregar_dados()
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()

if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'pagina' not in st.session_state:
    st.session_state.pagina = "Registro"

if not st.session_state.logado:
    # Usamos um container fixo para garantir a centralização
    with st.container():
        st.markdown('<div class="login-header">', unsafe_allow_html=True)
        # Layout da logo ao lado da chave/texto
        col_img, col_txt = st.columns([1, 2.5])
        with col_img:
            st.image("logo.png", width=60)
        with col_txt:
            st.markdown("<h2 style='margin: 0;'>🔑 Acesso</h2>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        with st.form("login_form"):
            user_input = st.text_input("Usuário")
            pass_input = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar", use_container_width=True)
            
            if entrar:
                if user_input == "master" and pass_input == "master123":
                    st.session_state.logado = True
                    st.session_state.user_data = {
                        'Professor': 'Administrador Master',
                        'Usuario': 'master',
                        'Senha': 'master123',
                        'Turmas': 'Todas',
                        'Disciplinas': 'Todas'
                    }
                    st.rerun()
                else:
                    match = df_profs[(df_profs['Usuario'].astype(str) == user_input) & (df_profs['Senha'].astype(str) == pass_input)]
                    if not match.empty:
                        status_bloqueio = str(match.iloc[0].get('Status', 'Ativo'))
                        if status_bloqueio == 'Bloqueado':
                            st.error("Usuário bloqueado.")
                        else:
                            st.session_state.logado = True
                            st.session_state.user_data = match.iloc[0].to_dict()
                            st.rerun()
                    else:
                        st.error("Credenciais inválidas.")

else:
    # O restante do código (Sidebar e Páginas) permanece o mesmo do seu original
    col_side1, col_side2, col_side3 = st.sidebar.columns([1, 2, 1])
    with col_side2:
        st.image("logo.png", width=80)
        
    prof_nome = st.session_state.user_data['Professor']
    st.sidebar.markdown(f"<div style='text-align: center'>Professor: <b>{prof_nome}</b></div>", unsafe_allow_html=True)
    st.sidebar.divider()
    
    # ... (restante dos botões e lógica das páginas igual ao seu código)
    if st.sidebar.button("Sair", use_container_width=True):
        st.session_state.logado = False
        st.rerun()

    if st.session_state.pagina == "Registro":
        st.title("📝 Novo Registro")
        # ... (continua lógica de registro)
