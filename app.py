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
    df_p = pd.DataFrame(sh.worksheet("Config_Professores").get_all_records())
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
if 'pagina' not in st.session_state:
    st.session_state.pagina = "Registro"

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

# INTERFACE PRINCIPAL
else:
    prof_nome = st.session_state.user_data['Professor']
    st.sidebar.write(f"Professor: **{prof_nome}**")
    
    if st.sidebar.button("Registro de Ocorrências"):
        st.session_state.pagina = "Registro"
        st.rerun()

    if st.sidebar.button("Cadastro"):
        st.session_state.pagina = "Cadastro"
        st.rerun()
    
    if st.sidebar.button("Atualizar Dados"):
        st.cache_data.clear()
        st.rerun()

    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.session_state.pagina = "Registro"
        st.rerun()

    if st.session_state.pagina == "Registro":
        st.title("📝 Novo Registro")
        
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

    elif st.session_state.pagina == "Cadastro":
        st.title("⚙️ Painel de Cadastro")
        
        tab1, tab2, tab3 = st.tabs(["Usuários/Professores", "Turmas/Alunos", "Alterar Senha"])
        
        with tab1:
            st.subheader("Cadastrar Novo Professor/Usuário")
            with st.form("form_prof"):
                novo_prof = st.text_input("Nome do Professor")
                novo_usuario = st.text_input("Nome de Usuário (Login)")
                nova_senha = st.text_input("Senha", type="password")
                if st.form_submit_button("Salvar Professor"):
                    try:
                        sh = conectar_google_sheets()
                        wks_p = sh.worksheet("Config_Professores")
                        wks_p.append_row([novo_prof, novo_usuario, str(nova_senha)])
                        st.success("Professor cadastrado!")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Erro: {e}")

        with tab2:
            st.subheader("Cadastrar Novo Aluno")
            with st.form("form_aluno"):
                nova_turma = st.text_input("Turma (Ex: 101, 202)")
                novo_aluno = st.text_input("Nome Completo do Aluno")
                if st.form_submit_button("Salvar Aluno"):
                    try:
                        sh = conectar_google_sheets()
                        wks_a = sh.worksheet("Config_Alunos")
                        wks_a.append_row([nova_turma, novo_aluno])
                        st.success("Aluno cadastrado!")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Erro: {e}")

        with tab3:
            st.subheader("Alterar Senha de Usuário")
            lista_usuarios = df_profs['Usuario'].tolist()
            user_alvo = st.selectbox("Selecione o Usuário", lista_usuarios)
            nova_senha_input = st.text_input("Nova Senha", type="password")
            confirmar_senha = st.text_input("Confirmar Nova Senha", type="password")
            
            if st.button("Atualizar Senha"):
                if nova_senha_input != confirmar_senha:
                    st.error("As senhas não coincidem.")
                else:
                    try:
                        sh = conectar_google_sheets()
                        wks_p = sh.worksheet("Config_Professores")
                        celula = wks_p.find(str(user_alvo))
                        wks_p.update_cell(celula.row, 3, str(nova_senha_input))
                        st.success(f"Senha de {user_alvo} atualizada com sucesso!")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Erro ao atualizar: {e}")
