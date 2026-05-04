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

def atualizar_presenca(usuario, sair=False):
    try:
        sh = conectar_google_sheets()
        try:
            wks_online = sh.worksheet("Usuarios_Online")
        except:
            wks_online = sh.add_worksheet(title="Usuarios_Online", rows="100", cols="2")
            wks_online.append_row(["Usuario", "Ultimo_Acesso"])
        
        celula = None
        try:
            celula = wks_online.find(usuario)
        except:
            pass

        if sair:
            if celula:
                wks_online.delete_rows(celula.row)
        else:
            agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            if celula:
                wks_online.update_cell(celula.row, 2, agora)
            else:
                wks_online.append_row([usuario, agora])
    except:
        pass

def obter_usuarios_online():
    try:
        sh = conectar_google_sheets()
        wks_online = sh.worksheet("Usuarios_Online")
        dados = wks_online.get_all_records()
        return pd.DataFrame(dados)
    except:
        return pd.DataFrame(columns=["Usuario", "Ultimo_Acesso"])

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
                atualizar_presenca("rodrigo")
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
                        atualizar_presenca(user_input)
                        st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

else:
    atualizar_presenca(st.session_state.user_data['Usuario'])
    
    col_side1, col_side2, col_side3 = st.sidebar.columns([1, 2, 1])
    with col_side2:
        st.image("logo.png", width=80)
        
    prof_nome = st.session_state.user_data['Professor']
    st.sidebar.markdown(f"<div style='text-align: center'>Professor: <b>{prof_nome}</b></div>", unsafe_allow_html=True)
    st.sidebar.divider()
    
    st.sidebar.subheader("👥 Usuários Online")
    df_online = obter_usuarios_online()
    if not df_online.empty:
        for u in df_online['Usuario'].tolist():
            st.sidebar.markdown(f"🟢 {u}")
    else:
        st.sidebar.write("Nenhum outro usuário")
    st.sidebar.divider()

    if st.sidebar.button("Desempenho do aluno", key="btn_desempenho", use_container_width=True):
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
        atualizar_presenca(st.session_state.user_data['Usuario'], sair=True)
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

    elif st.session_state.pagina == "VisualizarRegistros":
        st.title("📋 Registros Realizados")
        try:
            sh = conectar_google_sheets()
            wks_reg = sh.worksheet("Registros_Ocorrencias")
            dados_brutos = wks_reg.get_all_values()
            
            if len(dados_brutos) > 1:
                df_reg = pd.DataFrame(dados_brutos[1:], columns=dados_brutos[0])
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
                
                df_reg['ID_Original'] = range(2, len(df_reg) + 2)
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
                                    except Exception as e:
                                        st.error(f"Erro ao editar: {e}")
                                if btn_confirmar_exc:
                                    try:
                                        wks_reg.delete_rows(linha_idx)
                                        st.success("Registro excluído!")
                                        time.sleep(2)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro ao excluir: {e}")
                    else:
                        st.info("Nenhum registro disponível para gerenciar no filtro atual.")
                with col_exc2:
                    if st.session_state.user_data['Usuario'] in ["admin", "rodrigo"]:
                        st.markdown("**Exclusão em massa**")
                        if bim_filtro != "Todos":
                            if turma_filtro and len(turma_filtro) == 1:
                                t_unica = turma_filtro[0]
                                st.warning(f"Apagar TODOS os registros de {t_unica} no {bim_filtro}?")
                                if st.button(f"🚨 EXCLUIR TURMA: {t_unica} - {bim_filtro}"):
                                    indices_massa = sorted(df_filtrado['ID_Original'].tolist(), reverse=True)
                                    for idx in indices_massa: wks_reg.delete_rows(idx)
                                    st.success(f"Foram excluídos {len(indices_massa)} registros.")
                                    st.rerun()
                            st.divider()
                            st.error(f"Zerar BIMESTRE: Apagar TODOS os registros do {bim_filtro}?")
                            if st.button(f"💥 EXCLUIR TUDO DO {bim_filtro}"):
                                df_massa_bim = df_reg[df_reg[col_bim].astype(str) == bim_filtro]
                                if not df_massa_bim.empty:
                                    indices_bim = sorted(df_massa_bim['ID_Original'].tolist(), reverse=True)
                                    for idx in indices_bim: wks_reg.delete_rows(idx)
                                    st.success(f"Foram excluídos {len(indices_bim)} registros do {bim_filtro}.")
                                    st.rerun()
                                else:
                                    st.info("Não há registros para este bimestre.")
                        else:
                            st.info("Selecione um Bimestre específico para habilitar a exclusão em massa.")
                    else:
                        st.empty()
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
                    with col_senha_p2:
                        msg_placeholder_err_p = st.empty()
                        msg_placeholder_err_p.error("As senhas não coincidem.")
                        time.sleep(3)
                        msg_placeholder_err_p.empty()
                else:
                    try:
                        sh = conectar_google_sheets()
                        wks_p = sh.worksheet("Config_Professores")
                        celula = wks_p.find(str(user_atual))
                        wks_p.update_cell(celula.row, 3, str(nova_senha_prof))
                        with col_senha_p2:
                            msg_placeholder_ok_p = st.empty()
                            msg_placeholder_ok_p.success("✅ Senha atualizada!")
                            time.sleep(3)
                            msg_placeholder_ok_p.empty()
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Erro ao atualizar: {e}")

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
                    nova_turma = st.text_input("Turma (Ex: 101, 202)")
                    novo_aluno = st.text_input("Nome Completo do Aluno")
                    col_btn_ind, col_msg_ind = st.columns([1, 2])
                    with col_btn_ind: btn_salvar_ind = st.form_submit_button("Salvar Aluno")
                    if btn_salvar_ind:
                        duplicado = df_alunos[(df_alunos['Turma'].astype(str) == nova_turma) & (df_alunos['Nome_Aluno'].astype(str).str.upper() == novo_aluno.strip().upper())]
                        if not duplicado.empty:
                            with col_msg_ind:
                                msg_placeholder_err = st.empty()
                                msg_placeholder_err.error(f"Erro: O aluno '{novo_aluno}' já está cadastrado na turma '{nova_turma}'.")
                                time.sleep(3)
                                msg_placeholder_err.empty()
                        else:
                            try:
                                sh = conectar_google_sheets()
                                wks_a = sh.worksheet("Config_Alunos")
                                wks_a.append_row([nova_turma, novo_aluno])
                                with col_msg_ind:
                                    st.success("Aluno cadastrado com sucesso")
                                    st.cache_data.clear()
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")
            elif opcao_cadastro == "Em Massa (Excel/Word)":
                with st.form("form_aluno_massa", clear_on_submit=True):
                    turma_massa = st.text_input("Turma para todos os alunos (Ex: 101)")
                    lista_nomes = st.text_area("Cole aqui a lista de nomes (um por linha)")
                    col_btn_massa, col_msg_massa = st.columns([1, 2])
                    with col_btn_massa: btn_salvar_massa = st.form_submit_button("Salvar Todos os Alunos")
                    if btn_salvar_massa:
                        if not turma_massa or not lista_nomes: st.error("Preencha a turma e a lista de nomes.")
                        else:
                            try:
                                nomes = [n.strip() for n in lista_nomes.split('\n') if n.strip()]
                                novas_linhas = [[turma_massa, nome] for nome in nomes]
                                sh = conectar_google_sheets()
                                wks_a = sh.worksheet("Config_Alunos")
                                wks_a.append_rows(novas_linhas)
                                st.success(f"{len(nomes)} alunos cadastrados.")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")
            elif opcao_cadastro == "Transferir Aluno":
                todas_turmas_cadastradas = sorted(df_alunos['Turma'].unique().astype(str))
                turma_orig = st.selectbox("Turma de Origem", [""] + todas_turmas_cadastradas)
                if turma_orig != "":
                    alunos_orig = df_alunos[df_alunos['Turma'].astype(str) == turma_orig]['Nome_Aluno'].tolist()
                    aluno_a_transf = st.selectbox("Selecione o Aluno", [""] + sorted(alunos_orig))
                    turma_dest = st.selectbox("Turma de Destino", [""] + todas_turmas_cadastradas)
                    if aluno_a_transf != "" and turma_dest != "" and st.button("Executar Transferência"):
                        try:
                            sh = conectar_google_sheets()
                            wks_a = sh.worksheet("Config_Alunos")
                            data = wks_a.get_all_values()
                            row_index = -1
                            for i, row in enumerate(data):
                                if row[0] == turma_orig and row[1] == aluno_a_transf:
                                    row_index = i + 1; break
                            if row_index != -1:
                                wks_a.update_cell(row_index, 1, str(turma_dest))
                                st.success("Transferido!")
                                st.cache_data.clear(); st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")
            elif opcao_cadastro == "Excluir Aluno":
                todas_turmas_exc = sorted(df_alunos['Turma'].unique().astype(str))
                turma_exc = st.selectbox("Selecione a Turma", [""] + todas_turmas_exc)
                if turma_exc != "":
                    alunos_exc = df_alunos[df_alunos['Turma'].astype(str) == turma_exc]['Nome_Aluno'].tolist()
                    aluno_a_excluir = st.selectbox("Selecione o Aluno", [""] + sorted(alunos_exc))
                    if aluno_a_excluir != "" and st.button("❌ EXCLUIR ALUNO"):
                        try:
                            sh = conectar_google_sheets()
                            wks_a = sh.worksheet("Config_Alunos")
                            data = wks_a.get_all_values()
                            row_index = -1
                            for i, row in enumerate(data):
                                if row[0] == turma_exc and row[1] == aluno_a_excluir:
                                    row_index = i + 1; break
                            if row_index != -1:
                                wks_a.delete_rows(row_index)
                                st.success("Removido!")
                                st.cache_data.clear(); st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")
            elif opcao_cadastro == "Limpar turma":
                todas_turmas_limpar = sorted(df_alunos['Turma'].unique().astype(str))
                turma_alvo_limpar = st.selectbox("Turma para APAGAR TODOS", [""] + todas_turmas_limpar)
                if turma_alvo_limpar != "":
                    if st.checkbox("Confirmo apagar tudo") and st.button(f"🚨 LIMPAR {turma_alvo_limpar}"):
                        try:
                            sh = conectar_google_sheets()
                            wks_a = sh.worksheet("Config_Alunos")
                            data = wks_a.get_all_values()
                            indices = [i + 1 for i, row in enumerate(data) if row[0] == turma_alvo_limpar]
                            for idx in reversed(indices): wks_a.delete_rows(idx)
                            st.success("Turma limpa!")
                            st.cache_data.clear(); st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")

        with tabs[1]:
            st.subheader("Gerenciar Disciplinas")
            with st.form("form_disciplina", clear_on_submit=True):
                nova_disc = st.text_input("Nome da Disciplina")
                if st.form_submit_button("Cadastrar"):
                    if nova_disc:
                        try:
                            sh = conectar_google_sheets()
                            try: wks_d = sh.worksheet("Config_Disciplinas")
                            except: wks_d = sh.add_worksheet(title="Config_Disciplinas", rows="100", cols="2"); wks_d.append_row(["Disciplina"])
                            wks_d.append_row([nova_disc])
                            st.success("Cadastrada!"); st.cache_data.clear(); st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")
            st.divider()
            if not df_discs.empty:
                disc_lista = sorted(df_discs['Disciplina'].unique().astype(str))
                disc_excluir = st.selectbox("Remover disciplina", [""] + disc_lista)
                if st.button("❌ REMOVER"):
                    try:
                        sh = conectar_google_sheets(); wks_d = sh.worksheet("Config_Disciplinas")
                        celula = wks_d.find(str(disc_excluir))
                        wks_d.delete_rows(celula.row)
                        st.success("Removida!"); st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")

        with tabs[2]:
            st.subheader("Cadastrar Novo Professor")
            with st.form("form_prof", clear_on_submit=True):
                novo_prof = st.text_input("Nome")
                novo_usuario = st.text_input("Usuário")
                nova_senha = st.text_input("Senha", type="password")
                turmas_vinculo = st.multiselect("Vincular Turmas", sorted(df_alunos['Turma'].unique().astype(str)))
                disciplinas_vinculo = st.multiselect("Vincular Disciplinas", sorted(df_discs['Disciplina'].unique().astype(str)) if not df_discs.empty else [])
                if st.form_submit_button("Salvar Professor"):
                    try:
                        sh = conectar_google_sheets(); wks_p = sh.worksheet("Config_Professores")
                        wks_p.append_row([novo_prof, novo_usuario, nova_senha, ", ".join(turmas_vinculo), ", ".join(disciplinas_vinculo), "Ativo"])
                        st.success("Sucesso!"); st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")
            st.divider()
            lista_usuarios_edit = df_profs['Usuario'].tolist()
            user_selecionado = st.selectbox("Modificar Usuário", [""] + lista_usuarios_edit)
            if user_selecionado != "":
                dados_atuais = df_profs[df_profs['Usuario'] == user_selecionado].iloc[0]
                with st.form("form_editar_usuario"):
                    edit_nome = st.text_input("Nome", value=dados_atuais['Professor'])
                    edit_login = st.text_input("Login", value=dados_atuais['Usuario'])
                    edit_turmas = st.multiselect("Turmas", sorted(df_alunos['Turma'].unique().astype(str)), default=str(dados_atuais.get('Turmas', "")).split(", "))
                    edit_disciplinas = st.multiselect("Disciplinas", sorted(df_discs['Disciplina'].unique().astype(str)) if not df_discs.empty else [], default=str(dados_atuais.get('Disciplinas', "")).split(", "))
                    c1, c2, c3 = st.columns([1,2,1])
                    if c1.form_submit_button("SALVAR"):
                        try:
                            sh = conectar_google_sheets(); wks_p = sh.worksheet("Config_Professores")
                            celula = wks_p.find(user_selecionado)
                            wks_p.update_cell(celula.row, 1, edit_nome); wks_p.update_cell(celula.row, 2, edit_login)
                            wks_p.update_cell(celula.row, 4, ", ".join(edit_turmas)); wks_p.update_cell(celula.row, 5, ", ".join(edit_disciplinas))
                            st.success("Atualizado!"); st.cache_data.clear(); st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")
                    if c3.form_submit_button("❌ EXCLUIR"):
                        try:
                            sh = conectar_google_sheets(); wks_p = sh.worksheet("Config_Professores")
                            celula = wks_p.find(user_selecionado); wks_p.delete_rows(celula.row)
                            st.success("Excluído!"); st.cache_data.clear(); st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")

        with tabs[3]:
            st.subheader("Alterar Senha")
            user_alvo = st.selectbox("Selecione o Usuário", [""] + df_profs['Usuario'].tolist(), key="senha_alvo")
            nova_senha_input = st.text_input("Nova Senha", type="password")
            confirmar_senha = st.text_input("Confirmar", type="password")
            if st.button("Atualizar Senha"):
                if nova_senha_input == confirmar_senha:
                    try:
                        sh = conectar_google_sheets(); wks_p = sh.worksheet("Config_Professores")
                        celula = wks_p.find(user_alvo); wks_p.update_cell(celula.row, 3, nova_senha_input)
                        st.success("Senha alterada!"); st.cache_data.clear()
                    except Exception as e: st.error(f"Erro: {e}")

        with tabs[4]:
            st.subheader("Períodos de Lançamento")
            with st.form("form_periodo"):
                bim_sel = st.selectbox("Bimestre", ["1º Bimestre", "2º Bimestre", "3º Bimestre", "4º Bimestre"])
                data_inicio = st.date_input("Início")
                data_fim = st.date_input("Fim")
                if st.form_submit_button("Salvar Período"):
                    try:
                        sh = conectar_google_sheets()
                        try: wks_per = sh.worksheet("Config_Periodos")
                        except: wks_per = sh.add_worksheet(title="Config_Periodos", rows="10", cols="3"); wks_per.append_row(["Bimestre", "Inicio", "Fim"])
                        data_per = wks_per.get_all_values(); found = False
                        for i, row in enumerate(data_per):
                            if row[0] == bim_sel:
                                wks_per.update_cell(i+1, 2, data_inicio.strftime("%d/%m/%Y"))
                                wks_per.update_cell(i+1, 3, data_fim.strftime("%d/%m/%Y"))
                                found = True; break
                        if not found: wks_per.append_row([bim_sel, data_inicio.strftime("%d/%m/%Y"), data_fim.strftime("%d/%m/%Y")])
                        st.success("Configurado!"); st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")
            if not df_periodos.empty:
                st.dataframe(df_periodos, use_container_width=True)
                if st.button("Limpar Todos os Períodos"):
                    try:
                        sh = conectar_google_sheets(); wks_per = sh.worksheet("Config_Periodos")
                        rows = len(wks_per.get_all_values())
                        if rows > 1: wks_per.delete_rows(2, rows)
                        st.success("Limpo!"); st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")

        if st.session_state.user_data['Usuario'] == "rodrigo":
            with tabs[5]:
                st.subheader("🛡️ Controle Master")
                df_status = df_profs[['Professor', 'Usuario', 'Status']].copy()
                df_status['Status'] = df_status['Status'].apply(lambda x: "🔴 BLOQUEADO" if str(x).upper() == "BLOQUEADO" else "🟢 ATIVO")
                st.table(df_status)
                user_bloqueio = st.selectbox("Ação para", [""] + ["Todos"] + df_profs['Usuario'].tolist())
                c1, c2 = st.columns(2)
                if user_bloqueio:
                    if c1.button("🔴 BLOQUEAR"):
                        sh = conectar_google_sheets(); wks_p = sh.worksheet("Config_Professores")
                        if user_bloqueio == "Todos":
                            for i in range(2, len(wks_p.get_all_values())+1): wks_p.update_cell(i, 6, "Bloqueado")
                        else: celula = wks_p.find(user_bloqueio); wks_p.update_cell(celula.row, 6, "Bloqueado")
                        st.cache_data.clear(); st.rerun()
                    if c2.button("🟢 DESBLOQUEAR"):
                        sh = conectar_google_sheets(); wks_p = sh.worksheet("Config_Professores")
                        if user_bloqueio == "Todos":
                            for i in range(2, len(wks_p.get_all_values())+1): wks_p.update_cell(i, 6, "Ativo")
                        else: celula = wks_p.find(user_bloqueio); wks_p.update_cell(celula.row, 6, "Ativo")
                        st.cache_data.clear(); st.rerun()

    elif st.session_state.pagina == "Cadastro":
        st.session_state.pagina = "Registro"; st.rerun()
