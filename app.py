import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURAÇÕES DE CONEXÃO ---
# Novo ID da planilha Google nativa
SHEET_ID = "153ohv6YsmfOZHjoLpb8He2VM2P-DYTVGh9zDVNRBdS0"

# Função para conectar com a planilha usando os Secrets do Streamlit
def conectar_google_sheets():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(credentials)
    return client.open_by_key(SHEET_ID)

# --- CARREGAMENTO DE DADOS ---
@st.cache_data(ttl=60)
def carregar_dados():
    sh = conectar_google_sheets()
    # Carrega professores
    df_p = pd.DataFrame(sh.worksheet("Config_Professores").get_all_records())
    # Carrega alunos
    df_a = pd.DataFrame(sh.worksheet("Config_Alunos").get_all_records())
    return df_p, df_a

# --- INTERFACE ---
st.set_page_config(page_title="Sistema Escola Diva", layout="centered")

try:
    df_profs, df_alunos = carregar_dados()
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.info("Dica: Verifique se a planilha foi compartilhada como EDITOR com o e-mail da conta de serviço e se as abas têm os nomes corretos.")
    st.stop()

if 'logado' not in st.session_state:
    st.session_state.logado = False

# TELA DE LOGIN
if not st.session_state.logado:
    st.title("🔑 Acesso ao Sistema")
    user_input = st.text_input("Usuário")
    pass_input = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        match = df_profs[(df_profs['Usuario'].astype(str) == user_input) & (df_profs['Senha'].astype(str) == pass_input)]
        if not match.empty:
            st.session_state.logado = True
            st.session_state.user_data = match.iloc[0].to_dict()
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")

# INTERFACE DE REGISTRO
else:
    prof_nome = st.session_state.user_data['Professor']
    st.sidebar.write(f"Professor: **{prof_nome}**")
    
    if st.sidebar.button("Atualizar Alunos"):
        st.cache_data.clear()
        st.rerun()

    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    st.title("📝 Novo Registro")
    
    # Seleção de Turma e Aluno
    todas_turmas = sorted(df_alunos['Turma'].unique().astype(str))
    turma_sel = st.selectbox("1. Turma", todas_turmas)
    
    alunos_da_turma = df_alunos[df_alunos['Turma'].astype(str) == turma_sel]['Nome_Aluno'].tolist()
    aluno_sel = st.selectbox("2. Aluno", sorted(alunos_da_turma))

    with st.form("form_registro", clear_on_submit=True):
        disciplina = st.selectbox("Disciplina", ["Artes", "Educação Física", "Inglês", "Espanhol", "Ensino Religioso", "Projeto de Vida"])
        periodo = st.selectbox("Bimestre", ["1º Bimestre", "2º Bimestre", "3º Bimestre", "4º Bimestre"])
        tipo = st.radio("Ocorrência", ["Indisciplina", "Falta de Material", "Não realizou tarefa", "Elogio/Destaque", "Atraso"])
        obs = st.text_area("Observações")
        
        btn_salvar = st.form_submit_button("GRAVAR NA PLANILHA")

    if btn_salvar:
        try:
            sh = conectar_google_sheets()
            wks = sh.worksheet("Registros_Ocorrencias")
            
            nova_linha = [
                datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                prof_nome,
                turma_sel,
                aluno_sel,
                disciplina,
                periodo,
                tipo,
                obs
            ]
            
            wks.append_row(nova_linha)
            st.success(f"✅ Sucesso! Registro de {aluno_sel} salvo na planilha.")
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")
