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
            if len(bimestres_disponiveis) > 1:
                bimestre_ativo = st.selectbox("📅 Mais de um período aberto. Selecione o Bimestre:", bimestres_disponiveis)
            else:
                bimestre_ativo = bimestres_disponiveis[0]
                st.info(f"📅 Período de lançamento aberto: **{bimestre_ativo}**")

        if st.session_state.user_data['Usuario'] == "admin":
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
            
            # Atualizado: Nome do campo alterado para "Situação do Aluno"
            situacao_aluno = st.selectbox("Situação do Aluno", ["Não se aplica", "Reprovado", "Aprovado após recuperação"])
            
            valores_atitudes = st.multiselect("Valores e atitudes", ["Indisciplinado (a)", "Não traz material", "Não realiza tarefa em sala", "Não realiza tarefa em casa", "Muitas faltas"])
            obs = st.text_area("Observações")
            
            col_salvar, col_mensagem = st.columns([1, 2])
            with col_salvar:
                btn_salvar = st.form_submit_button("GRAVAR NA PLANILHA", disabled=(bimestre_ativo == "Bloqueado"))

        if btn_salvar:
            if not valores_atitudes and situacao_aluno == "Não se aplica":
                with col_mensagem:
                    placeholder_erro = st.empty()
                    placeholder_erro.error("Selecione a Situação do Aluno ou pelo menos um item de Valores e Atitudes.")
                    time.sleep(3)
                    placeholder_erro.empty()
            else:
                try:
                    sh = conectar_google_sheets()
                    wks = sh.worksheet("Registros_Ocorrencias")
                    
                    valores_formatados = ", ".join(valores_atitudes)
                    
                    # Ordem das colunas: Data, Professor, Turma, Aluno, Disciplina, Bimestre, Situação do Aluno, Valores e Atitudes, Obs
                    nova_linha = [
                        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                        prof_nome,
                        turma_sel,
                        aluno_sel,
                        disciplina,
                        periodo,
                        situacao_aluno,
                        valores_formatados,
                        obs
                    ]
                    
                    wks.append_row(nova_linha)
                    with col_mensagem:
                        placeholder_sucesso = st.empty()
                        placeholder_sucesso.success(f"✅ Sucesso! Registro salvo.")
                        time.sleep(3)
                        placeholder_sucesso.empty()
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
                
                col_data = colunas_df[0]

                # Mapeamento para garantir que as novas colunas apareçam na visualização
                mapeamento_colunas = {
                    colunas_df[2]: "Turma",
                    colunas_df[3]: "Aluno",
                    colunas_df[5]: "Periodo",
                    colunas_df[4]: "Disciplina",
                    colunas_df[1]: "Professor",
                    colunas_df[6]: "Situação do Aluno",
                    colunas_df[7]: "Valores e Atitudes",
                    colunas_df[8]: "Descrição_Detalhada"
                }
                
                df_exibicao = df_filtrado.rename(columns=mapeamento_colunas)
                df_exibicao["Disciplina / Prof."] = df_exibicao["Disciplina"].astype(str) + " (" + df_exibicao["Professor"].astype(str) + ")"
                df_exibicao = df_exibicao.sort_values(by=["Periodo", "Turma", "Aluno"])
                
                # Definindo a ordem das colunas para incluir as duas solicitadas
                ordem_colunas = ["Turma", "Aluno", "Periodo", "Disciplina / Prof.", "Situação do Aluno", "Valores e Atitudes", "Descrição_Detalhada"]
                df_exibicao = df_exibicao[ordem_colunas]
                
                column_config = {
                    "Turma": st.column_config.TextColumn("Turma", width=50),
                    "Periodo": st.column_config.TextColumn("Periodo", width=65),
                    "Situação do Aluno": st.column_config.TextColumn("Situação do Aluno", width=150),
                    "Valores e Atitudes": st.column_config.TextColumn("Valores e Atitudes", width=200)
                }
                
                st.dataframe(df_exibicao, use_container_width=True, hide_index=True, column_config=column_config)

                st.divider()
                st.subheader("🗑️ Gerenciar Exclusões")
                
                col_exc1, col_exc2 = st.columns(2)
                
                with col_exc1:
                    st.markdown("**Excluir registro único**")
                    if not df_filtrado.empty:
                        opcoes_excluir = {f"{row[col_data]} - {row[colunas_df[3]]}": row['ID_Original'] for _, row in df_filtrado.iterrows()}
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

    # --- O restante do código de Segurança e Cadastro permanece inalterado ---
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
                    with col_senha_p2:
                        st.error("As senhas não coincidem.")
                else:
                    try:
                        sh = conectar_google_sheets()
                        wks_p = sh.worksheet("Config_Professores")
                        celula = wks_p.find(str(user_atual))
                        wks_p.update_cell(celula.row, 3, str(nova_senha_prof))
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
                with st.form("form_aluno", clear_on_submit=True):
                    nova_turma = st.text_input("Turma (Ex: 101, 202)")
                    novo_aluno = st.text_input("Nome Completo do Aluno")
                    if st.form_submit_button("Salvar Aluno"):
                        try:
                            sh = conectar_google_sheets()
                            wks_a = sh.worksheet("Config_Alunos")
                            wks_a.append_row([nova_turma, novo_aluno])
                            st.success("Aluno cadastrado!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e: st.error(e)
            
            elif opcao_cadastro == "Em Massa (Excel/Word)":
                with st.form("form_aluno_massa", clear_on_submit=True):
                    turma_massa = st.text_input("Turma")
                    lista_nomes = st.text_area("Nomes (um por linha)")
                    if st.form_submit_button("Salvar Todos"):
                        try:
                            nomes = [[turma_massa, n.strip()] for n in lista_nomes.split('\n') if n.strip()]
                            sh = conectar_google_sheets(); wks_a = sh.worksheet("Config_Alunos")
                            wks_a.append_rows(nomes)
                            st.success("Alunos cadastrados!"); st.cache_data.clear(); st.rerun()
                        except Exception as e: st.error(e)

        # (Continuação padrão das abas de cadastro...)
        with tab2:
            st.subheader("Gerenciar Disciplinas")
            with st.form("form_disciplina", clear_on_submit=True):
                nova_disc = st.text_input("Nome da Disciplina")
                if st.form_submit_button("Cadastrar Disciplina"):
                    try:
                        sh = conectar_google_sheets(); wks_d = sh.worksheet("Config_Disciplinas")
                        wks_d.append_row([nova_disc])
                        st.success("Disciplina cadastrada!"); st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(e)

        with tab3:
            st.subheader("Cadastrar Novo Professor")
            with st.form("form_prof", clear_on_submit=True):
                n_prof = st.text_input("Nome Professor"); n_user = st.text_input("Login"); n_pass = st.text_input("Senha", type="password")
                if st.form_submit_button("Salvar Professor"):
                    try:
                        sh = conectar_google_sheets(); wks_p = sh.worksheet("Config_Professores")
                        wks_p.append_row([n_prof, n_user, n_pass, "", ""])
                        st.success("Professor cadastrado!"); st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(e)

        with tab5:
            st.subheader("Configurar Período de Lançamento")
            with st.form("form_periodo"):
                b_sel = st.selectbox("Bimestre", ["1º Bimestre", "2º Bimestre", "3º Bimestre", "4º Bimestre"])
                d_ini = st.date_input("Início"); d_fim = st.date_input("Fim")
                if st.form_submit_button("Salvar Período"):
                    try:
                        sh = conectar_google_sheets(); wks_per = sh.worksheet("Config_Periodos")
                        wks_per.append_row([b_sel, d_ini.strftime("%d/%m/%Y"), d_fim.strftime("%d/%m/%Y")])
                        st.success("Período salvo!"); st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(e)

    elif st.session_state.pagina == "Cadastro":
        st.error("Acesso restrito.")
        st.session_state.pagina = "Registro"
        st.rerun()
