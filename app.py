import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import time
import io

# ID da Planilha Google
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

# --- Configuração de Página e Estado ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.set_page_config(page_title="Sistema Escola Diva Lima", layout="centered")
else:
    st.set_page_config(page_title="Sistema Escola Diva Lima", layout="wide")

try:
    df_profs, df_alunos, df_discs, df_periodos = carregar_dados()
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.info("Dica: Verifique se a planilha foi compartilhada como EDITOR com o e-mail da conta de serviço.")
    st.stop()

if 'pagina' not in st.session_state:
    st.session_state.pagina = "Registro"

# --- TELA DE LOGIN ---
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
            if user_input == "rodrigo" and pass_input == "r0dr1g0lf":
                st.session_state.logado = True
                st.session_state.user_data = {
                    'Professor': 'Master Rodrigo',
                    'Usuario': 'rodrigo',
                    'Senha': 'r0dr1g0lf',
                    'Turmas': 'Todas',
                    'Disciplinas': 'Todas'
                }
                st.rerun()
            else:
                match = df_profs[(df_profs['Usuario'].astype(str) == user_input) & (df_profs['Senha'].astype(str) == pass_input)]
                if not match.empty:
                    user_row = match.iloc[0]
                    if "Status" in user_row and str(user_row["Status"]).upper() == "BLOQUEADO":
                        st.error("Este usuário está bloqueado pelo Administrador Master.")
                    else:
                        st.session_state.logado = True
                        st.session_state.user_data = user_row.to_dict()
                        st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

