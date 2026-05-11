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

    is_soe = "SOE" in str(st.session_state.user_data.get('Disciplinas', ""))
    is_master = st.session_state.user_data['Usuario'] in ["admin", "rodrigo"]

    if is_soe or is_master:
        if st.sidebar.button("SOE", key="btn_soe_nav", use_container_width=True):
            st.session_state.pagina = "SOE"
            st.rerun()

    if not is_master:
        if st.sidebar.button("Segurança", key="btn_seguranca", use_container_width=True):
            st.session_state.pagina = "Segurança"
            st.rerun()

    if is_master:
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
        
        if is_soe and not is_master:
            st.info("Você está logado como SOE. Este módulo é apenas para visualização de períodos e turmas.")
        
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

        if is_master or (is_soe and st.session_state.pagina != "SOE"):
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
            if is_master:
                if not df_discs.empty:
                    disciplina_opcoes = sorted(df_discs['Disciplina'].unique().astype(str))
                else:
                    disciplina_opcoes = ["Artes", "Educação Física", "Inglês", "Espanhol", "Ensino Religioso", "Projeto de Vida", "SOE"]
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
            
            desempenho_escolha = st.radio("Desempenho do aluno", options=opcoes_desempenho, horizontal=True)
            
            opcoes_valores_atitudes = ["Indisciplinado (a)", "Não traz material", "Não realiza tarefa em sala", "Não realiza tarefa em casa", "Muitas faltas", "Baixo rendimento", "Não fez o simulado", "Não apresentou trabalho"]
            if any(d in usuario_disciplinas for d in ["educação física", "religião", "artes"]):
                opcoes_valores_atitudes.append("Não fez o questionário participativo")
                
            tipo_selecao = st.multiselect("Valores e atitudes", options=opcoes_valores_atitudes)
            obs = st.text_area("Observações")
            
            col_salvar, col_mensagem = st.columns([1, 2])
            with col_salvar:
                btn_salvar = st.form_submit_button("GRAVAR NA PLANILHA", disabled=(bimestre_ativo == "Bloqueado" or (is_soe and not is_master)))

        if btn_salvar:
            if is_soe and not is_master:
                st.error("Usuários SOE não possuem permissão para realizar registros neste módulo.")
            elif not tipo_selecao and not desempenho_escolha:
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

    elif st.session_state.pagina in ["Ocorrencias", "SOE"]:
        titulo_pag = "🚨 Registro de Ocorrências" if st.session_state.pagina == "Ocorrencias" else "🏢 Módulo SOE"
        st.title(titulo_pag)
        tab_oc1, tab_oc2 = st.tabs(["Nova Ocorrência", "Visualizar Ocorrências"])
        
        # Define se pode editar/salvar (SOE pode no módulo SOE, master pode sempre)
        pode_editar_soe = (st.session_state.pagina == "SOE" and (is_soe or is_master))
        pode_editar_geral = (st.session_state.pagina == "Ocorrencias" and not is_soe) or is_master
        permissao_final = pode_editar_soe or pode_editar_geral

        with tab_oc1:
            if is_soe and st.session_state.pagina == "Ocorrencias" and not is_master:
                st.info("Você está logado como SOE. Este módulo é apenas para visualização. Para registrar use o botão SOE na lateral.")
            
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
                bimestre_ativo = bimestres_disponiveis[0] if len(bimestres_disponiveis) == 1 else st.selectbox("Selecione o Bimestre:", bimestres_disponiveis, key="sb_bim_soe")

            if is_master or (is_soe and st.session_state.pagina == "SOE"):
                todas_turmas = sorted(df_alunos['Turma'].unique().astype(str))
            else:
                turmas_vinc = str(st.session_state.user_data.get('Turmas', "")).split(", ")
                todas_turmas = sorted([t.strip() for t in turmas_vinc if t.strip()])
                
            col_o1, col_o2 = st.columns([1, 4])
            with col_o1:
                turma_sel = st.selectbox("1. Turma", todas_turmas, key="turma_oc_soe")
            with col_o2:
                alunos_da_turma = df_alunos[df_alunos['Turma'].astype(str) == turma_sel]['Nome_Aluno'].tolist()
                aluno_sel = st.selectbox("2. Aluno", sorted(alunos_da_turma), key="aluno_oc_soe")

            with st.form("form_ocorrencia_soe", clear_on_submit=True):
                if is_master:
                    if not df_discs.empty:
                        disciplina_opcoes = sorted(df_discs['Disciplina'].unique().astype(str))
                    else:
                        disciplina_opcoes = ["Artes", "Educação Física", "Inglês", "Espanhol", "Ensino Religioso", "Projeto de Vida", "SOE"]
                else:
                    discs_vinc = str(st.session_state.user_data.get('Disciplinas', "")).split(", ")
                    disciplina_opcoes = sorted([d.strip() for d in discs_vinc if d.strip()])
                    
                disciplina = st.selectbox("Disciplina", disciplina_opcoes, key="disc_oc_soe")
                periodo = st.text_input("Bimestre", value=bimestre_ativo, disabled=True, key="bim_oc_soe")
                
                data_ocorrido = st.date_input("Data do ocorrido", value=datetime.now().date(), format="DD/MM/YYYY", key="data_oc_soe")
                tempo_aula = st.selectbox("Tempo de aula", ["1º tempo", "2º tempo", "3º tempo", "4º tempo"], key="tempo_oc_soe")
                
                opcoes_ocorrencias = [
                    "Agrediu o colega verbalmente", 
                    "Agrediu o colega fisicamente", 
                    "Agrediu o professor verbalmente", 
                    "Agrediu o professor fisicamente", 
                    "Não trouxe o livro",
                    "Dormiu em sala", 
                    "Usou o celular em sala", 
                    "Não fez a tarefa em sala", 
                    "Não fez a tarefa em casa", 
                    "Não trouxe o material", 
                    "Excesso de faltas"
                ]
                
                selecao_oc = st.multiselect("Selecione as ocorrências", options=opcoes_ocorrencias, key="ms_oc_soe")
                obs_oc = st.text_area("Observações detalhadas", key="obs_oc_soe")
                
                btn_salvar_oc = st.form_submit_button("GRAVAR OCORRÊNCIA", disabled=(bimestre_ativo == "Bloqueado" or not permissao_final))

            if btn_salvar_oc:
                if not permissao_final:
                    st.error("Sem permissão para gravar neste módulo.")
                elif not selecao_oc:
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

        with tab_oc2:
            try:
                sh = conectar_google_sheets()
                wks_reg = sh.worksheet("Registros_Ocorrencias")
                dados_brutos = wks_reg.get_all_values()
                
                if len(dados_brutos) > 1:
                    df_full = pd.DataFrame(dados_brutos[1:], columns=dados_brutos[0])
                    df_full['ID_Original'] = range(2, len(df_full) + 2)
                    df_oc = df_full[df_full[df_full.columns[6]].astype(str).str.contains("OCORRÊNCIA:", na=False)]
                    
                    if not df_oc.empty:
                        colunas_df = df_oc.columns.tolist()
                        
                        col_fo1, col_fo2, col_fo3 = st.columns(3)
                        with col_fo1:
                            col_bim_oc = colunas_df[5]
                            lista_bimestres_oc = ["Todos"] + sorted(df_oc[col_bim_oc].unique().astype(str).tolist())
                            bim_filtro_oc = st.selectbox("Filtrar por Bimestre (Ocorrências)", lista_bimestres_oc, key="f_bim_oc_soe")
                        
                        with col_fo2:
                            col_turma_oc = colunas_df[2]
                            if is_master or (is_soe and st.session_state.pagina == "SOE"):
                                opcoes_turmas_oc = sorted(df_oc[col_turma_oc].unique().astype(str).tolist())
                            else:
                                turmas_vinc = str(st.session_state.user_data.get('Turmas', "")).split(", ")
                                opcoes_turmas_oc = sorted([t.strip() for t in turmas_vinc if t.strip()])
                            turma_filtro_oc = st.multiselect("Filtrar por Turma (Ocorrências)", options=opcoes_turmas_oc, key="f_turma_oc_soe")

                        with col_fo3:
                            col_disc_oc = colunas_df[4]
                            opcoes_disciplinas_oc = sorted(df_oc[col_disc_oc].unique().astype(str).tolist())
                            disciplina_filtro_oc = st.multiselect("Filtrar por Disciplina (Ocorrências)", options=opcoes_disciplinas_oc, key="f_disc_oc_soe")

                        df_oc_filtrado = df_oc.copy()
                        if bim_filtro_oc != "Todos":
                            df_oc_filtrado = df_oc_filtrado[df_oc_filtrado[col_bim_oc].astype(str) == bim_filtro_oc]
                        
                        if not is_master and not (is_soe and st.session_state.pagina == "SOE"):
                            turmas_usuario = [t.strip() for t in str(st.session_state.user_data.get('Turmas', "")).split(", ") if t.strip()]
                            df_oc_filtrado = df_oc_filtrado[df_oc_filtrado[col_turma_oc].astype(str).isin(turmas_usuario)]
                            
                        if turma_filtro_oc:
                            df_oc_filtrado = df_oc_filtrado[df_oc_filtrado[col_turma_oc].astype(str).isin(turma_filtro_oc)]
                        
                        if disciplina_filtro_oc:
                            df_oc_filtrado = df_oc_filtrado[df_oc_filtrado[col_disc_oc].astype(str).isin(disciplina_filtro_oc)]

                        def extrair_data_tempo(detalhes):
                            try:
                                data_parte = detalhes.split("DATA: ")[1].split(" | ")[0]
                                tempo_parte = detalhes.split("TEMPO: ")[1].split(" | ")[0]
                                return f"{data_parte} - {tempo_parte}"
                            except:
                                return ""

                        def extrair_obs_limpa(detalhes):
                            try:
                                return detalhes.split(" | ")[2] if len(detalhes.split(" | ")) > 2 else detalhes
                            except:
                                return detalhes

                        df_oc_filtrado['Data/Tempo'] = df_oc_filtrado[colunas_df[7]].apply(extrair_data_tempo)
                        df_oc_filtrado['Detalhes_Limpo'] = df_oc_filtrado[colunas_df[7]].apply(extrair_obs_limpa)
                        df_oc_filtrado[colunas_df[6]] = df_oc_filtrado[colunas_df[6]].astype(str).str.replace("OCORRÊNCIA: ", "", case=False)

                        mapeamento_oc = {
                            'Data/Tempo': 'Data/Tempo',
                            colunas_df[2]: "Turma",
                            colunas_df[3]: "Alunos",
                            colunas_df[5]: "Periodo",
                            colunas_df[4]: "Disciplina",
                            colunas_df[1]: "Professor",
                            colunas_df[6]: "Tipo_Ocorrência",
                            'Detalhes_Limpo': "Observações"
                        }
                        
                        df_ex_oc = df_oc_filtrado.rename(columns=mapeamento_oc)
                        df_ex_oc = df_ex_oc.sort_values(by=["Periodo", "Turma", "Alunos"])
                        
                        ordem_oc = ["Data/Tempo", "Turma", "Alunos", "Periodo", "Disciplina", "Professor", "Tipo_Ocorrência", "Observações"]
                        st.dataframe(df_ex_oc[ordem_oc], use_container_width=True, hide_index=True)

                        output_oc = io.BytesIO()
                        with pd.ExcelWriter(output_oc, engine='xlsxwriter') as writer:
                            df_ex_oc[ordem_oc].to_excel(writer, index=False, sheet_name='Ocorrencias')
                            workbook = writer.book
                            worksheet = writer.sheets['Ocorrencias']
                            worksheet.set_landscape()
                            worksheet.set_paper(9)
                            worksheet.set_margins(0.5, 0.5, 0.5, 0.5)
                            worksheet.fit_to_pages(1, 0)
                            header_format = workbook.add_format({'bold': True, 'bg_color': '#F2DCDB', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
                            wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top', 'border': 1})
                            worksheet.set_column('A:A', 15, wrap_format)
                            worksheet.set_column('B:B', 6, wrap_format)
                            worksheet.set_column('C:C', 25, wrap_format)
                            worksheet.set_column('D:D', 10, wrap_format)
                            worksheet.set_column('E:E', 15, wrap_format)
                            worksheet.set_column('F:F', 15, wrap_format)
                            worksheet.set_column('G:G', 25, wrap_format)
                            worksheet.set_column('H:H', 35, wrap_format)
                            for col_num, value in enumerate(df_ex_oc[ordem_oc].columns.values):
                                worksheet.write(0, col_num, value, header_format)

                        st.download_button(label="📥 Baixar Relatório de Ocorrências (A4 Paisagem)", data=output_oc.getvalue(), file_name=f'Ocorrencias_{datetime.now().strftime("%Y%m%d")}.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', use_container_width=True)

                        st.divider()
                        st.subheader("📝 Editar ou 🗑️ Excluir Ocorrências")
                        
                        if is_soe and st.session_state.pagina == "Ocorrencias" and not is_master:
                            st.info("Usuários SOE não possuem permissão para editar ou excluir registros neste módulo. Use o botão SOE na lateral.")
                        else:
                            if is_master or (is_soe and st.session_state.pagina == "SOE"):
                                df_edit_oc_propria = df_oc_filtrado
                            else:
                                discs_usuario = [d.strip().lower() for d in str(st.session_state.user_data.get('Disciplinas', "")).split(", ") if d.strip()]
                                df_edit_oc_propria = df_oc_filtrado[df_oc_filtrado[colunas_df[4]].astype(str).str.lower().isin(discs_usuario)]
                            
                            if not df_edit_oc_propria.empty:
                                col_data_oc = colunas_df[0]
                                opcoes_edit_oc = {f"{row[col_data_oc]} - {row[colunas_df[3]]} ({row[colunas_df[4]]})": row['ID_Original'] for _, row in df_edit_oc_propria.iterrows()}
                                selecionado_oc_edit = st.selectbox("Selecione a ocorrência para gerenciar", [""] + list(opcoes_edit_oc.keys()), key="sel_edit_oc_soe")
                                
                                if selecionado_oc_edit != "":
                                    linha_idx_oc = opcoes_edit_oc[selecionado_oc_edit]
                                    dados_oc_edit = df_edit_oc_propria[df_edit_oc_propria['ID_Original'] == linha_idx_oc].iloc[0]
                                    
                                    with st.form("form_editar_ocorrencia_soe"):
                                        st.markdown(f"Gerenciando ocorrência de: **{dados_oc_edit[colunas_df[3]]}**")
                                        texto_oc_atual = str(dados_oc_edit[colunas_df[6]]).replace("OCORRÊNCIA: ", "")
                                        lista_oc_atual = [i.strip() for i in texto_oc_atual.split(",")]
                                        opcoes_oc_edit = ["Agrediu o colega verbalmente", "Agrediu o colega fisicamente", "Agrediu o professor verbalmente", "Agrediu o professor fisicamente", "Não trouxe o livro", "Dormiu em sala", "Usou o celular em sala", "Não fez a tarefa em sala", "Não fez a tarefa em casa", "Não trouxe o material", "Excesso de faltas"]
                                        edit_selecao_oc = st.multiselect("Selecione as ocorrências", options=opcoes_oc_edit, default=[i for i in lista_oc_atual if i in opcoes_oc_edit])
                                        edit_detalhes_oc = st.text_area("Detalhes (Data/Tempo/Obs)", value=dados_oc_edit[colunas_df[7]])
                                        col_at_oc1, col_at_oc2 = st.columns(2)
                                        with col_at_oc1:
                                            btn_confirmar_edit_oc = st.form_submit_button("SALVAR ALTERAÇÕES")
                                        with col_at_oc2:
                                            btn_confirmar_exc_oc = st.form_submit_button("❌ EXCLUIR OCORRÊNCIA")
                                            
                                        if btn_confirmar_edit_oc:
                                            try:
                                                tipo_formatado_edit_oc = "OCORRÊNCIA: " + ", ".join(edit_selecao_oc)
                                                wks_reg.update_cell(linha_idx_oc, 7, tipo_formatado_edit_oc)
                                                wks_reg.update_cell(linha_idx_oc, 8, edit_detalhes_oc)
                                                st.success("Ocorrência atualizada!")
                                                time.sleep(2)
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"Erro ao editar: {e}")
                                                
                                        if btn_confirmar_exc_oc:
                                            try:
                                                wks_reg.delete_rows(linha_idx_oc)
                                                st.success("Ocorrência excluída!")
                                                time.sleep(2)
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"Erro ao excluir: {e}")
                            else:
                                st.info("Nenhuma ocorrência disponível para gerenciar.")
                else:
                    st.info("Nenhuma ocorrência encontrada.")
            except Exception as e:
                st.error(f"Erro ao carregar ocorrências: {e}")

    elif st.session_state.pagina == "VisualizarRegistros":
        st.title("📋 Registros de Desempenho Realizados")
        try:
            sh = conectar_google_sheets()
            wks_reg = sh.worksheet("Registros_Ocorrencias")
            dados_brutos = wks_reg.get_all_values()
            
            if len(dados_brutos) > 1:
                df_reg = pd.DataFrame(dados_brutos[1:], columns=dados_brutos[0])
                df_reg = df_reg[~df_reg[df_reg.columns[6]].astype(str).str.contains("OCORRÊNCIA:", na=False)]
                
                colunas_df = df_reg.columns.tolist()
                
                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1:
                    col_bim = 'Bimestre' if 'Bimestre' in colunas_df else colunas_df[5]
                    lista_bimestres = ["Todos"] + sorted(df_reg[col_bim].unique().astype(str).tolist())
                    bim_filtro = st.selectbox("Filtrar por Bimestre", lista_bimestres)
                
                with col_f2:
                    col_turma = 'Turma' if 'Turma' in colunas_df else colunas_df[2]
                    if is_master or is_soe:
                        opcoes_turmas_reg = sorted(df_reg[col_turma].unique().astype(str).tolist())
                    else:
                        turmas_vinc = str(st.session_state.user_data.get('Turmas', "")).split(", ")
                        opcoes_turmas_reg = sorted([t.strip() for t in turmas_vinc if t.strip()])
                    turma_filtro = st.multiselect("Filtrar por Turma", options=opcoes_turmas_reg, default=[])

                with col_f3:
                    col_disc_data = colunas_df[4]
                    opcoes_disciplinas_reg = sorted(df_reg[col_disc_data].unique().astype(str).tolist())
                    disciplina_filtro = st.multiselect("Filtrar por Disciplina", options=opcoes_disciplinas_reg, default=[])
                
                df_reg['ID_Original'] = range(2, len(df_reg) + 2)
                df_filtrado = df_reg.copy()
                
                if bim_filtro != "Todos":
                    df_filtrado = df_filtrado[df_filtrado[col_bim].astype(str) == bim_filtro]
                
                if turma_filtro:
                    df_filtrado = df_filtrado[df_filtrado[col_turma].astype(str).isin(turma_filtro)]
                else:
                    if not is_master and not is_soe:
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
                st.dataframe(df_exibicao[ordem_colunas], use_container_width=True, hide_index=True)

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_exibicao[ordem_colunas].to_excel(writer, index=False, sheet_name='Relatorio')
                    workbook = writer.book
                    worksheet = writer.sheets['Relatorio']
                    worksheet.set_landscape() 
                    worksheet.set_paper(9)
                    worksheet.set_margins(0.5, 0.5, 0.5, 0.5)
                    worksheet.fit_to_pages(1, 0)
                    header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
                    wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top', 'border': 1})
                    worksheet.set_column('A:A', 6, wrap_format)
                    worksheet.set_column('B:B', 25, wrap_format)
                    worksheet.set_column('C:C', 10, wrap_format)
                    worksheet.set_column('D:D', 28, wrap_format)
                    worksheet.set_column('E:E', 25, wrap_format)
                    worksheet.set_column('F:F', 40, wrap_format)
                    for col_num, value in enumerate(df_exibicao[ordem_colunas].columns.values):
                        worksheet.write(0, col_num, value, header_format)

                st.download_button(label="📥 Baixar Relatório de Desempenho (A4 Paisagem)", data=output.getvalue(), file_name=f'Relatorio_Desempenho_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', use_container_width=True)

                st.divider()
                st.subheader("📝 Editar ou 🗑️ Excluir Registros de Desempenho")
                
                if is_soe and not is_master:
                    st.info("Usuários SOE não possuem permissão para editar ou excluir registros.")
                else:
                    col_exc1, col_exc2 = st.columns(2)
                    with col_exc1:
                        st.markdown("**Gerenciar registro individual**")
                        if is_master:
                            df_edit_proprio = df_filtrado
                        else:
                            discs_usuario_reg = [d.strip().lower() for d in str(st.session_state.user_data.get('Disciplinas', "")).split(", ") if d.strip()]
                            df_edit_proprio = df_filtrado[df_filtrado[colunas_df[4]].astype(str).str.lower().isin(discs_usuario_reg)]
                        
                        if not df_edit_proprio.empty:
                            opcoes_edit = {f"{row[col_data]} - {row[colunas_df[3]]} ({row[colunas_df[4]]})": row['ID_Original'] for _, row in df_edit_proprio.iterrows()}
                            selecionado_para_edit = st.selectbox("Selecione o registro para modificar", [""] + list(opcoes_edit.keys()))
                            if selecionado_para_edit != "":
                                linha_idx = opcoes_edit[selecionado_para_edit]
                                dados_reg_edit = df_edit_proprio[df_edit_proprio['ID_Original'] == linha_idx].iloc[0]
                                with st.form("form_editar_registro_desempenho"):
                                    st.markdown(f"Editando registro de: **{dados_reg_edit[colunas_df[3]]}**")
                                    itens_atuais = str(dados_reg_edit[colunas_df[6]]).split(", ")
                                    usuario_disciplinas = str(st.session_state.user_data.get('Disciplinas', "")).lower()
                                    if any(d in usuario_disciplinas for d in ["educação física", "religião", "artes"]):
                                        opcoes_radio = ["Ponto de atenção"]
                                    else:
                                        opcoes_radio = ["Reprovado", "Aprovado após recuperação", "Ponto de atenção"]
                                    desemp_atual = next((i for i in itens_atuais if i in opcoes_radio), None)
                                    edit_desempenho = st.radio("Desempenho", options=opcoes_radio, index=opcoes_radio.index(desemp_atual) if desemp_atual else 0, horizontal=True)
                                    opcoes_multi = ["Indisciplinado (a)", "Não traz material", "Não realiza tarefa em sala", "Não realiza tarefa em casa", "Muitas faltas", "Baixo rendimento", "Não fez o simulado", "Não apresentou trabalho"]
                                    if any(d in usuario_disciplinas for d in ["educação física", "religião", "artes"]):
                                        opcoes_multi.append("Não fez o questionário participativo")
                                    itens_multi_atuais = [i for i in itens_atuais if i in opcoes_multi]
                                    edit_tipo_selecao = st.multiselect("Valores e atitudes", options=opcoes_multi, default=itens_multi_atuais)
                                    edit_obs = st.text_area("Observações", value=dados_reg_edit[colunas_df[7]])
                                    col_at1, col_at2 = st.columns(2)
                                    with col_at1:
                                        btn_confirmar_edit = st.form_submit_button("SALVAR ALTERAÇÕES")
                                    with col_at2:
                                        btn_confirmar_exc = st.form_submit_button("❌ EXCLUIR REGISTRO")
                                    if btn_confirmar_edit:
                                        try:
                                            itens_finais_edit = []
                                            if edit_desempenho: itens_finais_edit.append(edit_desempenho)
                                            itens_finais_edit.extend(edit_tipo_selecao)
                                            tipo_formatado_edit = ", ".join(itens_finais_edit)
                                            wks_reg.update_cell(linha_idx, 7, tipo_formatado_edit)
                                            wks_reg.update_cell(linha_idx, 8, edit_obs)
                                            st.success("Registro atualizado!")
                                            time.sleep(2)
                                            st.rerun()
                                        except Exception as e: st.error(f"Erro ao editar: {e}")
                                    if btn_confirmar_exc:
                                        try:
                                            wks_reg.delete_rows(linha_idx)
                                            st.success("Registro excluído!")
                                            time.sleep(2)
                                            st.rerun()
                                        except Exception as e: st.error(f"Erro ao excluir: {e}")
                        else: st.info("Nenhum registro disponível para gerenciar.")
                    with col_exc2:
                        if is_master:
                            st.markdown("**Exclusão em massa**")
                            if bim_filtro != "Todos":
                                if turma_filtro and len(turma_filtro) == 1:
                                    t_unica = turma_filtro[0]
                                    st.warning(f"Apagar registros de {t_unica} no {bim_filtro}?")
                                    if st.button(f"🚨 EXCLUIR TURMA: {t_unica}"):
                                        indices_massa = sorted(df_filtrado['ID_Original'].tolist(), reverse=True)
                                        for idx in indices_massa: wks_reg.delete_rows(idx)
                                        st.success("Excluído!"); st.rerun()
                                if st.button(f"💥 EXCLUIR TUDO DO {bim_filtro}"):
                                    df_m = df_reg[df_reg[col_bim].astype(str) == bim_filtro]
                                    if not df_m.empty:
                                        indices_bim = sorted(df_m['ID_Original'].tolist(), reverse=True)
                                        for idx in indices_bim: wks_reg.delete_rows(idx)
                                        st.success("Bimestre zerado!"); st.rerun()
                            else: st.info("Selecione um Bimestre para exclusão em massa.")
        except Exception as e: st.error(f"Erro: {e}")

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
                        st.success("✅ Senha atualizada!")
                        st.cache_data.clear()
                    except Exception as e: st.error(f"Erro: {e}")

    elif st.session_state.pagina == "Cadastro" and is_master:
        st.title("⚙️ Painel de Cadastro")
        abas = ["Turmas/Alunos", "Disciplinas", "Gerenciar Usuários", "Alterar Senha", "Período de Lançamento"]
        if st.session_state.user_data['Usuario'] == "rodrigo": abas.append("Bloqueio Master")
        tabs = st.tabs(abas)
        with tabs[0]:
            st.subheader("Gerenciar Alunos e Turmas")
            opcao_cadastro = st.radio("Selecione uma Ação", ["Individual", "Em Massa (Excel/Word)", "Transferir Aluno", "Excluir Aluno", "Limpar turma"])
            if opcao_cadastro == "Individual":
                with st.form("form_aluno", clear_on_submit=True):
                    nova_turma = st.text_input("Turma (Ex: 101, 201...)")
                    novo_aluno = st.text_input("Nome Completo do Aluno")
                    if st.form_submit_button("CADASTRAR ALUNO"):
                        if nova_turma and novo_aluno:
                            try:
                                sh = conectar_google_sheets()
                                wks_a = sh.worksheet("Config_Alunos")
                                wks_a.append_row([nova_turma, novo_aluno])
                                st.success("Aluno cadastrado!")
                                st.cache_data.clear()
                            except Exception as e: st.error(f"Erro: {e}")
                        else: st.warning("Preencha todos os campos.")
            elif opcao_cadastro == "Em Massa (Excel/Word)":
                st.info("Cole os dados: Coluna 1 = Turma, Coluna 2 = Nome do Aluno.")
                texto_massa = st.text_area("Dados (Copie e cole aqui)", height=200)
                if st.button("PROCESSAR E SALVAR ALUNOS"):
                    if texto_massa:
                        linhas = [l.split('\t') for l in texto_massa.strip().split('\n')]
                        dados_finais = []
                        for l in linhas:
                            if len(l) >= 2: dados_finais.append([l[0].strip(), l[1].strip()])
                        if dados_finais:
                            try:
                                sh = conectar_google_sheets()
                                wks_a = sh.worksheet("Config_Alunos")
                                wks_a.append_rows(dados_finais)
                                st.success(f"{len(dados_finais)} alunos cadastrados!")
                                st.cache_data.clear()
                            except Exception as e: st.error(f"Erro: {e}")
                    else: st.warning("Cole os dados primeiro.")
            elif opcao_cadastro == "Excluir Aluno":
                t_exc = st.selectbox("Selecione a Turma", sorted(df_alunos['Turma'].unique().astype(str)))
                a_exc = st.selectbox("Selecione o Aluno", sorted(df_alunos[df_alunos['Turma'].astype(str) == t_exc]['Nome_Aluno'].tolist()))
                if st.button("❌ EXCLUIR DEFINITIVAMENTE"):
                    try:
                        sh = conectar_google_sheets()
                        wks_a = sh.worksheet("Config_Alunos")
                        celula = wks_a.find(str(a_exc))
                        if celula:
                            wks_a.delete_rows(celula.row)
                            st.success("Aluno removido!")
                            st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")
        with tabs[1]:
            st.subheader("Gerenciar Disciplinas")
            with st.form("form_disc", clear_on_submit=True):
                nova_d = st.text_input("Nome da Disciplina")
                if st.form_submit_button("ADICIONAR DISCIPLINA"):
                    if nova_d:
                        try:
                            sh = conectar_google_sheets()
                            wks_d = sh.worksheet("Config_Disciplinas")
                            wks_d.append_row([nova_d])
                            st.success("Disciplina adicionada!"); st.cache_data.clear()
                        except Exception as e: st.error(f"Erro: {e}")
        with tabs[2]:
            st.subheader("Gerenciar Professores/Usuários")
            with st.form("form_prof", clear_on_submit=True):
                c1, c2 = st.columns(2)
                p_nome = c1.text_input("Nome do Professor")
                p_user = c2.text_input("Usuário (Login)")
                p_pass = c1.text_input("Senha Inicial")
                p_turmas = c2.text_input("Turmas (Separadas por vírgula e espaço: 101, 201)")
                p_discs = st.text_input("Disciplinas (Separadas por vírgula e espaço: Artes, Inglês)")
                if st.form_submit_button("CADASTRAR PROFESSOR"):
                    if p_nome and p_user and p_pass:
                        try:
                            sh = conectar_google_sheets()
                            wks_p = sh.worksheet("Config_Professores")
                            wks_p.append_row([p_nome, p_user, p_pass, p_turmas, p_discs, "Ativo"])
                            st.success("Professor cadastrado!"); st.cache_data.clear()
                        except Exception as e: st.error(f"Erro: {e}")
            st.divider()
            st.write("**Lista de Professores**")
            st.dataframe(df_profs, use_container_width=True)
            user_del = st.selectbox("Selecione um usuário para remover", [""] + df_profs['Usuario'].tolist())
            if st.button("🗑️ EXCLUIR USUÁRIO"):
                if user_del:
                    try:
                        sh = conectar_google_sheets()
                        wks_p = sh.worksheet("Config_Professores")
                        celula = wks_p.find(str(user_del))
                        wks_p.delete_rows(celula.row)
                        st.success("Removido!"); st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")
        with tabs[3]:
            st.subheader("Alterar Senha de Outro Usuário")
            user_m = st.selectbox("Selecione o Usuário", df_profs['Usuario'].tolist(), key="sel_m")
            nova_s_m = st.text_input("Nova Senha", type="password", key="pass_m")
            if st.button("ATUALIZAR SENHA"):
                try:
                    sh = conectar_google_sheets()
                    wks_p = sh.worksheet("Config_Professores")
                    celula = wks_p.find(str(user_m))
                    wks_p.update_cell(celula.row, 3, str(nova_s_m))
                    st.success("Senha alterada!"); st.cache_data.clear()
                except Exception as e: st.error(f"Erro: {e}")
        with tabs[4]:
            st.subheader("Configurar Período de Lançamento")
            with st.form("form_per"):
                bim = st.selectbox("Bimestre", ["1º Bimestre", "2º Bimestre", "3º Bimestre", "4º Bimestre", "Recuperação Final"])
                dat_ini = st.date_input("Data Início")
                dat_fim = st.date_input("Data Fim")
                if st.form_submit_button("SALVAR PERÍODO"):
                    try:
                        sh = conectar_google_sheets()
                        wks_per = sh.worksheet("Config_Periodos")
                        dados_at = wks_per.get_all_records()
                        wks_per.clear()
                        wks_per.append_row(["Bimestre", "Inicio", "Fim"])
                        wks_per.append_row([bim, dat_ini.strftime("%d/%m/%Y"), dat_fim.strftime("%d/%m/%Y")])
                        st.success("Período atualizado!"); st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")
        if st.session_state.user_data['Usuario'] == "rodrigo":
            with tabs[5]:
                st.subheader("Bloqueio de Acesso Master")
                user_b = st.selectbox("Usuário", df_profs['Usuario'].tolist())
                c_b1, c_b2 = st.columns(2)
                if c_b1.button("🔴 BLOQUEAR"):
                    try:
                        sh = conectar_google_sheets(); wks_p = sh.worksheet("Config_Professores")
                        celula = wks_p.find(str(user_b))
                        wks_p.update_cell(celula.row, 6, "Bloqueado")
                        st.success("Bloqueado!"); st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")
                if c_b2.button("🟢 DESBLOQUEAR"):
                    try:
                        sh = conectar_google_sheets(); wks_p = sh.worksheet("Config_Professores")
                        celula = wks_p.find(str(user_b))
                        wks_p.update_cell(celula.row, 6, "Ativo")
                        st.success("Desbloqueado!"); st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")
