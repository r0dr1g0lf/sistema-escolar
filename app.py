import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURAÇÕES DE CONEXÃO ---
SHEET_ID = "153ohv6YsmfOZHjoLpb8He2VM2P-DYTVGh9zDVNRBdS0"

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
    
    # Carrega alunos e trata possíveis nomes de coluna
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

# --- INTERFACE ---
st.set_page_config(page_title="Sistema Escola Diva", layout="centered")

try:
    df_profs, df_alunos, df_discs, df_periodos = carregar_dados()
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()

if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'pagina' not in st.session_state:
    st.session_state.pagina = "Registro"

# TELA DE LOGIN
if not st.session_state.logado:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.image("logo.png", width=120)
    
    st.title("🔑 Acesso ao Sistema")
    with st.form("login_form"):
        user_input = st.text_input("Usuário")
        pass_input = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar")
        
        if entrar:
            match = df_profs[(df_profs['Usuario'].astype(str) == user_input) & (df_profs['Senha'].astype(str) == pass_input)]
            if not match.empty:
                st.session_state.logado = True
                st.session_state.user_data = match.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

else:
    # Interface Principal
    prof_nome = st.session_state.user_data['Professor']
    st.sidebar.image("logo.png", width=80)
    st.sidebar.markdown(f"Professor: **{prof_nome}**")
    st.sidebar.divider()
    
    if st.sidebar.button("Registro de Ocorrências", use_container_width=True):
        st.session_state.pagina = "Registro"
        st.rerun()

    if st.session_state.user_data['Usuario'] == "admin":
        if st.sidebar.button("⚙️ Painel Admin", use_container_width=True):
            st.session_state.pagina = "Cadastro"
            st.rerun()

    if st.sidebar.button("Sair", use_container_width=True):
        st.session_state.logado = False
        st.rerun()

    if st.session_state.pagina == "Registro":
        st.title("📝 Novo Registro")
        
        # Lógica de Bimestre
        hoje = datetime.now().date()
        bimestre_ativo = "Bloqueado"
        if not df_periodos.empty:
            for _, row in df_periodos.iterrows():
                try:
                    inicio = datetime.strptime(str(row['Inicio']), "%d/%m/%Y").date()
                    fim = datetime.strptime(str(row['Fim']), "%d/%m/%Y").date()
                    if inicio <= hoje <= fim:
                        bimestre_ativo = row['Bimestre']
                        break
                except: continue

        if bimestre_ativo == "Bloqueado":
            st.warning("🏮 Período de lançamentos fechado.")
        else:
            st.info(f"📅 Período: **{bimestre_ativo}**")

        # --- CORREÇÃO DA FILTRAGEM (TURMAS vs DISCIPLINAS) ---
        # Identifica as turmas vinculadas ao professor
        if st.session_state.user_data['Usuario'] == "admin":
            lista_turmas_disp = sorted(df_alunos['Turma'].unique().astype(str))
        else:
            vinc_turmas = str(st.session_state.user_data.get('Turmas', "")).split(", ")
            lista_turmas_disp = sorted([t.strip() for t in vinc_turmas if t.strip()])

        turma_sel = st.selectbox("1. Selecione a Turma", lista_turmas_disp)
        
        # Filtra alunos daquela turma específica
        df_alunos_filtrados = df_alunos[df_alunos['Turma'].astype(str) == turma_sel]
        
        # Tenta encontrar a coluna de nome (ajuda a evitar o KeyError)
        col_nome_aluno = "Nome_Aluno" if "Nome_Aluno" in df_alunos.columns else df_alunos.columns[1]
        lista_alunos = sorted(df_alunos_filtrados[col_nome_aluno].tolist())
        
        aluno_sel = st.selectbox("2. Selecione o Aluno", lista_alunos)

        with st.form("form_ocorrencia", clear_on_submit=True):
            # Identifica as disciplinas vinculadas
            if st.session_state.user_data['Usuario'] == "admin":
                opcoes_discs = sorted(df_discs['Disciplina'].unique().astype(str))
            else:
                vinc_discs = str(st.session_state.user_data.get('Disciplinas', "")).split(", ")
                opcoes_discs = sorted([d.strip() for d in vinc_discs if d.strip()])

            disciplina = st.selectbox("Disciplina", opcoes_discs)
            tipo = st.radio("Tipo de Ocorrência", ["Indisciplina", "Falta de Material", "Tarefa não realizada", "Elogio", "Atraso"])
            obs = st.text_area("Observações detalhadas")
            
            salvar = st.form_submit_button("SALVAR REGISTRO", disabled=(bimestre_ativo == "Bloqueado"))

            if salvar:
                try:
                    sh = conectar_google_sheets()
                    wks = sh.worksheet("Registros_Ocorrencias")
                    wks.append_row([
                        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                        prof_nome, turma_sel, aluno_sel, disciplina, bimestre_ativo, tipo, obs
                    ])
                    st.success("✅ Registro salvo com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

    elif st.session_state.pagina == "Cadastro":
        st.title("⚙️ Gerenciamento")
        st.info("Utilize as abas da planilha Google para cadastros em massa ou o formulário abaixo.")
        # ... (restante do código de cadastro pode ser mantido ou simplificado)