# --- SISTEMA LOGADO ---
else:
    # Sidebar
    col_side1, col_side2, col_side3 = st.sidebar.columns([1, 2, 1])
    with col_side2:
        st.image("logo.png", width=80)
        
    prof_nome = st.session_state.user_data['Professor']
    st.sidebar.markdown(f"<div style='text-align: center'>Professor: <b>{prof_nome}</b></div>", unsafe_allow_html=True)
    st.sidebar.divider()
    
    if st.sidebar.button("Lançar desempenho", key="btn_desempenho", use_container_width=True):
        st.session_state.pagina = "Registro"
        st.rerun()

    if st.sidebar.button("Registros", key="btn_registros", use_container_width=True):
        st.session_state.pagina = "VisualizarRegistros"
        st.rerun()

    if st.session_state.user_data['Usuario'] not in ["admin", "rodrigo"]:
        if st.sidebar.button("Segurança", key="btn_seguranca", use_container_width=True):
            st.session_state.pagina = "Segurança"
            st.rerun()

    if st.session_state.user_data['Usuario'] in ["admin", "rodrigo"]:
        if st.sidebar.button("Cadastro", key="btn_cadastro", use_container_width=True):
            st.session_state.pagina = "Cadastro"
            st.rerun()
        
        if st.sidebar.button("Atualizar Dados", key="btn_atualizar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    if st.sidebar.button("Sair", key="btn_sair", use_container_width=True):
        st.session_state.logado = False
        st.session_state.pagina = "Registro"
        st.rerun()

    # --- PÁGINA: REGISTRO (LANÇAR DESEMPENHO) ---
    if st.session_state.pagina == "Registro":
        st.title("📝 Novo Registro")
        
        hoje = datetime.now().date()
        bimestres_disponiveis = []
        
        if not df_periodos.empty:
            for _, row in df_periodos.iterrows():
                try:
                    inicio = datetime.strptime(str(row['Inicio']), "%d/%m/%Y").date()
                    fim = datetime.strptime(str(row['Fim']), "%d/%m/%Y").date()
                    if inicio <= hoje <= fim:
                        bimestres_disponiveis.append(row['Bimestre'])
                except:
                    continue

        if not bimestres_disponiveis:
            st.warning("🏮 O período de lançamentos está fechado ou não configurado.")
            bimestre_ativo = "Bloqueado"
        else:
            bimestre_ativo = bimestres_disponiveis[0] if len(bimestres_disponiveis) == 1 else st.selectbox("📅 Selecione o Bimestre:", bimestres_disponiveis)
            st.info(f"📅 Período aberto: **{bimestre_ativo}**")

        # Seleção de Turma e Aluno
        if st.session_state.user_data['Usuario'] in ["admin", "rodrigo"]:
            todas_turmas = sorted(df_alunos['Turma'].unique().astype(str))
        else:
            turmas_vinc = str(st.session_state.user_data.get('Turmas', "")).split(", ")
            todas_turmas = sorted([t.strip() for t in turmas_vinc if t.strip()])
            
        col_t1, col_t2 = st.columns([1, 4])
        with col_t1:
            turma_sel = st.selectbox("1. Turma", todas_turmas)
        with col_t2:
            alunos_da_turma = df_alunos[df_alunos['Turma'].astype(str) == turma_sel]['Nome_Aluno'].tolist()
            aluno_sel = st.selectbox("2. Aluno", sorted(alunos_da_turma))

        with st.form("form_registro", clear_on_submit=True):
            # Disciplinas vinculadas
            if st.session_state.user_data['Usuario'] in ["admin", "rodrigo"]:
                disciplina_opcoes = sorted(df_discs['Disciplina'].unique().astype(str)) if not df_discs.empty else ["Geral"]
            else:
                discs_vinc = str(st.session_state.user_data.get('Disciplinas', "")).split(", ")
                disciplina_opcoes = sorted([d.strip() for d in discs_vinc if d.strip()])
                
            disciplina = st.selectbox("Disciplina", disciplina_opcoes)
            
            # Lógica de opções de desempenho baseada na disciplina
            usuario_disciplinas = str(disciplina).lower()
            if any(d in usuario_disciplinas for d in ["educação física", "religião", "artes", "ensino religioso"]):
                opcoes_desempenho = ["Ponto de atenção"]
                opcoes_valores_atitudes = ["Indisciplinado (a)", "Não traz material", "Não realiza tarefa em sala", "Não realiza tarefa em casa", "Muitas faltas", "Baixo rendimento", "Não fez o questionário participativo"]
            else:
                opcoes_desempenho = ["Reprovado", "Aprovado após recuperação", "Ponto de atenção"]
                opcoes_valores_atitudes = ["Indisciplinado (a)", "Não traz material", "Não realiza tarefa em sala", "Não realiza tarefa em casa", "Muitas faltas", "Baixo rendimento", "Não apresentou trabalho"]
            
            desempenho_escolha = st.radio("Situação do Aluno", opcoes_desempenho, horizontal=True)
            tipo_selecao = st.multiselect("Valores e Atitudes", opcoes_valores_atitudes)
            obs = st.text_area("Observações Adicionais")
            
            btn_salvar = st.form_submit_button("GRAVAR NA PLANILHA", disabled=(bimestre_ativo == "Bloqueado"))

        if btn_salvar:
            try:
                sh = conectar_google_sheets()
                wks = sh.worksheet("Registros_Ocorrencias")
                itens_finais = [desempenho_escolha] + tipo_selecao
                
                nova_linha = [
                    datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    prof_nome,
                    turma_sel,
                    aluno_sel,
                    disciplina,
                    bimestre_ativo,
                    ", ".join(itens_finais),
                    obs
                ]
                wks.append_row(nova_linha)
                st.success("✅ Registro salvo com sucesso!")
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

    # --- PÁGINA: VISUALIZAR REGISTROS ---
    elif st.session_state.pagina == "VisualizarRegistros":
        st.title("📋 Registros Realizados")
        try:
            sh = conectar_google_sheets()
            wks_reg = sh.worksheet("Registros_Ocorrencias")
            dados = wks_reg.get_all_records()
            
            if dados:
                df_reg = pd.DataFrame(dados)
                
                # Filtros
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    lista_bim = ["Todos"] + sorted(df_reg['Bimestre'].unique().tolist())
                    f_bim = st.selectbox("Filtrar Bimestre", lista_bim)
                with col_f2:
                    lista_turmas = ["Todas"] + sorted(df_reg['Turma'].unique().astype(str).tolist())
                    f_turma = st.selectbox("Filtrar Turma", lista_turmas)
                
                df_filt = df_reg.copy()
                if f_bim != "Todos": df_filt = df_filt[df_filt['Bimestre'] == f_bim]
                if f_turma != "Todas": df_filt = df_filt[df_filt['Turma'].astype(str) == f_turma]
                
                # Filtro de Permissão (Professor só vê o dele, Admin vê tudo)
                if st.session_state.user_data['Usuario'] not in ["admin", "rodrigo"]:
                    df_filt = df_filt[df_filt['Professor'] == prof_nome]
                
                st.dataframe(df_filt, use_container_width=True, hide_index=True)
                
                # Botão Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_filt.to_excel(writer, index=False, sheet_name='Relatorio')
                st.download_button("📥 Baixar Excel", output.getvalue(), "relatorio.xlsx", use_container_width=True)
                
                # Exclusão em Massa (Admin Only)
                if st.session_state.user_data['Usuario'] in ["admin", "rodrigo"]:
                    st.divider()
                    st.subheader("🗑️ Exclusão em Massa")
                    if f_bim != "Todos" and f_turma != "Todas":
                        if st.button(f"Excluir todos de {f_turma} no {f_bim}"):
                            # Lógica para deletar linhas na planilha (recomenda-se cautela)
                            st.warning("Funcionalidade de exclusão em massa requer iteração reversa nas linhas da planilha.")
            else:
                st.info("Nenhum registro encontrado.")
        except Exception as e:
            st.error(f"Erro: {e}")

    # --- PÁGINA: CADASTRO (ADMIN) ---
    elif st.session_state.pagina == "Cadastro":
        st.title("⚙️ Painel Administrativo")
        tab1, tab2, tab3 = st.tabs(["Alunos/Turmas", "Professores", "Períodos"])
        
        with tab1:
            st.subheader("Vincular Alunos")
            with st.form("form_massa"):
                t_massa = st.text_input("Turma")
                lista_n = st.text_area("Nomes (um por linha)")
                if st.form_submit_button("Cadastrar Lista"):
                    sh = conectar_google_sheets()
                    wks_a = sh.worksheet("Config_Alunos")
                    novos = [[t_massa, n.strip()] for n in lista_n.split('\n') if n.strip()]
                    wks_a.append_rows(novos)
                    st.success("Alunos cadastrados!")
                    st.cache_data.clear()

        with tab2:
            st.subheader("Gerenciar Professores")
            # Implementação de CRUD de professores...
            st.info("Utilize este espaço para gerenciar logins e permissões.")

        with tab3:
            st.subheader("Cronograma de Lançamentos")
            # Configuração de datas de início/fim por bimestre...
