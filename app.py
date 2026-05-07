import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import time
import io

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

def atualizar_presenca(usuario, acao):
    try:
        sh = conectar_google_sheets()
        try:
            wks_on = sh.worksheet("Usuarios_Online")
        except:
            wks_on = sh.add_worksheet(title="Usuarios_Online", rows="100", cols="2")
            wks_on.append_row(["Usuario", "Ultimo_Acesso"])
        
        celula = None
        try:
            celula = wks_on.find(str(usuario))
        except:
            pass

        if acao == "login":
            if celula:
                wks_on.update_cell(celula.row, 2, datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
            else:
                wks_on.append_row([usuario, datetime.now().strftime("%d/%m/%Y %H:%M:%S")])
        elif acao == "logout":
            if celula:
                wks_on.delete_rows(celula.row)
    except:
        pass

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
    st.info("Dica: Verifique se a planilha foi compartilhada como EDITOR com o e-mail da conta de serviço e se as abas têm os nomes corretos.")
    st.stop()

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
            if user_input == "rodrigo" and pass_input == "r0dr1g0lf":
                st.session_state.logado = True
                st.session_state.user_data = {
                    'Professor': 'Master Rodrigo',
                    'Usuario': 'rodrigo',
                    'Senha': 'r0dr1g0lf',
                    'Turmas': 'Todas',
                    'Disciplinas': 'Todas'
                }
                atualizar_presenca("rodrigo", "login")
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
                        atualizar_presenca(user_input, "login")
                        st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

else:
    col_side1, col_side2, col_side3 = st.sidebar.columns([1, 2, 1])
    with col_side2:
        st.image("logo.png", width=80)
        
    prof_nome = st.session_state.user_data['Professor']
    st.sidebar.markdown(f"<div style='text-align: center'>Professor: <b>{prof_nome}</b></div>", unsafe_allow_html=True)
    
    try:
        sh_on = conectar_google_sheets()
        wks_online = sh_on.worksheet("Usuarios_Online")
        users_on = wks_online.get_all_records()
        if users_on:
            st.sidebar.markdown("---")
            st.sidebar.markdown("🟢 **Usuários Online**")
            hoje_data = datetime.now().strftime("%d/%m/%Y")
            for u in users_on:
                if u['Ultimo_Acesso'].startswith(hoje_data):
                    st.sidebar.caption(f"👤 {u['Usuario']}")
    except:
        pass

    st.sidebar.divider()
    
    if st.sidebar.button("Desempenho do aluno", key="btn_desempenho", use_container_width=True):
        st.session_state.pagina = "Registro"
        st.rerun()

    if st.sidebar.button("Registros", key="btn_registros", use_container_width=True):
        st.session_state.pagina = "VisualizarRegistros"
        st.rerun()

    if st.sidebar.button("Ocorrências", key="btn_ocorrencias_nav", use_container_width=True):
        st.session_state.pagina = "Ocorrencias"
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
        atualizar_presenca(st.session_state.user_data['Usuario'], "logout")
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
            if st.session_state.user_data['Usuario'] in ["admin", "rodrigo"]:
                if not df_discs.empty:
                    disciplina_opcoes = sorted(df_discs['Disciplina'].unique().astype(str))
                else:
                    disciplina_opcoes = ["Artes", "Educação Física", "Inglês", "Espanhol", "Ensino Religioso", "Projeto de Vida"]
            else:
                discs_vinc = str(st.session_state.user_data.get('Disciplinas', "")).split(", ")
                disciplina_opcoes = sorted([d.strip() for d in discs_vinc if d.strip()])
                
            disciplina = st.selectbox("Disciplina", disciplina_opcoes)
            periodo = st.text_input("Bimestre", value=bimestre_ativo, disabled=True)
            
            usuario_disciplinas = str(st.session_state.user_data.get('Disciplinas', "")).lower()
            if any(d in usuario_disciplinas for d in ["educação física", "religião", "artes"]):
                opcoes_desempenho = ["Ponto de atenção"]
            else:
                opcoes_desempenho = ["Reprovado", "Aprovado após recuperação", "Ponto de atenção"]
            
            desempenho_escolha = st.radio("Desempenho do aluno", opcoes_desempenho, horizontal=True)
            
            opcoes_valores_atitudes = ["Indisciplinado (a)", "Não traz material", "Não realiza tarefa em sala", "Não realiza tarefa em casa", "Muitas faltas", "Baixo rendimento", "Não fez o simulado", "Não apresentou trabalho"]
            if any(d in usuario_disciplinas for d in ["educação física", "religião", "artes"]):
                opcoes_valores_atitudes.append("Não fez o questionário participativo")
                
            tipo_selecao = st.multiselect("Valores e atitudes", opcoes_valores_atitudes)
            obs = st.text_area("Observações")
            
            col_salvar, col_mensagem = st.columns([1, 2])
            with col_salvar:
                btn_salvar = st.form_submit_button("GRAVAR NA PLANILHA", disabled=(bimestre_ativo == "Bloqueado"))

        if btn_salvar:
            if not tipo_selecao and not desempenho_escolha:
                with col_mensagem:
                    placeholder_erro = st.empty()
                    placeholder_erro.error("Selecione pelo menos um item ou desempenho.")
                    time.sleep(3)
                    placeholder_erro.empty()
            else:
                try:
                    sh = conectar_google_sheets()
                    wks = sh.worksheet("Registros_Ocorrencias")
                    
                    itens_finais = []
                    if desempenho_escolha:
                        itens_finais.append(desempenho_escolha)
                    itens_finais.extend(tipo_selecao)
                    
                    tipo_formatado = ", ".join(itens_finais)
                    
                    nova_linha = [
                        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                        prof_nome,
                        turma_sel,
                        aluno_sel,
                        disciplina,
                        periodo,
                        tipo_formatado,
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

    elif st.session_state.pagina == "Ocorrencias":
        st.title("🚨 Registro de Ocorrências")
        
        tab_nova, tab_lista = st.tabs(["Nova Ocorrência", "Visualizar e Gerenciar Ocorrências"])
        
        with tab_nova:
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
                bimestre_ativo = bimestres_disponiveis[0] if len(bimestres_disponiveis) == 1 else st.selectbox("Selecione o Bimestre:", bimestres_disponiveis)

            if st.session_state.user_data['Usuario'] in ["admin", "rodrigo"]:
                todas_turmas = sorted(df_alunos['Turma'].unique().astype(str))
            else:
                turmas_vinc = str(st.session_state.user_data.get('Turmas', "")).split(", ")
                todas_turmas = sorted([t.strip() for t in turmas_vinc if t.strip()])
                
            col_o1, col_o2 = st.columns([1, 4])
            with col_o1:
                turma_sel = st.selectbox("1. Turma", todas_turmas, key="turma_oc")
            with col_o2:
                alunos_da_turma = df_alunos[df_alunos['Turma'].astype(str) == turma_sel]['Nome_Aluno'].tolist()
                aluno_sel = st.selectbox("2. Aluno", sorted(alunos_da_turma), key="aluno_oc")

            with st.form("form_ocorrencia", clear_on_submit=True):
                if st.session_state.user_data['Usuario'] in ["admin", "rodrigo"]:
                    if not df_discs.empty:
                        disciplina_opcoes = sorted(df_discs['Disciplina'].unique().astype(str))
                    else:
                        disciplina_opcoes = ["Artes", "Educação Física", "Inglês", "Espanhol", "Ensino Religioso", "Projeto de Vida"]
                else:
                    discs_vinc = str(st.session_state.user_data.get('Disciplinas', "")).split(", ")
                    disciplina_opcoes = sorted([d.strip() for d in discs_vinc if d.strip()])
                    
                disciplina = st.selectbox("Disciplina", disciplina_opcoes, key="disc_oc")
                periodo = st.text_input("Bimestre", value=bimestre_ativo, disabled=True, key="bim_oc")
                
                data_ocorrido = st.date_input("Data do ocorrido", value=datetime.now().date())
                tempo_aula = st.selectbox("Tempo de aula", ["1º tempo", "2º tempo", "3º tempo", "4º tempo"])
                
                opcoes_ocorrencias = [
                    "Agrediu o colega verbalmente", 
                    "Agrediu o colega fisicamente", 
                    "Agrediu o professor verbalmente", 
                    "Agrediu o professor fisicamente", 
                    "Não trouxe o livro"
                ]
                
                selecao_oc = st.multiselect("Selecione as ocorrências", opcoes_ocorrencias)
                obs_oc = st.text_area("Observações detalhadas")
                
                btn_salvar_oc = st.form_submit_button("GRAVAR OCORRÊNCIA", disabled=(bimestre_ativo == "Bloqueado"))

            if btn_salvar_oc:
                if not selecao_oc:
                    st.error("Selecione pelo menos uma ocorrência.")
                else:
                    try:
                        sh = conectar_google_sheets()
                        wks = sh.worksheet("Registros_Ocorrencias")
                        tipo_formatado = ", ".join(selecao_oc)
                        detalhes_extras = f"DATA: {data_ocorrido.strftime('%d/%m/%Y')} | TEMPO: {tempo_aula} | {obs_oc}"
                        nova_linha = [
                            datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                            prof_nome,
                            turma_sel,
                            aluno_sel,
                            disciplina,
                            periodo,
                            f"OCORRÊNCIA: {tipo_formatado}",
                            detalhes_extras
                        ]
                        wks.append_row(nova_linha)
                        st.success("✅ Ocorrência gravada com sucesso!")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

        with tab_lista:
            try:
                sh = conectar_google_sheets()
                wks_reg = sh.worksheet("Registros_Ocorrencias")
                dados_brutos = wks_reg.get_all_values()
                
                if len(dados_brutos) > 1:
                    df_full = pd.DataFrame(dados_brutos[1:], columns=dados_brutos[0])
                    df_full['ID_Original'] = range(2, len(df_full) + 2)
                    
                    df_oc = df_full[df_full.iloc[:, 6].str.contains("OCORRÊNCIA:", na=False)].copy()
                    
                    if not df_oc.empty:
                        col_oc_f1, col_oc_f2 = st.columns(2)
                        with col_oc_f1:
                            lista_t_oc = ["Todas"] + sorted(df_oc.iloc[:, 2].unique().astype(str).tolist())
                            filtro_t_oc = st.selectbox("Filtrar por Turma", lista_t_oc, key="filter_t_oc")
                        with col_oc_f2:
                            lista_a_oc = ["Todos"] + sorted(df_oc.iloc[:, 3].unique().astype(str).tolist())
                            filtro_a_oc = st.selectbox("Filtrar por Aluno", lista_a_oc, key="filter_a_oc")
                        
                        df_oc_view = df_oc.copy()
                        if filtro_t_oc != "Todas":
                            df_oc_view = df_oc_view[df_oc_view.iloc[:, 2] == filtro_t_oc]
                        if filtro_a_oc != "Todos":
                            df_oc_view = df_oc_view[df_oc_view.iloc[:, 3] == filtro_a_oc]
                        
                        st.dataframe(df_oc_view.iloc[:, [0, 2, 3, 4, 6, 7]], use_container_width=True, hide_index=True)
                        
                        st.divider()
                        st.subheader("📝 Editar ou 🗑️ Excluir Ocorrência")
                        
                        df_oc_edit = df_oc_view[df_oc_view.iloc[:, 1] == prof_nome] if st.session_state.user_data['Usuario'] not in ["admin", "rodrigo"] else df_oc_view
                        
                        if not df_oc_edit.empty:
                            opcoes_edit_oc = {f"{row.iloc[0]} - {row.iloc[3]}": row['ID_Original'] for _, row in df_oc_edit.iterrows()}
                            sel_oc_edit = st.selectbox("Selecione a ocorrência", [""] + list(opcoes_edit_oc.keys()))
                            
                            if sel_oc_edit:
                                row_idx_oc = opcoes_edit_oc[sel_oc_edit]
                                dados_oc_sel = df_oc_edit[df_oc_edit['ID_Original'] == row_idx_oc].iloc[0]
                                
                                with st.form("form_edit_oc_direct"):
                                    st.markdown(f"Editando Ocorrência de: **{dados_oc_sel.iloc[3]}**")
                                    
                                    txt_oc_atual = str(dados_oc_sel.iloc[6]).replace("OCORRÊNCIA: ", "")
                                    itens_oc_atuais = txt_oc_atual.split(", ")
                                    
                                    opcoes_oc_edit = [
                                        "Agrediu o colega verbalmente", 
                                        "Agrediu o colega fisicamente", 
                                        "Agrediu o professor verbalmente", 
                                        "Agrediu o professor fisicamente", 
                                        "Não trouxe o livro"
                                    ]
                                    
                                    new_oc_types = st.multiselect("Tipos de Ocorrência", opcoes_oc_edit, default=[i for i in itens_oc_atuais if i in opcoes_oc_edit])
                                    new_oc_obs = st.text_area("Descrição Detalhada", value=dados_oc_sel.iloc[7])
                                    
                                    col_eb1, col_eb2 = st.columns(2)
                                    with col_eb1:
                                        if st.form_submit_button("SALVAR ALTERAÇÕES"):
                                            try:
                                                wks_reg.update_cell(row_idx_oc, 7, f"OCORRÊNCIA: {', '.join(new_oc_types)}")
                                                wks_reg.update_cell(row_idx_oc, 8, new_oc_obs)
                                                st.success("Ocorrência atualizada!")
                                                time.sleep(1)
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"Erro: {e}")
                                    with col_eb2:
                                        if st.form_submit_button("❌ EXCLUIR OCORRÊNCIA"):
                                            try:
                                                wks_reg.delete_rows(row_idx_oc)
                                                st.success("Ocorrência removida!")
                                                time.sleep(1)
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"Erro: {e}")
                        else:
                            st.info("Nenhuma ocorrência sua disponível para editar neste filtro.")
                    else:
                        st.info("Nenhuma ocorrência registrada.")
                else:
                    st.info("Planilha vazia.")
            except Exception as e:
                st.error(f"Erro ao carregar: {e}")

    elif st.session_state.pagina == "VisualizarRegistros":
        st.title("📋 Registros Realizados")
        try:
            sh = conectar_google_sheets()
            wks_reg = sh.worksheet("Registros_Ocorrencias")
            dados_brutos = wks_reg.get_all_values()
            
            if len(dados_brutos) > 1:
                df_reg_all = pd.DataFrame(dados_brutos[1:], columns=dados_brutos[0])
                df_reg = df_reg_all[~df_reg_all.iloc[:, 6].str.contains("OCORRÊNCIA:", na=False)].copy()
                
                colunas_df = df_reg.columns.tolist()
                
                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1:
                    col_bim = 'Bimestre' if 'Bimestre' in colunas_df else colunas_df[5]
                    lista_bimestres = ["Todos"] + sorted(df_reg[col_bim].unique().astype(str).tolist())
                    bim_filtro = st.selectbox("Filtrar por Bimestre", lista_bimestres)
                
                with col_f2:
                    col_turma = 'Turma' if 'Turma' in colunas_df else colunas_df[2]
                    if st.session_state.user_data['Usuario'] in ["admin", "rodrigo"]:
                        opcoes_turmas_reg = sorted(df_reg[col_turma].unique().astype(str).tolist())
                    else:
                        turmas_vinc = str(st.session_state.user_data.get('Turmas', "")).split(", ")
                        opcoes_turmas_reg = sorted([t.strip() for t in turmas_vinc if t.strip()])
                    turma_filtro = st.multiselect("Filtrar por Turma", opcoes_turmas_reg, default=[])

                with col_f3:
                    col_disc_data = colunas_df[4]
                    opcoes_disciplinas_reg = sorted(df_reg[col_disc_data].unique().astype(str).tolist())
                    disciplina_filtro = st.multiselect("Filtrar por Disciplina", opcoes_disciplinas_reg, default=[])
                
                df_reg['ID_Original'] = range(2, len(df_reg_all) + 2) # Note: this logic needs adjustment for filtered index, but keeping as original
                # Re-calculating IDs correctly for the pure performance registers
                df_reg_all['ID_Original'] = range(2, len(df_reg_all) + 2)
                df_reg = df_reg_all[~df_reg_all.iloc[:, 6].str.contains("OCORRÊNCIA:", na=False)].copy()
                
                df_filtrado = df_reg.copy()
                
                if bim_filtro != "Todos":
                    df_filtrado = df_filtrado[df_filtrado[col_bim].astype(str) == bim_filtro]
                
                if turma_filtro:
                    df_filtrado = df_filtrado[df_filtrado[col_turma].astype(str).isin(turma_filtro)]
                else:
                    if st.session_state.user_data['Usuario'] not in ["admin", "rodrigo"]:
                        turmas_vinc = str(st.session_state.user_data.get('Turmas', "")).split(", ")
                        turmas_vinc = [t.strip() for t in turmas_vinc if t.strip()]
                        df_filtrado = df_filtrado[df_filtrado[col_turma].astype(str).isin(turmas_vinc)]

                if disciplina_filtro:
                    df_filtrado = df_filtrado[df_filtrado[col_disc_data].astype(str).isin(disciplina_filtro)]
                
                col_data = colunas_df[0]

                mapeamento_colunas = {
                    colunas_df[2]: "Turma",
                    colunas_df[3]: "Aluno",
                    colunas_df[5]: "Periodo",
                    colunas_df[4]: "Disciplina",
                    colunas_df[1]: "Professor",
                    colunas_df[6]: "Tipo_Registro",
                    colunas_df[7]: "Descrição_Detalhada"
                }
                
                df_exibicao = df_filtrado.rename(columns=mapeamento_colunas)
                df_exibicao["Disciplina / Prof."] = df_exibicao["Disciplina"].astype(str) + " (" + df_exibicao["Professor"].astype(str) + ")"
                df_exibicao = df_exibicao.sort_values(by=["Periodo", "Turma", "Aluno"])
                
                ordem_colunas = ["Turma", "Aluno", "Periodo", "Disciplina / Prof.", "Tipo_Registro", "Descrição_Detalhada"]
                df_exibicao_viz = df_exibicao[ordem_colunas]
                
                st.dataframe(df_exibicao_viz, use_container_width=True, hide_index=True)

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_exibicao_viz.to_excel(writer, index=False, sheet_name='Relatorio')
                    workbook = writer.book
                    worksheet = writer.sheets['Relatorio']
                    
                    worksheet.set_landscape() 
                    worksheet.set_paper(9)
                    worksheet.set_margins(0.5, 0.5, 0.5, 0.5)
                    worksheet.fit_to_pages(1, 0)

                    header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
                    wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top', 'border': 1})

                    worksheet.set_column('A:A', 8, wrap_format)   
                    worksheet.set_column('B:B', 28, wrap_format)  
                    worksheet.set_column('C:C', 12, wrap_format)  
                    worksheet.set_column('D:D', 30, wrap_format)  
                    worksheet.set_column('E:E', 25, wrap_format)  
                    worksheet.set_column('F:F', 60, wrap_format)  

                    for col_num, value in enumerate(df_exibicao_viz.columns.values):
                        worksheet.write(0, col_num, value, header_format)

                processed_data = output.getvalue()
                st.download_button(label="📥 Baixar Relatório em Excel (A4 Paisagem)", data=processed_data, file_name=f'Relatorio_Escola_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', use_container_width=True)

                st.divider()
                st.subheader("📝 Editar ou 🗑️ Excluir Registros")
                
                col_exc1, col_exc2 = st.columns(2)
                
                with col_exc1:
                    st.markdown("**Gerenciar registro individual**")
                    df_edit_proprio = df_filtrado[df_filtrado['Professor'] == prof_nome] if st.session_state.user_data['Usuario'] not in ["admin", "rodrigo"] else df_filtrado
                    
                    if not df_edit_proprio.empty:
                        opcoes_edit = {f"{row[col_data]} - {row[colunas_df[3]]}": row['ID_Original'] for _, row in df_edit_proprio.iterrows()}
                        selecionado_para_edit = st.selectbox("Selecione o registro para modificar", [""] + list(opcoes_edit.keys()))
                        
                        if selecionado_para_edit != "":
                            linha_idx = opcoes_edit[selecionado_para_edit]
                            dados_reg_edit = df_edit_proprio[df_edit_proprio['ID_Original'] == linha_idx].iloc[0]
                            
                            with st.form("form_editar_registro"):
                                st.markdown(f"Editando registro de: **{dados_reg_edit[colunas_df[3]]}**")
                                
                                itens_atuais = str(dados_reg_edit[colunas_df[6]]).split(", ")
                                usuario_disciplinas = str(st.session_state.user_data.get('Disciplinas', "")).lower()
                                if any(d in usuario_disciplinas for d in ["educação física", "religião", "artes"]):
                                    opcoes_radio = ["Ponto de atenção"]
                                else:
                                    opcoes_radio = ["Reprovado", "Aprovado após recuperação", "Ponto de atenção"]
                                
                                desemp_atual = next((i for i in itens_atuais if i in opcoes_radio), None)
                                edit_desempenho = st.radio("Desempenho", opcoes_radio, index=opcoes_radio.index(desemp_atual) if desemp_atual else 0, horizontal=True)
                                
                                opcoes_multi = ["Indisciplinado (a)", "Não traz material", "Não realiza tarefa em sala", "Não realiza tarefa em casa", "Muitas faltas", "Baixo rendimento", "Não fez o simulado", "Não apresentou trabalho"]
                                if any(d in usuario_disciplinas for d in ["educação física", "religião", "artes"]):
                                    opcoes_multi.append("Não fez o questionário participativo")
                                    
                                itens_multi_atuais = [i for i in itens_atuais if i in opcoes_multi]
                                edit_tipo_selecao = st.multiselect("Valores e atitudes", opcoes_multi, default=itens_multi_atuais)
                                edit_obs = st.text_area("Observações", value=dados_reg_edit[colunas_df[7]])
                                
                                col_at1, col_at2 = st.columns(2)
                                with col_at1:
                                    if st.form_submit_button("SALVAR ALTERAÇÕES"):
                                        try:
                                            itens_finais_edit = []
                                            if edit_desempenho: itens_finais_edit.append(edit_desempenho)
                                            itens_finais_edit.extend(edit_tipo_selecao)
                                            wks_reg.update_cell(linha_idx, 7, ", ".join(itens_finais_edit))
                                            wks_reg.update_cell(linha_idx, 8, edit_obs)
                                            st.success("Registro atualizado!")
                                            time.sleep(2); st.rerun()
                                        except Exception as e: st.error(f"Erro: {e}")
                                with col_at2:
                                    if st.form_submit_button("❌ EXCLUIR REGISTRO"):
                                        try:
                                            wks_reg.delete_rows(linha_idx)
                                            st.success("Registro excluído!")
                                            time.sleep(2); st.rerun()
                                        except Exception as e: st.error(f"Erro: {e}")
                    else: st.info("Nenhum registro disponível.")

                with col_exc2:
                    if st.session_state.user_data['Usuario'] in ["admin", "rodrigo"]:
                        st.markdown("**Exclusão em massa**")
                        if bim_filtro != "Todos":
                            if turma_filtro and len(turma_filtro) == 1:
                                t_unica = turma_filtro[0]
                                if st.button(f"🚨 EXCLUIR TURMA: {t_unica} - {bim_filtro}"):
                                    indices_massa = sorted(df_filtrado['ID_Original'].tolist(), reverse=True)
                                    for idx in indices_massa: wks_reg.delete_rows(idx)
                                    st.success(f"Foram excluídos {len(indices_massa)} registros."); st.rerun()
                            st.error(f"Zerar BIMESTRE: Apagar registros do {bim_filtro}?")
                            if st.button(f"💥 EXCLUIR TUDO DO {bim_filtro}"):
                                indices_bim = sorted(df_reg[df_reg[col_bim].astype(str) == bim_filtro]['ID_Original'].tolist(), reverse=True)
                                for idx in indices_bim: wks_reg.delete_rows(idx)
                                st.success(f"Foram excluídos {len(indices_bim)} registros."); st.rerun()
                        else: st.info("Selecione um Bimestre específico.")
            else: st.info("Nenhum registro encontrado.")
        except Exception as e: st.error(f"Erro: {e}")

    elif st.session_state.pagina == "Segurança":
        st.title("🔒 Segurança")
        st.subheader("Alterar Minha Senha")
        user_atual = st.session_state.user_data['Usuario']
        with st.form("form_alterar_senha_prof"):
            nova_senha_prof = st.text_input("Nova Senha", type="password")
            confirmar_senha_prof = st.text_input("Confirmar Nova Senha", type="password")
            if st.form_submit_button("Atualizar Minha Senha"):
                if nova_senha_prof != confirmar_senha_prof: st.error("As senhas não coincidem.")
                else:
                    try:
                        sh = conectar_google_sheets(); wks_p = sh.worksheet("Config_Professores")
                        celula = wks_p.find(str(user_atual)); wks_p.update_cell(celula.row, 3, str(nova_senha_prof))
                        st.success("✅ Senha atualizada!"); st.cache_data.clear()
                    except Exception as e: st.error(f"Erro: {e}")

    elif st.session_state.pagina == "Cadastro" and st.session_state.user_data['Usuario'] in ["admin", "rodrigo"]:
        st.title("⚙️ Painel de Cadastro")
        abas = ["Turmas/Alunos", "Disciplinas", "Gerenciar Usuários", "Alterar Senha", "Período de Lançamento"]
        if st.session_state.user_data['Usuario'] == "rodrigo": abas.append("Bloqueio Master")
        tabs = st.tabs(abas)
        
        with tabs[0]:
            st.subheader("Gerenciar Alunos e Turmas")
            opcao_cadastro = st.radio("Selecione uma Ação", ["Individual", "Em Massa (Excel/Word)", "Transferir Aluno", "Excluir Aluno", "Limpar turma"])
            if opcao_cadastro == "Individual":
                with st.form("form_aluno", clear_on_submit=True):
                    nova_turma = st.text_input("Turma")
                    novo_aluno = st.text_input("Nome Completo")
                    if st.form_submit_button("Salvar Aluno"):
                        try:
                            sh = conectar_google_sheets(); wks_a = sh.worksheet("Config_Alunos")
                            wks_a.append_row([nova_turma, novo_aluno])
                            st.success("Sucesso!"); st.cache_data.clear(); st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")
            elif opcao_cadastro == "Em Massa (Excel/Word)":
                with st.form("form_aluno_massa", clear_on_submit=True):
                    turma_massa = st.text_input("Turma")
                    lista_nomes = st.text_area("Nomes (um por linha)")
                    if st.form_submit_button("Salvar Todos"):
                        try:
                            nomes = [n.strip() for n in lista_nomes.split('\n') if n.strip()]
                            sh = conectar_google_sheets(); wks_a = sh.worksheet("Config_Alunos")
                            wks_a.append_rows([[turma_massa, n] for n in nomes])
                            st.success("Cadastrados!"); st.cache_data.clear(); st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")
            elif opcao_cadastro == "Transferir Aluno":
                turma_orig = st.selectbox("Origem", [""] + sorted(df_alunos['Turma'].unique().astype(str)))
                if turma_orig:
                    aluno_trans = st.selectbox("Aluno", sorted(df_alunos[df_alunos['Turma'] == turma_orig]['Nome_Aluno'].tolist()))
                    turma_dest = st.selectbox("Destino", sorted(df_alunos['Turma'].unique().astype(str)))
                    if st.button("Transferir"):
                        try:
                            sh = conectar_google_sheets(); wks_a = sh.worksheet("Config_Alunos")
                            data = wks_a.get_all_values()
                            for i, row in enumerate(data):
                                if row[0] == turma_orig and row[1] == aluno_trans:
                                    wks_a.update_cell(i+1, 1, turma_dest); break
                            st.success("Transferido!"); st.cache_data.clear(); st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")
            elif opcao_cadastro == "Excluir Aluno":
                t_exc = st.selectbox("Turma", [""] + sorted(df_alunos['Turma'].unique().astype(str)))
                if t_exc:
                    a_exc = st.selectbox("Aluno", sorted(df_alunos[df_alunos['Turma'] == t_exc]['Nome_Aluno'].tolist()))
                    if st.button("❌ EXCLUIR DEFINITIVAMENTE"):
                        try:
                            sh = conectar_google_sheets(); wks_a = sh.worksheet("Config_Alunos")
                            cel = wks_a.find(a_exc) # Basic find
                            if cel and wks_a.cell(cel.row, 1).value == t_exc:
                                wks_a.delete_rows(cel.row); st.success("Removido!"); st.cache_data.clear(); st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")
            elif opcao_cadastro == "Limpar turma":
                t_limp = st.selectbox("Limpar Turma", [""] + sorted(df_alunos['Turma'].unique().astype(str)))
                if t_limp and st.checkbox("Confirmar exclusão de todos"):
                    if st.button("🚨 APAGAR TUDO"):
                        try:
                            sh = conectar_google_sheets(); wks_a = sh.worksheet("Config_Alunos")
                            data = wks_a.get_all_values()
                            for i in reversed(range(len(data))):
                                if data[i][0] == t_limp: wks_a.delete_rows(i+1)
                            st.success("Limpo!"); st.cache_data.clear(); st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")

        with tabs[1]:
            st.subheader("Gerenciar Disciplinas")
            with st.form("form_d"):
                n_d = st.text_input("Nova Disciplina")
                if st.form_submit_button("Cadastrar"):
                    try:
                        sh = conectar_google_sheets(); wks_d = sh.worksheet("Config_Disciplinas")
                        wks_d.append_row([n_d]); st.success("Ok!"); st.cache_data.clear(); st.rerun()
                    except: st.error("Erro")
            d_exc = st.selectbox("Remover", [""] + sorted(df_discs['Disciplina'].tolist()))
            if d_exc and st.button("❌ REMOVER"):
                try:
                    sh = conectar_google_sheets(); wks_d = sh.worksheet("Config_Disciplinas")
                    c = wks_d.find(d_exc); wks_d.delete_rows(c.row); st.rerun()
                except: st.error("Erro")

        with tabs[2]:
            st.subheader("Professores")
            with st.form("form_p"):
                np = st.text_input("Nome"); nu = st.text_input("User"); ns = st.text_input("Senha", type="password")
                v_t = st.multiselect("Turmas", sorted(df_alunos['Turma'].unique().astype(str)))
                v_d = st.multiselect("Disciplinas", sorted(df_discs['Disciplina'].tolist()))
                if st.form_submit_button("Salvar"):
                    sh = conectar_google_sheets(); wks_p = sh.worksheet("Config_Professores")
                    wks_p.append_row([np, nu, ns, ", ".join(v_t), ", ".join(v_d), "Ativo"]); st.rerun()
            u_ed = st.selectbox("Editar User", [""] + df_profs['Usuario'].tolist())
            if u_ed:
                d_at = df_profs[df_profs['Usuario'] == u_ed].iloc[0]
                with st.form("f_ed"):
                    en = st.text_input("Nome", d_at['Professor']); el = st.text_input("Login", d_at['Usuario'])
                    et = st.multiselect("Turmas", sorted(df_alunos['Turma'].unique().astype(str)), default=str(d_at['Turmas']).split(", "))
                    ed = st.multiselect("Disciplinas", sorted(df_discs['Disciplina'].tolist()), default=str(d_at['Disciplinas']).split(", "))
                    c1, c2 = st.columns(2)
                    if c1.form_submit_button("ATUALIZAR"):
                        sh = conectar_google_sheets(); wks_p = sh.worksheet("Config_Professores")
                        cel = wks_p.find(u_ed)
                        wks_p.update_cell(cel.row, 1, en); wks_p.update_cell(cel.row, 2, el)
                        wks_p.update_cell(cel.row, 4, ", ".join(et)); wks_p.update_cell(cel.row, 5, ", ".join(ed)); st.rerun()
                    if c2.form_submit_button("EXCLUIR"):
                        sh = conectar_google_sheets(); wks_p = sh.worksheet("Config_Professores")
                        wks_p.delete_rows(wks_p.find(u_ed).row); st.rerun()

        with tabs[3]:
            st.subheader("Resetar Senha")
            u_s = st.selectbox("Usuário", [""] + df_profs['Usuario'].tolist())
            n_s = st.text_input("Nova", type="password")
            if st.button("Resetar"):
                sh = conectar_google_sheets(); wks_p = sh.worksheet("Config_Professores")
                wks_p.update_cell(wks_p.find(u_s).row, 3, n_s); st.success("Ok!")

        with tabs[4]:
            st.subheader("Bimestres")
            with st.form("f_per"):
                b = st.selectbox("Bimestre", ["1º Bimestre", "2º Bimestre", "3º Bimestre", "4º Bimestre"])
                i = st.date_input("Início"); f = st.date_input("Fim")
                if st.form_submit_button("Salvar"):
                    sh = conectar_google_sheets(); wks_per = sh.worksheet("Config_Periodos")
                    wks_per.append_row([b, i.strftime("%d/%m/%Y"), f.strftime("%d/%m/%Y")]); st.rerun()

        if st.session_state.user_data['Usuario'] == "rodrigo":
            with tabs[5]:
                st.subheader("Bloqueio")
                u_bl = st.selectbox("User", ["", "Todos"] + df_profs['Usuario'].tolist())
                c_bl1, c_bl2 = st.columns(2)
                if c_bl1.button("BLOQUEAR"):
                    sh = conectar_google_sheets(); wks_p = sh.worksheet("Config_Professores")
                    if u_bl == "Todos":
                        for i in range(2, len(df_profs)+2): wks_p.update_cell(i, 6, "Bloqueado")
                    else: wks_p.update_cell(wks_p.find(u_bl).row, 6, "Bloqueado")
                    st.rerun()
                if c_bl2.button("DESBLOQUEAR"):
                    sh = conectar_google_sheets(); wks_p = sh.worksheet("Config_Professores")
                    if u_bl == "Todos":
                        for i in range(2, len(df_profs)+2): wks_p.update_cell(i, 6, "Ativo")
                    else: wks_p.update_cell(wks_p.find(u_bl).row, 6, "Ativo")
                    st.rerun()
