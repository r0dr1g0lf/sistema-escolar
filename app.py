import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import time

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
    st.info("Dica: Verifique se a planilha foi compartilhada como EDITOR com o e-mail da conta de serviço e se as abas têm os nomes corretos.")
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

# INTERFACE PRINCIPAL
else:
    col_side1, col_side2, col_side3 = st.sidebar.columns([1, 2, 1])
    with col_side2:
        st.image("logo.png", width=80)
        
    prof_nome = st.session_state.user_data['Professor']
    st.sidebar.markdown(f"<div style='text-align: center'>Professor: <b>{prof_nome}</b></div>", unsafe_allow_html=True)
    st.sidebar.divider()
    
    if st.sidebar.button("Desempenho do aluno", key="btn_desempenho", use_container_width=True):
        st.session_state.pagina = "Registro"
        st.rerun()

    if st.sidebar.button("Registros", key="btn_registros", use_container_width=True):
        st.session_state.pagina = "VisualizarRegistros"
        st.rerun()

    if st.session_state.user_data['Usuario'] != "admin":
        if st.sidebar.button("Segurança", key="btn_seguranca", use_container_width=True):
            st.session_state.pagina = "Segurança"
            st.rerun()

    if st.session_state.user_data['Usuario'] == "admin":
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

    if st.session_state.pagina == "Registro":
        st.title("📝 Novo Registro")
        
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
                except:
                    continue

        if bimestre_ativo == "Bloqueado":
            st.warning("🏮 O período de lançamentos está fechado ou não configurado.")
        else:
            st.info(f"📅 Período de lançamento aberto: **{bimestre_ativo}**")

        if st.session_state.user_data['Usuario'] == "admin":
            todas_turmas = sorted(df_alunos['Turma'].unique().astype(str))
        else:
            turmas_vinc = str(st.session_state.user_data.get('Turmas', "")).split(", ")
            todas_turmas = sorted([t.strip() for t in turmas_vinc if t.strip()])
            
        turma_sel = st.selectbox("1. Turma", todas_turmas)
        
        alunos_da_turma = df_alunos[df_alunos['Turma'].astype(str) == turma_sel]['Nome_Aluno'].tolist()
        aluno_sel = st.selectbox("2. Aluno", sorted(alunos_da_turma))

        with st.form("form_registro", clear_on_submit=True):
            if st.session_state.user_data['Usuario'] == "admin":
                if not df_discs.empty:
                    disciplina_opcoes = sorted(df_discs['Disciplina'].unique().astype(str))
                else:
                    disciplina_opcoes = ["Artes", "Educação Física", "Inglês", "Espanhol", "Ensino Religioso", "Projeto de Vida"]
            else:
                discs_vinc = str(st.session_state.user_data.get('Disciplinas', "")).split(", ")
                disciplina_opcoes = sorted([d.strip() for d in discs_vinc if d.strip()])
                
            disciplina = st.selectbox("Disciplina", disciplina_opcoes)
            periodo = st.text_input("Bimestre", value=bimestre_ativo, disabled=True)
            tipo = st.radio("Valores e atitudes", ["Indisciplinado (a)", "Não traz material", "Não realiza tarefa em sala", "Não realiza tarefa em casa", "Muitas faltas"])
            obs = st.text_area("Observações")
            
            btn_salvar = st.form_submit_button("GRAVAR NA PLANILHA", disabled=(bimestre_ativo == "Bloqueado"))

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

    elif st.session_state.pagina == "VisualizarRegistros":
        st.title("📋 Registros Realizados")
        try:
            sh = conectar_google_sheets()
            wks_reg = sh.worksheet("Registros_Ocorrencias")
            dados_brutos = wks_reg.get_all_values()
            
            if len(dados_brutos) > 1:
                df_reg = pd.DataFrame(dados_brutos[1:], columns=dados_brutos[0])
                colunas_df = df_reg.columns.tolist()
                
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    col_bim = 'Bimestre' if 'Bimestre' in colunas_df else colunas_df[5]
                    lista_bimestres = ["Todos"] + sorted(df_reg[col_bim].unique().astype(str).tolist())
                    bim_filtro = st.selectbox("Filtrar por Bimestre", lista_bimestres)
                
                with col_f2:
                    col_turma = 'Turma' if 'Turma' in colunas_df else colunas_df[2]
                    lista_turmas_reg = ["Todas"] + sorted(df_reg[col_turma].unique().astype(str).tolist())
                    turma_filtro = st.selectbox("Filtrar por Turma", lista_turmas_reg)
                
                df_reg['ID_Original'] = range(2, len(df_reg) + 2)
                df_filtrado = df_reg.copy()
                
                if bim_filtro != "Todos":
                    df_filtrado = df_filtrado[df_filtrado[col_bim].astype(str) == bim_filtro]
                
                if turma_filtro != "Todas":
                    df_filtrado = df_filtrado[df_filtrado[col_turma].astype(str) == turma_filtro]
                
                if st.session_state.user_data['Usuario'] != "admin":
                    df_filtrado = df_filtrado[df_filtrado['Professor'] == prof_nome]
                
                st.dataframe(df_filtrado.drop(columns=['ID_Original']), use_container_width=True)

                st.divider()
                st.subheader("🗑️ Gerenciar Exclusões")
                
                col_exc1, col_exc2 = st.columns(2)
                
                with col_exc1:
                    st.markdown("**Excluir registro único**")
                    if not df_filtrado.empty:
                        opcoes_excluir = {f"{row['Data_Hora']} - {row['Aluno']}": row['ID_Original'] for _, row in df_filtrado.iterrows()}
                        selecionado_para_excluir = st.selectbox("Selecione o registro para apagar", [""] + list(opcoes_excluir.keys()))
                        
                        if selecionado_para_excluir != "" and st.button("Confirmar Exclusão Única"):
                            linha_idx = opcoes_excluir[selecionado_para_excluir]
                            wks_reg.delete_rows(linha_idx)
                            st.success("Registro excluído!")
                            st.rerun()
                    else:
                        st.info("Nenhum registro para excluir no filtro atual.")

                with col_exc2:
                    st.markdown("**Exclusão em massa**")
                    if bim_filtro != "Todos" and turma_filtro != "Todas":
                        st.warning(f"Apagar TODOS os registros de {turma_filtro} no {bim_filtro}?")
                        if st.button(f"🚨 EXCLUIR TUDO: {turma_filtro} - {bim_filtro}"):
                            indices_massa = sorted(df_filtrado['ID_Original'].tolist(), reverse=True)
                            for idx in indices_massa:
                                wks_reg.delete_rows(idx)
                            st.success(f"Foram excluídos {len(indices_massa)} registros.")
                            st.rerun()
                    else:
                        st.info("Selecione uma Turma e um Bimestre específicos para habilitar a exclusão em massa.")

            else:
                st.info("Nenhum registro encontrado na planilha.")
        except Exception as e:
            st.error(f"Erro ao carregar registros: {e}")

    elif st.session_state.pagina == "Segurança":
        st.title("🔒 Segurança")
        st.subheader("Alterar Minha Senha")
        
        user_atual = st.session_state.user_data['Usuario']
        
        with st.form("form_alterar_senha_prof"):
            nova_senha_prof = st.text_input("Nova Senha", type="password")
            confirmar_senha_prof = st.text_input("Confirmar Nova Senha", type="password")
            
            col_senha_p1, col_senha_p2 = st.columns([1, 2])
            with col_senha_p1:
                btn_p = st.form_submit_button("Atualizar Minha Senha")
            
            if btn_p:
                if nova_senha_prof != confirmar_senha_prof:
                    st.error("As senhas não coincidem.")
                else:
                    try:
                        sh = conectar_google_sheets()
                        wks_p = sh.worksheet("Config_Professores")
                        celula = wks_p.find(str(user_atual))
                        wks_p.update_cell(celula.row, 3, str(nova_senha_prof))
                        with col_senha_p2:
                            st.success("✅ Senha atualizada!")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Erro ao atualizar: {e}")

    elif st.session_state.pagina == "Cadastro" and st.session_state.user_data['Usuario'] == "admin":
        st.title("⚙️ Painel de Cadastro")
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Turmas/Alunos", "Disciplinas", "Gerenciar Usuários", "Alterar Senha", "Período de Lançamento"])
        
        with tab1:
            st.subheader("Gerenciar Alunos e Turmas")
            
            opcao_cadastro = st.radio("Selecione uma Ação", ["Individual", "Em Massa (Excel/Word)", "Transferir Aluno", "Excluir Aluno", "Limpar turma"])
            
            if opcao_cadastro == "Individual":
                placeholder_msg = st.empty()
                if 'aluno_sucesso' in st.session_state:
                    placeholder_msg.markdown(f"<h3 style='color: #28a745; text-align: center;'>{st.session_state.aluno_sucesso}</h3>", unsafe_allow_html=True)
                    time.sleep(3)
                    placeholder_msg.empty()
                    del st.session_state.aluno_sucesso
                
                with st.form("form_aluno", clear_on_submit=True):
                    nova_turma = st.text_input("Turma (Ex: 101, 202)")
                    novo_aluno = st.text_input("Nome Completo do Aluno")
                    if st.form_submit_button("Salvar Aluno"):
                        duplicado = df_alunos[(df_alunos['Turma'].astype(str) == nova_turma) & (df_alunos['Nome_Aluno'].astype(str).str.upper() == novo_aluno.strip().upper())]
                        if not duplicado.empty:
                            st.error(f"Erro: O aluno '{novo_aluno}' já está cadastrado na turma '{nova_turma}'.")
                        else:
                            try:
                                sh = conectar_google_sheets()
                                wks_a = sh.worksheet("Config_Alunos")
                                wks_a.append_row([nova_turma, novo_aluno])
                                st.session_state.aluno_sucesso = "Aluno cadastrado com sucesso"
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")
            
            elif opcao_cadastro == "Em Massa (Excel/Word)":
                placeholder_msg_massa = st.empty()
                if 'massa_sucesso' in st.session_state:
                    placeholder_msg_massa.markdown(f"<h3 style='color: #28a745; text-align: center;'>{st.session_state.massa_sucesso}</h3>", unsafe_allow_html=True)
                    time.sleep(3)
                    placeholder_msg_massa.empty()
                    del st.session_state.massa_sucesso

                with st.form("form_aluno_massa", clear_on_submit=True):
                    turma_massa = st.text_input("Turma para todos os alunos (Ex: 101)")
                    lista_nomes = st.text_area("Cole aqui a lista de nomes (um por linha)")
                    if st.form_submit_button("Salvar Todos os Alunos"):
                        if not turma_massa or not lista_nomes:
                            st.error("Preencha a turma e a lista de nomes.")
                        else:
                            try:
                                nomes = [n.strip() for n in lista_nomes.split('\n') if n.strip()]
                                novas_linhas = []
                                ja_existentes = []

                                for nome in nomes:
                                    existe = df_alunos[(df_alunos['Turma'].astype(str) == turma_massa) & (df_alunos['Nome_Aluno'].astype(str).str.upper() == nome.upper())]
                                    if existe.empty:
                                        novas_linhas.append([turma_massa, nome])
                                    else:
                                        ja_existentes.append(nome)
                                
                                if ja_existentes:
                                    st.error(f"Não foi possível cadastrar: Os seguintes alunos já existem nesta turma: {', '.join(ja_existentes)}")
                                elif novas_linhas:
                                    sh = conectar_google_sheets()
                                    wks_a = sh.worksheet("Config_Alunos")
                                    wks_a.append_rows(novas_linhas)
                                    
                                    st.session_state.massa_sucesso = f"{len(nomes)} alunos cadastrados com sucesso!"
                                    st.cache_data.clear()
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao cadastrar em massa: {e}")

            elif opcao_cadastro == "Transferir Aluno":
                st.subheader("Transferir Aluno de Turma")
                
                placeholder_transf = st.empty()
                if 'transf_sucesso' in st.session_state:
                    placeholder_transf.markdown(f"<h3 style='color: #28a745; text-align: center;'>{st.session_state.transf_sucesso}</h3>", unsafe_allow_html=True)
                    time.sleep(3)
                    placeholder_transf.empty()
                    del st.session_state.transf_sucesso

                todas_turmas_cadastradas = sorted(df_alunos['Turma'].unique().astype(str))
                turma_orig = st.selectbox("Turma de Origem", [""] + todas_turmas_cadastradas)
                
                if turma_orig != "":
                    alunos_orig = df_alunos[df_alunos['Turma'].astype(str) == turma_orig]['Nome_Aluno'].tolist()
                    aluno_a_transf = st.selectbox("Selecione o Aluno para Transferir", [""] + sorted(alunos_orig))
                    turma_dest = st.selectbox("Turma de Destino", [""] + todas_turmas_cadastradas)
                    
                    if aluno_a_transf != "" and turma_dest != "" and st.button("Executar Transferência"):
                        try:
                            sh = conectar_google_sheets()
                            wks_a = sh.worksheet("Config_Alunos")
                            data = wks_a.get_all_values()
                            row_index = -1
                            for i, row in enumerate(data):
                                if row[0] == turma_orig and row[1] == aluno_a_transf:
                                    row_index = i + 1
                                    break
                            
                            if row_index != -1:
                                wks_a.update_cell(row_index, 1, str(turma_dest))
                                st.session_state.transf_sucesso = "Aluno transferido com sucesso"
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error("Aluno não encontrado na base de dados para atualização.")
                        except Exception as e:
                            st.error(f"Erro ao transferir aluno: {e}")

            elif opcao_cadastro == "Excluir Aluno":
                st.subheader("Excluir Aluno Específico")
                
                placeholder_exc = st.empty()
                if 'exc_sucesso' in st.session_state:
                    placeholder_exc.markdown(f"<h3 style='color: #28a745; text-align: center;'>{st.session_state.exc_sucesso}</h3>", unsafe_allow_html=True)
                    time.sleep(3)
                    placeholder_exc.empty()
                    del st.session_state.exc_sucesso

                todas_turmas_exc = sorted(df_alunos['Turma'].unique().astype(str))
                turma_exc = st.selectbox("Selecione a Turma", [""] + todas_turmas_exc)
                
                if turma_exc != "":
                    alunos_exc = df_alunos[df_alunos['Turma'].astype(str) == turma_exc]['Nome_Aluno'].tolist()
                    aluno_a_excluir = st.selectbox("Selecione o Aluno para Excluir", [""] + sorted(alunos_exc))
                    
                    if aluno_a_excluir != "" and st.button("❌ EXCLUIR ALUNO DEFINITIVAMENTE"):
                        try:
                            sh = conectar_google_sheets()
                            wks_a = sh.worksheet("Config_Alunos")
                            data = wks_a.get_all_values()
                            row_index = -1
                            for i, row in enumerate(data):
                                if row[0] == turma_exc and row[1] == aluno_a_excluir:
                                    row_index = i + 1
                                    break
                            
                            if row_index != -1:
                                wks_a.delete_rows(row_index)
                                st.session_state.exc_sucesso = f"Aluno {aluno_a_excluir} removido com sucesso"
                                st.cache_data.clear()
                                st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao excluir aluno: {e}")

            elif opcao_cadastro == "Limpar turma":
                st.subheader("Limpar Todos os Alunos de uma Turma")
                
                placeholder_limpar = st.empty()
                if 'limpar_sucesso' in st.session_state:
                    placeholder_limpar.markdown(f"<h3 style='color: #28a745; text-align: center;'>{st.session_state.limpar_sucesso}</h3>", unsafe_allow_html=True)
                    time.sleep(3)
                    placeholder_limpar.empty()
                    del st.session_state.limpar_sucesso

                todas_turmas_limpar = sorted(df_alunos['Turma'].unique().astype(str))
                turma_alvo_limpar = st.selectbox("Selecione a Turma para APAGAR TODOS os alunos", [""] + todas_turmas_limpar)
                
                if turma_alvo_limpar != "":
                    st.warning(f"⚠️ ATENÇÃO: Esta ação apagará TODOS os alunos da turma {turma_alvo_limpar}.")
                    confirmacao_turma = st.checkbox(f"Confirmo que desejo apagar todos os alunos da {turma_alvo_limpar}")
                    
                    if st.button(f"🚨 APAGAR ALUNOS DA TURMA {turma_alvo_limpar}"):
                        if confirmacao_turma:
                            try:
                                sh = conectar_google_sheets()
                                wks_a = sh.worksheet("Config_Alunos")
                                data = wks_a.get_all_values()
                                
                                indices_para_deletar = [i + 1 for i, row in enumerate(data) if row[0] == turma_alvo_limpar]
                                
                                if indices_para_deletar:
                                    for idx in reversed(indices_para_deletar):
                                        wks_a.delete_rows(idx)
                                    
                                    st.session_state.limpar_sucesso = f"Todos os alunos da turma {turma_alvo_limpar} foram removidos com sucesso"
                                    st.cache_data.clear()
                                    st.rerun()
                                else:
                                    st.info("Nenhum aluno encontrado para esta turma.")
                            except Exception as e:
                                st.error(f"Erro ao limpar turma: {e}")
                        else:
                            st.error("Marque a caixa de confirmação.")

        with tab2:
            st.subheader("Gerenciar Disciplinas")
            
            placeholder_disc = st.empty()
            if 'disc_sucesso' in st.session_state:
                placeholder_disc.markdown(f"<h3 style='color: #28a745; text-align: center;'>{st.session_state.disc_sucesso}</h3>", unsafe_allow_html=True)
                time.sleep(3)
                placeholder_disc.empty()
                del st.session_state.disc_sucesso
            
            with st.form("form_disciplina", clear_on_submit=True):
                nova_disc = st.text_input("Nome da Disciplina")
                if st.form_submit_button("Cadastrar Disciplina"):
                    if nova_disc:
                        duplicada_disc = df_discs[df_discs['Disciplina'].astype(str).str.upper() == nova_disc.strip().upper()]
                        if not duplicada_disc.empty:
                            st.error(f"Erro: A disciplina '{nova_disc}' já está cadastrada.")
                        else:
                            try:
                                sh = conectar_google_sheets()
                                try:
                                    wks_d = sh.worksheet("Config_Disciplinas")
                                except:
                                    wks_d = sh.add_worksheet(title="Config_Disciplinas", rows="100", cols="2")
                                    wks_d.append_row(["Disciplina"])
                                    
                                wks_d.append_row([nova_disc])
                                st.session_state.disc_sucesso = f"Disciplina '{nova_disc}' cadastrada com sucesso"
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")
                    else:
                        st.error("Informe o nome da disciplina.")

            st.divider()
            st.subheader("Excluir Disciplina")
            
            placeholder_disc_exc = st.empty()
            if 'disc_exc_sucesso' in st.session_state:
                placeholder_disc_exc.markdown(f"<h3 style='color: #28a745; text-align: center;'>{st.session_state.disc_exc_sucesso}</h3>", unsafe_allow_html=True)
                time.sleep(3)
                placeholder_disc_exc.empty()
                del st.session_state.disc_exc_sucesso

            if not df_discs.empty:
                disc_lista = sorted(df_discs['Disciplina'].unique().astype(str))
                disc_excluir = st.selectbox("Selecione a disciplina para remover", [""] + disc_lista)
                
                if disc_excluir != "" and st.button("❌ REMOVER DISCIPLINA"):
                    try:
                        sh = conectar_google_sheets()
                        wks_d = sh.worksheet("Config_Disciplinas")
                        celula = wks_d.find(str(disc_excluir))
                        wks_d.delete_rows(celula.row)
                        st.session_state.disc_exc_sucesso = f"Disciplina '{disc_excluir}' removida com sucesso"
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao excluir: {e}")
            else:
                st.info("Nenhuma disciplina cadastrada.")

        with tab3:
            st.subheader("Cadastrar Novo Professor")
            
            with st.form("form_prof", clear_on_submit=True):
                novo_prof = st.text_input("Nome do Professor")
                novo_usuario = st.text_input("Nome de Usuário (Login)")
                nova_senha = st.text_input("Senha", type="password", help="Opcional")
                
                todas_turmas_disp = sorted(df_alunos['Turma'].unique().astype(str))
                turmas_vinculo = st.multiselect("Vincular Turmas", todas_turmas_disp)
                
                if not df_discs.empty:
                    disciplina_opcoes = sorted(df_discs['Disciplina'].unique().astype(str))
                else:
                    disciplina_opcoes = ["Artes", "Educação Física", "Inglês", "Espanhol", "Ensino Religioso", "Projeto de Vida"]
                
                disciplinas_vinculo = st.multiselect("Vincular Disciplinas", disciplina_opcoes)
                
                col_btn_salvar, col_msg_salvar = st.columns([1, 2])
                with col_btn_salvar:
                    btn_salvar_prof = st.form_submit_button("Salvar Professor")
                
                if btn_salvar_prof:
                    if not novo_prof or not novo_usuario:
                        st.error("Por favor, preencha o nome do professor e o nome de usuário.")
                    else:
                        duplicado_user = df_profs[df_profs['Usuario'].astype(str).str.upper() == novo_usuario.strip().upper()]
                        if not duplicado_user.empty:
                            st.error(f"Erro: O nome de usuário '{novo_usuario}' já está em uso.")
                        else:
                            try:
                                sh = conectar_google_sheets()
                                wks_p = sh.worksheet("Config_Professores")
                                
                                turmas_str = ", ".join(turmas_vinculo)
                                disciplinas_str = ", ".join(disciplinas_vinculo)
                                
                                senha_final = str(nova_senha) if nova_senha else ""
                                
                                wks_p.append_row([novo_prof, novo_usuario, senha_final, turmas_str, disciplinas_str])
                                with col_msg_salvar:
                                    st.success("Professor cadastrado com sucesso!")
                                st.cache_data.clear()
                                time.sleep(2)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")
            
            st.divider()
            st.subheader("Editar ou Excluir Usuário Existente")
            
            placeholder_prof_edit = st.empty()
            if 'prof_edit_sucesso' in st.session_state:
                placeholder_prof_edit.markdown(f"<h3 style='color: #28a745; text-align: center;'>{st.session_state.prof_edit_sucesso}</h3>", unsafe_allow_html=True)
                time.sleep(3)
                placeholder_prof_edit.empty()
                del st.session_state.prof_edit_sucesso
            
            lista_usuarios_edit = df_profs['Usuario'].tolist()
            user_selecionado = st.selectbox("Selecione o Usuário para Modificar", [""] + lista_usuarios_edit)
            
            if user_selecionado != "":
                dados_atuais = df_profs[df_profs['Usuario'] == user_selecionado].iloc[0]
                
                with st.form("form_editar_usuario"):
                    edit_nome = st.text_input("Alterar Nome do Professor", value=dados_atuais['Professor'])
                    edit_login = st.text_input("Alterar Login (Usuário)", value=dados_atuais['Usuario'])
                    
                    todas_turmas_disp = sorted(df_alunos['Turma'].unique().astype(str))
                    turmas_atuais = str(dados_atuais.get('Turmas', "")).split(", ") if dados_atuais.get('Turmas') else []
                    edit_turmas = st.multiselect("Alterar Turmas", todas_turmas_disp, default=[t for t in turmas_atuais if t in todas_turmas_disp])
                    
                    if not df_discs.empty:
                        disciplina_opcoes = sorted(df_discs['Disciplina'].unique().astype(str))
                    else:
                        disciplina_opcoes = ["Artes", "Educação Física", "Inglês", "Espanhol", "Ensino Religioso", "Projeto de Vida"]
                        
                    disciplinas_atuais = str(dados_atuais.get('Disciplinas', "")).split(", ") if dados_atuais.get('Disciplinas') else []
                    edit_disciplinas = st.multiselect("Alterar Disciplinas", disciplina_opcoes, default=[d for d in disciplinas_atuais if d in disciplina_opcoes])
                    
                    col_btn1, col_btn_msg, col_btn2 = st.columns([1, 2, 1])
                    with col_btn1:
                        btn_update = st.form_submit_button("SALVAR ALTERAÇÕES")
                    with col_btn2:
                        btn_delete = st.form_submit_button("❌ EXCLUIR USUÁRIO")

                if btn_update:
                    try:
                        sh = conectar_google_sheets()
                        wks_p = sh.worksheet("Config_Professores")
                        celula = wks_p.find(str(user_selecionado))
                        
                        turmas_edit_str = ", ".join(edit_turmas)
                        disciplinas_edit_str = ", ".join(edit_disciplinas)
                        
                        wks_p.update_cell(celula.row, 1, edit_nome)
                        wks_p.update_cell(celula.row, 2, edit_login)
                        wks_p.update_cell(celula.row, 4, turmas_edit_str)
                        wks_p.update_cell(celula.row, 5, disciplinas_edit_str)
                        
                        with col_btn_msg:
                            st.success("Atualizado!")
                        
                        st.session_state.prof_edit_sucesso = f"Dados de {user_selecionado} atualizados com sucesso!"
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao atualizar: {e}")

                if btn_delete:
                    try:
                        sh = conectar_google_sheets()
                        wks_p = sh.worksheet("Config_Professores")
                        celula = wks_p.find(str(user_selecionado))
                        wks_p.delete_rows(celula.row)
                        
                        with col_btn_msg:
                            st.success(f"Usuário {user_selecionado} excluído!")
                        
                        st.session_state.prof_edit_sucesso = f"Usuário {user_selecionado} excluído com sucesso!"
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao excluir: {e}")

        with tab4:
            st.subheader("Alterar Senha de Usuário")
            
            lista_usuarios = df_profs['Usuario'].tolist()
            user_alvo = st.selectbox("Selecione o Usuário", [""] + lista_usuarios)
            nova_senha_input = st.text_input("Nova Senha", type="password")
            confirmar_senha = st.text_input("Confirmar Nova Senha", type="password")
            
            col_senha1, col_senha2 = st.columns([1, 2])
            with col_senha1:
                btn_senha = st.button("Atualizar Senha")
            
            if btn_senha:
                if not user_alvo:
                    st.error("Selecione um usuário.")
                elif nova_senha_input != confirmar_senha:
                    st.error("As senhas não coincidem.")
                else:
                    try:
                        sh = conectar_google_sheets()
                        wks_p = sh.worksheet("Config_Professores")
                        celula = wks_p.find(str(user_alvo))
                        wks_p.update_cell(celula.row, 3, str(nova_senha_input))
                        with col_senha2:
                            st.success(f"✅ Senha de {user_alvo} atualizada!")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Erro ao atualizar: {e}")

        with tab5:
            st.subheader("Configurar Período de Lançamento")
            
            placeholder_per = st.empty()
            if 'per_sucesso' in st.session_state:
                placeholder_per.markdown(f"<h3 style='color: #28a745; text-align: center;'>{st.session_state.per_sucesso}</h3>", unsafe_allow_html=True)
                time.sleep(3)
                placeholder_per.empty()
                del st.session_state.per_sucesso

            with st.form("form_periodo"):
                bim_sel = st.selectbox("Bimestre", ["1º Bimestre", "2º Bimestre", "3º Bimestre", "4º Bimestre"])
                data_inicio = st.date_input("Início do Lançamento", format="DD/MM/YYYY")
                data_fim = st.date_input("Fim do Lançamento", format="DD/MM/YYYY")
                
                if st.form_submit_button("Salvar Período"):
                    try:
                        sh = conectar_google_sheets()
                        try:
                            wks_per = sh.worksheet("Config_Periodos")
                        except:
                            wks_per = sh.add_worksheet(title="Config_Periodos", rows="10", cols="3")
                            wks_per.append_row(["Bimestre", "Inicio", "Fim"])
                        
                        data_per = wks_per.get_all_values()
                        found = False
                        
                        inicio_str = data_inicio.strftime("%d/%m/%Y")
                        fim_str = data_fim.strftime("%d/%m/%Y")
                        
                        for i, row in enumerate(data_per):
                            if row[0] == bim_sel:
                                wks_per.update_cell(i + 1, 2, inicio_str)
                                wks_per.update_cell(i + 1, 3, fim_str)
                                found = True
                                break
                        
                        if not found:
                            wks_per.append_row([bim_sel, inicio_str, fim_str])
                            
                        st.session_state.per_sucesso = f"Período do {bim_sel} configurado com sucesso!"
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar período: {e}")
            
            st.divider()
            st.subheader("Períodos Configurados")
            if not df_periodos.empty:
                st.dataframe(df_periodos, use_container_width=True)
                
                placeholder_per_del = st.empty()
                if 'per_del_sucesso' in st.session_state:
                    placeholder_per_del.markdown(f"<h3 style='color: #28a745; text-align: center;'>{st.session_state.per_del_sucesso}</h3>", unsafe_allow_html=True)
                    time.sleep(3)
                    placeholder_per_del.empty()
                    del st.session_state.per_del_sucesso

                if st.button("Limpar Todos os Períodos"):
                    try:
                        sh = conectar_google_sheets()
                        wks_per = sh.worksheet("Config_Periodos")
                        rows = len(wks_per.get_all_values())
                        if rows > 1:
                            wks_per.delete_rows(2, rows)
                            st.session_state.per_del_sucesso = "Todos os períodos foram removidos com sucesso!"
                            st.cache_data.clear()
                            st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")
            else:
                st.info("Nenhum período configurado.")
    
    elif st.session_state.pagina == "Cadastro":
        st.error("Acesso restrito.")
        st.session_state.pagina = "Registro"
        st.rerun()
