import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import time
import io
import pytz

# Configuração do fuso horário correto de Roraima
fuso_roraima = pytz.timezone('America/Boa_Vista')

# Esta variável garante a data certa em Boa Vista, mesmo rodando no servidor da nuvem
data_atual = datetime.now(fuso_roraima).date()

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

def carregar_agendamentos():
    try:
        sh = conectar_google_sheets()
        try:
            wks = sh.worksheet("Agendamentos_Equipamentos")
        except:
            # Cria a aba caso ela não exista na planilha
            wks = sh.add_worksheet(title="Agendamentos_Equipamentos", rows="1000", cols="7")
            wks.append_row(["Data_Registro", "Equipamento", "Professor", "Data_Uso", "Turno", "Horario", "Observacao"])
        
        dados = wks.get_all_records()
        return pd.DataFrame(dados), wks
    except Exception as e:
        return pd.DataFrame(), None

def verificar_conflito(equipamento, data_uso, turno, horario):
    df_ag, _ = carregar_agendamentos()
    if df_ag.empty:
        return False
    
    # Verifica se já existe agendamento para o mesmo item, dia, turno e aula
    conflito = df_ag[
        (df_ag['Equipamento'] == equipamento) & 
        (df_ag['Data_Uso'] == data_uso) & 
        (df_ag['Turno'] == turno) & 
        (df_ag['Horario'] == horario)
    ]
    return not conflito.empty

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
                wks_on.update_cell(celula.row, 2, datetime.now(fuso_roraima).strftime("%d/%m/%Y %H:%M:%S"))
            else:
                wks_on.append_row([usuario, datetime.now(fuso_roraima).strftime("%d/%m/%Y %H:%M:%S")])
        elif acao == "logout":
            if celula:
                wks_on.delete_rows(celula.row)
    except:
        pass

if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'is_master_admin' not in st.session_state: # NEW: Track if user is master admin
    st.session_state.is_master_admin = False

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
            # Validação especial para Administradores e Rodrigo (Master Admin)
            if user_input.lower() == 'admin':
                admin_match = df_profs[df_profs['Usuario'].astype(str).str.lower() == 'admin']
                senha_admin_planilha = str(admin_match.iloc[0]['Senha']).strip() if not admin_match.empty else "admin" # Fallback if 'admin' not in df_profs
                if str(pass_input).strip() == senha_admin_planilha:
                    st.session_state.logado = True
                    if not admin_match.empty:
                        st.session_state.user_data = admin_match.iloc[0].to_dict()
                    else:
                        st.session_state.user_data = {'Professor': 'Administrador', 'Usuario': 'admin', 'Senha': senha_admin_planilha, 'Turmas': 'Todas', 'Disciplinas': 'Todas'}
                    st.session_state.is_master_admin = True # Admin is a master admin
                    atualizar_presenca("admin", "login")
                    st.session_state.pagina = "Registro"
                    st.success("Login realizado com sucesso!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Senha incorreta para Admin.")
                    
            elif user_input.lower() == 'rodrigo':
                rodrigo_match = df_profs[df_profs['Usuario'].astype(str).str.lower() == 'rodrigo']
                if not rodrigo_match.empty:
                    senha_rodrigo_planilha = str(rodrigo_match.iloc[0]['Senha']).strip()
                    if str(pass_input).strip() == senha_rodrigo_planilha:
                        st.session_state.logado = True
                        st.session_state.user_data = rodrigo_match.iloc[0].to_dict() # Use full data from df_profs
                        st.session_state.is_master_admin = True # Ativa os privilégios totais de Master
                        atualizar_presenca("rodrigo", "login")
                        st.session_state.pagina = "Registro"
                        st.success("Login Master realizado com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Senha incorreta para Rodrigo.")
                else:
                    st.error("Usuário 'rodrigo' não encontrado na configuração de professores.")
            else: # Login de usuários regulares
                match = df_profs[(df_profs['Usuario'].astype(str) == user_input) & (df_profs['Senha'].astype(str) == pass_input)]
                if not match.empty:
                    user_row = match.iloc[0]
                    if "Status" in user_row and str(user_row["Status"]).upper() == "BLOQUEADO":
                        st.error("Este usuário está bloqueado pelo Administrador Master.")
                    else:
                        st.session_state.logado = True
                        st.session_state.user_data = user_row.to_dict()
                        st.session_state.is_master_admin = False # Usuários regulares não são master admin
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
            hoje_data = datetime.now(fuso_roraima).strftime("%d/%m/%Y")
            for u in users_on:
                if u['Ultimo_Acesso'].startswith(hoje_data):
                    st.sidebar.caption(f"👤 {u['Usuario']}")
    except:
        pass

    st.sidebar.divider()
    
    if st.sidebar.button("Registro", key="btn_desempenho", use_container_width=True):
        st.session_state.pagina = "Registro"
        st.rerun()

    if st.sidebar.button("Ocorrências", key="btn_ocorrencias_nav", use_container_width=True):
        st.session_state.pagina = "Ocorrencias"
        st.rerun()

    if st.sidebar.button("Avaliações", key="btn_avaliacoes_nav", use_container_width=True):
        st.session_state.pagina = "Avaliações"
        st.rerun()

    # NOVO LOCAL: Botão posicionado logo abaixo de Ocorrências
    if st.sidebar.button('📅 Agendar Equipamentos', key="btn_agendar_equipamentos_nav", use_container_width=True):
        st.session_state.pagina = 'Agendamento de Equipamentos'
        st.rerun()

    # All logged-in users can see "Segurança" to change their own password
    if st.sidebar.button("Segurança", key="btn_seguranca", use_container_width=True):
        st.session_state.pagina = "Segurança"
        st.rerun()

    # Apenas master-admins veem "Cadastro" e "Atualizar Dados"
    if st.session_state.get('is_master_admin', False):
        if st.sidebar.button("Cadastro", key="btn_cadastro", use_container_width=True):
            st.session_state.pagina = "Cadastro"
            st.rerun()
        
        if st.sidebar.button("Atualizar Dados", key="btn_atualizar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    if st.sidebar.button("Sair", key="btn_sair", use_container_width=True):
        atualizar_presenca(st.session_state.user_data['Usuario'], "logout")
        st.session_state.logado = False
        st.session_state.is_master_admin = False # NEW: Reset master admin status on logout
        st.session_state.pagina = "Registro"
        st.rerun()

    is_soe = "SOE" in str(st.session_state.user_data.get('Disciplinas', ""))

    pagina_atual = st.session_state.get("pagina", "Registro")

    if pagina_atual == "Registro":
        st.title("📊 Desempenho do Aluno")
        
        # Cria a navegação interna por abas na parte superior da tela
        aba_selecionada = st.radio(
            "Selecione a ação desejada:",
            ["Novo registro", "Visualizar registros"],
            horizontal=True
        )
        
        st.markdown("---")
        
        # --- SUB-ABA: NOVO REGISTRO ---
        if aba_selecionada == "Novo registro":
            st.subheader("📝 Cadastrar Novo Desempenho")
            
            if is_soe:
                st.info("Você está logado como SOE. Este módulo é apenas para visualização de períodos e turmas.")
            
            hoje = data_atual
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

            # Changed: Use is_master_admin for admin/rodrigo check
            if st.session_state.get('is_master_admin', False) or is_soe:
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
                # Changed: Use is_master_admin for admin/rodrigo check
                if st.session_state.get('is_master_admin', False):
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
                    btn_salvar = st.form_submit_button("GRAVAR NA PLANILHA", disabled=(bimestre_ativo == "Bloqueado" or is_soe))

            if btn_salvar:
                if is_soe:
                    st.error("Usuários SOE não possuem permissão para realizar registros.")
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
                            datetime.now(fuso_roraima).strftime("%d/%m/%Y %H:%M:%S"),
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

# --- SUB-ABA: VISUALIZAR REGISTROS ---
        elif aba_selecionada == "Visualizar registros":
            st.subheader("📋 Histórico e Relatórios de Desempenho")
            try:
                sh = conectar_google_sheets()
                wks_reg = sh.worksheet("Registros_Ocorrencias")
                dados_brutos = wks_reg.get_all_values()
                
                if len(dados_brutos) > 1:
                    df_reg = pd.DataFrame(dados_brutos[1:], columns=dados_brutos[0])
                    
                    # CORREÇÃO CRÍTICA: Mapeia o índice REAL da linha na planilha ANTES de aplicar qualquer filtro por conteúdo
                    df_reg['ID_Original'] = range(2, len(df_reg) + 2)
                    
                    # Filtro padrão para separar o desempenho
                    df_reg = df_reg[~df_reg[df_reg.columns[6]].astype(str).str.contains("OCORRÊNCIA:", na=False)]
                    
                    colunas_df = df_reg.columns.tolist()
                    
                    col_f1, col_f2, col_f3 = st.columns(3)
                    with col_f1:
                        col_bim = 'Bimestre' if 'Bimestre' in colunas_df else colunas_df[5]
                        lista_bimestres = ["Todos"] + sorted(df_reg[col_bim].unique().astype(str).tolist())
                        bim_filtro = st.selectbox("Filtrar por Bimestre", lista_bimestres)
                    
                    with col_f2:
                        col_turma = 'Turma' if 'Turma' in colunas_df else colunas_df[2]
                        if st.session_state.get('is_master_admin', False) or is_soe:
                            opcoes_turmas_reg = sorted(df_reg[col_turma].unique().astype(str).tolist())
                        else:
                            turmas_vinc = str(st.session_state.user_data.get('Turmas', "")).split(", ")
                            opcoes_turmas_reg = sorted([t.strip() for t in turmas_vinc if t.strip()])
                        turma_filtro = st.multiselect("Filtrar por Turma", options=opcoes_turmas_reg, default=[])

                    with col_f3:
                        col_disc_data = colunas_df[4]
                        opcoes_disciplinas_reg = sorted(df_reg[col_disc_data].unique().astype(str).tolist())
                        disciplina_filtro = st.multiselect("Filtrar por Disciplina", options=opcoes_disciplinas_reg, default=[])
                    
                    df_filtrado = df_reg.copy()
                    
                    if bim_filtro != "Todos":
                        df_filtrado = df_filtrado[df_filtrado[col_bim].astype(str) == bim_filtro]
                    
                    if turma_filtro:
                        df_filtrado = df_filtrado[df_filtrado[col_turma].astype(str).isin(turma_filtro)]
                    else:
                        if not st.session_state.get('is_master_admin', False) and not is_soe:
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
                        worksheet.set_paper(9) # A4
                        worksheet.set_margins(0.5, 0.5, 0.5, 0.5)
                        worksheet.fit_to_pages(1, 0)

                        header_format = workbook.add_format({
                            'bold': True, 
                            'bg_color': '#D7E4BC', 
                            'border': 1,
                            'align': 'center',
                            'valign': 'vcenter'
                        })
                        
                        wrap_format = workbook.add_format({
                            'text_wrap': True, 
                            'valign': 'top',
                            'border': 1
                        })

                        worksheet.set_column('A:A', 6, wrap_format)   # Turma
                        worksheet.set_column('B:B', 25, wrap_format)  # Aluno
                        worksheet.set_column('C:C', 10, wrap_format)  # Periodo
                        worksheet.set_column('D:D', 28, wrap_format)  # Disciplina / Prof.
                        worksheet.set_column('E:E', 25, wrap_format)  # Tipo_Registro
                        worksheet.set_column('F:F', 40, wrap_format)  # Descrição_Detalhada

                        for col_num, value in enumerate(df_exibicao_viz.columns.values):
                            worksheet.write(0, col_num, value, header_format)

                    processed_data = output.getvalue()

                    st.download_button(
                        label="📥 Baixar Relatório de Desempenho (A4 Paisagem)",
                        data=processed_data,
                        file_name=f'Relatorio_Desempenho_{datetime.now(fuso_roraima).strftime("%Y%m%d_%H%M")}.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        use_container_width=True
                    )

                    st.divider()
                    st.subheader("📝 Editar ou 🗑️ Excluir Registros de Desempenho")
                    
                    if is_soe:
                        st.info("Usuários SOE não possuem permissão para realizar registros.")
                    else:
                        col_exc1, col_exc2 = st.columns(2)
                        
                        with col_exc1:
                            st.markdown("**Gerenciar registro individual**")
                            if st.session_state.get('is_master_admin', False):
                                df_edit_proprio = df_filtrado
                            else:
                                discs_usuario_reg = [d.strip().lower() for d in str(st.session_state.user_data.get('Disciplinas', "")).split(", ") if d.strip()]
                                df_edit_proprio = df_filtrado[df_filtrado[colunas_df[4]].astype(str).str.lower().isin(discs_usuario_reg)]
                            
                            if not df_edit_proprio.empty:
                                opcoes_edit = {f"{row[col_data]} - {row[colunas_df[3]]} ({row[colunas_df[4]]})": row['ID_Original'] for _, row in df_edit_proprio.iterrows()}
                                selecionado_para_edit = st.selectbox("Selecione o registro para modificar (Apenas suas disciplinas)", [""] + list(opcoes_edit.keys()))
                                
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
                                                if edit_desempenho:
                                                    itens_finais_edit.append(edit_desempenho)
                                                itens_finais_edit.extend(edit_tipo_selecao)
                                                tipo_formatado_edit = ", ".join(itens_finais_edit)
                                                
                                                # SEGURANÇA ADICIONAL: Procura a correspondência exata antes da gravação direta
                                                valores_verificacao = wks_reg.get_all_values()
                                                linha_alvo_sheets = None
                                                for idx_v, linha_v in enumerate(valores_verificacao[1:], start=2):
                                                    if linha_v[0] == dados_reg_edit[col_data] and linha_v[3] == dados_reg_edit[colunas_df[3]]:
                                                        linha_alvo_sheets = idx_v
                                                        break
                                                
                                                if linha_alvo_sheets:
                                                    wks_reg.update_cell(linha_alvo_sheets, 7, tipo_formatado_edit)
                                                    wks_reg.update_cell(linha_alvo_sheets, 8, edit_obs)
                                                    st.success("Registro de desempenho alterado e salvo com sucesso!")
                                                    st.cache_data.clear()
                                                    time.sleep(1.5)
                                                    st.rerun()
                                                else:
                                                    st.error("O registro não foi encontrado para atualização.")
                                            except Exception as e:
                                                st.error(f"Erro ao editar: {e}")
                                                
                                        if btn_confirmar_exc:
                                            try:
                                                # SEGURANÇA ADICIONAL: Procura a linha correta pelo Timestamp e Aluno
                                                valores_verificacao = wks_reg.get_all_values()
                                                linha_alvo_sheets = None
                                                for idx_v, linha_v in enumerate(valores_verificacao[1:], start=2):
                                                    if linha_v[0] == dados_reg_edit[col_data] and linha_v[3] == dados_reg_edit[colunas_df[3]]:
                                                        linha_alvo_sheets = idx_v
                                                        break
                                                
                                                if linha_alvo_sheets:
                                                    wks_reg.delete_rows(linha_alvo_sheets)
                                                    st.success("Registro de desempenho excluído permanentemente!")
                                                    st.cache_data.clear()
                                                    time.sleep(1.5)
                                                    st.rerun()
                                                else:
                                                    st.error("O registro já foi removido ou não pôde ser encontrado.")
                                            except Exception as e:
                                                st.error(f"Erro ao excluir: {e}")
                            else:
                                st.info("Nenhum registro de suas disciplinas disponível para gerenciar no filtro atual.")

                        with col_exc2:
                            if st.session_state.get('is_master_admin', False):
                                st.markdown("**Exclusão em massa**")
                                if bim_filtro != "Todos":
                                    if turma_filtro and len(turma_filtro) == 1:
                                        t_unica = turma_filtro[0]
                                        st.warning(f"Apagar TODOS os registros de {t_unica} no {bim_filtro}?")
                                        if st.button(f"🚨 EXCLUIR TURMA: {t_unica} - {bim_filtro}"):
                                            indices_massa = sorted(df_filtrado['ID_Original'].tolist(), reverse=True)
                                            for idx in indices_massa:
                                                wks_reg.delete_rows(idx)
                                            st.success(f"Foram excluídos {len(indices_massa)} registros.")
                                            st.cache_data.clear()
                                            st.rerun()
                                    
                                    st.divider()
                                    st.error(f"Zerar BIMESTRE: Apagar TODOS os registros do {bim_filtro}?")
                                    if st.button(f"💥 EXCLUIR TUDO DO {bim_filtro}"):
                                        df_massa_bim = df_reg[df_reg[col_bim].astype(str) == bim_filtro]
                                        if not df_massa_bim.empty:
                                            indices_bim = sorted(df_massa_bim['ID_Original'].tolist(), reverse=True)
                                            for idx in indices_bim:
                                                wks_reg.delete_rows(idx)
                                            st.success(f"Foram excluídos {len(indices_bim)} registros do {bim_filtro}.")
                                            st.cache_data.clear()
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

    elif pagina_atual == "Ocorrencias":
        st.markdown("<h1 style='color: #B91C1C;'>🚨 Sistema de Registro de Ocorrências</h1>", unsafe_allow_html=True)
        
        aba_nova_oc, aba_visualizar_oc = st.tabs(["🚨 Nova Ocorrência", "📋 Visualizar Ocorrências"])
        
        # Initialize df_ocorrencias and wks_oc for use in both tabs
        df_ocorrencias = pd.DataFrame()
        wks_oc = None
        try:
            sh_oc = conectar_google_sheets()
            try:
                wks_oc = sh_oc.worksheet("Dados_Ocorrencias")
            except gspread.exceptions.WorksheetNotFound:
                # Create if not exists, with headers
                wks_oc = sh_oc.add_worksheet(title="Dados_Ocorrencias", rows="1000", cols="8")
                wks_oc.append_row(["Data_Registro", "Turma", "Aluno", "Categoria", "Descricao", "Encaminhamento", "Responsavel", "Setor_Responsavel"])
            
            dados_ocorrencias = wks_oc.get_all_records()
            if dados_ocorrencias:
                df_ocorrencias = pd.DataFrame(dados_ocorrencias)
        except Exception as e:
            st.error(f"Erro ao carregar dados de ocorrências: {e}")
            df_ocorrencias = pd.DataFrame() # Ensure it's empty on error

        with aba_nova_oc:
            st.markdown("### 📝 Preencher Nova Ficha de Ocorrência")
            
            # Logic for turmas and students, adapted from original code
            if st.session_state.get('is_master_admin', False) or is_soe:
                todas_turmas = sorted(df_alunos['Turma'].unique().astype(str)) if not df_alunos.empty else []
            else:
                turmas_vinc = str(st.session_state.user_data.get('Turmas', "")).split(", ")
                todas_turmas = sorted([t.strip() for t in turmas_vinc if t.strip()])
            
            if not todas_turmas:
                st.warning("Nenhuma turma disponível para seleção. Verifique o cadastro de alunos ou suas permissões.")
                turma_sel = "Nenhuma turma"
                alunos_da_turma = []
            else:
                col_o1, col_o2 = st.columns([1, 4])
                with col_o1:
                    turma_sel = st.selectbox("1. Turma", todas_turmas, key="turma_oc")
                with col_o2:
                    alunos_da_turma = df_alunos[df_alunos['Turma'].astype(str) == turma_sel]['Nome_Aluno'].tolist()
            
            aluno_sel = st.selectbox("2. Aluno", sorted(alunos_da_turma) if alunos_da_turma else ["Nenhum aluno encontrado"], key="aluno_oc")
                
            col_o3, col_o4 = st.columns(2)
            with col_o3:
                categoria_oc = st.selectbox("3. Classificação", ["Indisciplina em Sala", "Agressão Verbal / Física", "Falta de Material / Desinteresse", "Atrasos recorrentes", "Uso indevido de Celular", "Outros Aspectos Atitudinais"])
            with col_o4:
                encaminhamento_oc = st.selectbox("4. Ação Tomada / Encaminhamento", ["Advertência Verbal", "Comunicação aos Pais/Responsáveis", "Encaminhamento ao SOE", "Afastamento de Sala", "Termo de Compromisso Assinado"])
                
            descricao_oc = st.text_area("5. Descrição Detalhada do Fato", placeholder="Descreva cronologicamente o acontecido com máxima clareza e imparcialidade...")
            
            # Determine 'Responsavel' and 'Setor_Responsavel' based on session state
            responsavel_oc = st.session_state.user_data.get('Usuario', 'Desconhecido')
            setor_responsavel_oc = "Professor"
            if is_soe:
                setor_responsavel_oc = "SOE"
            elif st.session_state.get('is_master_admin', False):
                setor_responsavel_oc = "Administrador"

            if st.button("💾 Salvar Registro de Ocorrência", use_container_width=True, type="primary"):
                if not aluno_sel or aluno_sel == "Nenhum aluno encontrado":
                    st.error("Selecione um estudante válido.")
                elif wks_oc is None:
                    st.error("Não foi possível conectar à planilha de ocorrências. Tente novamente mais tarde.")
                else:
                    with st.spinner("Registrando ocorrência..."):
                        try:
                            nova_linha_oc = [
                                datetime.now(fuso_roraima).strftime("%d/%m/%Y %H:%M:%S"),
                                turma_sel,
                                aluno_sel,
                                categoria_oc,
                                descricao_oc,
                                encaminhamento_oc,
                                responsavel_oc,
                                setor_responsavel_oc
                            ]
                            wks_oc.append_row(nova_linha_oc)
                            st.success(f"Ocorrência de {aluno_sel} adicionada ao prontuário escolar!")
                            st.cache_data.clear()
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")
                            
        with aba_visualizar_oc:
            st.markdown("### 📋 Histórico Geral de Ocorrências")
            if not df_ocorrencias.empty:
                st.dataframe(df_ocorrencias, use_container_width=True)
                
                if st.session_state.get('is_master_admin', False) or is_soe:
                    st.markdown("#### 🗑️ Zona de Administração de Conflitos")
                    
                    max_idx = len(df_ocorrencias) - 1
                    if max_idx < 0:
                        st.info("Não há ocorrências para excluir.")
                    else:
                        idx_excluir = st.number_input("Digite o índice da linha para excluir (0 a X)", min_value=0, max_value=max_idx, step=1, key="idx_excluir_oc")
                        if st.button("🗑️ Remover Ocorrência Permanentemente", key="btn_remover_oc_perm"):
                            if wks_oc is None:
                                st.error("Não foi possível conectar à planilha de ocorrências para exclusão.")
                            else:
                                try:
                                    wks_oc.delete_rows(int(idx_excluir) + 2)
                                    st.success("Registro removido com sucesso!")
                                    st.cache_data.clear()
                                    time.sleep(1.5)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao deletar: {e}")
            else:
                st.info("Nenhuma ocorrência registrada.")

    elif st.session_state.pagina == "Segurança":
        st.title("🔒 Segurança")
        st.subheader("Alterar Minha Senha")
        
        user_atual = st.session_state.user_data['Usuario']
        
        # Bloqueia apenas o 'admin' genérico de mudar a senha por aqui, mas PERMITE o 'rodrigo' e os professores
        if user_atual == "admin":
            st.warning("O usuário 'admin' padrão não pode alterar a senha por esta interface.")
        else:
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
                    elif len(nova_senha_prof.strip()) == 0:
                        with col_senha_p2:
                            st.error("A senha não pode ficar em branco.")
                    else:
                        try:
                            sh = conectar_google_sheets()
                            wks_p = sh.worksheet("Config_Professores")
                            
                            # Encontra a linha do 'rodrigo' ou do professor logado
                            celula = wks_p.find(str(user_atual))
                            
                            # Atualiza a senha na coluna 3 (Coluna da Senha)
                            wks_p.update_cell(celula.row, 3, str(nova_senha_prof).strip())
                            
                            with col_senha_p2:
                                msg_placeholder_ok_p = st.empty()
                                msg_placeholder_ok_p.success("✅ Sua senha foi alterada com sucesso!")
                                st.cache_data.clear()
                                time.sleep(2)
                                msg_placeholder_ok_p.empty()
                                st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao atualizar a senha na planilha: {e}")

    # =========================================================================
    # MÓDULO INDEPENDENTE: AVALIAÇÕES (COM CAPTURA DE CÂMERA E HISTÓRICO SALVO)
    # =========================================================================
    elif pagina_atual == "Avaliações":
        # Inicializa a lista de histórico global na memória caso não exista
        if 'historico_correcoes' not in st.session_state:
            st.session_state['historico_correcoes'] = []

        # Captura dinamicamente o nome do professor logado para o cabeçalho
        if 'user_data' in st.session_state and st.session_state.user_data.get('Professor'):
            nome_professor_cabecalho = st.session_state.user_data.get('Professor')
        else:
            nome_professor_cabecalho = st.session_state.get('username', 'Administrador')

        # SE NÃO FOR ADMIN MASTER: Mostra apenas a mensagem de em construção
        if not st.session_state.get('is_master_admin', False):
            st.title("📝 Sistema de Gestão de Avaliações")
            st.warning("🚧 **Esta função está em desenvolvimento!** Brevemente, professores e administradores poderão criar e corrigir avaliações de forma automatizada por aqui. Fique atento às novidades!")
            
            if st.button("Voltar para o Início", use_container_width=True):
                st.session_state.pagina = "Registro"
                st.rerun()
                
        # SE FOR ADMIN MASTER: Carrega o sistema completo de forma segura
        else:
            st.title("📝 Sistema de Gestão de Avaliações")
            aba_av_escolhida = st.radio("Selecione a ação desejada:", ["Criar", "Correção", "Histórico de Notas"], horizontal=True)
            st.markdown("---")
            
            if aba_av_escolhida == "Criar":
                st.subheader("✨ Elaborar Nova Avaliação e Gabarito")
                
                if 'user_data' in st.session_state and st.session_state.user_data.get('Disciplinas'):
                    disc_professor = st.session_state.user_data.get('Disciplinas').split(', ')[0] # Pega a primeira disciplina se houver
                    disciplinas_av = [disc_professor]
                    st.success(f"📚 Disciplina identificada pelo seu perfil: **{disc_professor}**")
                else:
                    disciplinas_av = sorted(df_discs['Disciplina'].unique().astype(str)) if not df_discs.empty else ["Geografia", "História", "Português", "Matemática"]
                
                col_cfg1, col_cfg2 = st.columns(2)
                with col_cfg1:
                    disciplina_sel_av = st.selectbox("Selecione a Disciplina correspondente", disciplinas_av, key="disciplina_sel_av")
                    nota_maxima = st.number_input("Defina a Nota Máxima da Avaliação:", min_value=1.0, max_value=100.0, value=10.0, step=0.5)
                with col_cfg2:
                    num_questoes = st.number_input("Quantidade Total de Questões:", min_value=1, max_value=20, value=5, step=1)
                    
                st.info(f"ℹ️ Configure os valores individuais e as alternativas. A soma deve totalizar exatamente **{nota_maxima:.2f}** pontos.")
                st.markdown("### 📋 Formulação das Questões")
                
                questoes_dados = []
                soma_valores_atual = 0.0
                valor_sugerido = round(nota_maxima / int(num_questoes), 2)
                
                for i in range(int(num_questoes)):
                    with st.expander(f"📝 Questão {i+1}", expanded=True):
                        col_enum, col_val = st.columns([4, 1])
                        with col_enum:
                            enunciado = st.text_area(f"Enunciado da Questão {i+1}:", key=f"enunciado_av_{i}", placeholder="Texto da questão...")
                        with col_val:
                            valor_questao = st.number_input(f"Valor (Pts):", min_value=0.0, max_value=float(nota_maxima), value=float(valor_sugerido), step=0.1, key=f"valor_av_{i}")
                        
                        st.markdown("**Alternativas de Resposta:**")
                        col_a, col_b = st.columns(2)
                        with col_a:
                            opc_a = st.text_input(f"Opção A:", key=f"opc_a_av_{i}", placeholder="Primeira opção...")
                            opc_b = st.text_input(f"Opção B:", key=f"opc_b_av_{i}", placeholder="Segunda opção...")
                        with col_b:
                            opc_c = st.text_input(f"Opção C:", key=f"opc_c_av_{i}", placeholder="Terceira opção...")
                            opc_d = st.text_input(f"Opção D:", key=f"opc_d_av_{i}", placeholder="Quarta opção...")
                        
                        # Adição do selectbox para definir qual das alternativas está correta
                        alternativa_correta = st.selectbox(f"Selecione a Alternativa Correta para a Questão {i+1}:", ["A", "B", "C", "D"], key=f"gabarito_av_{i}")
                            
                        questoes_dados.append({
                            "numero": i + 1,
                            "enunciado": enunciado,
                            "valor": valor_questao,
                            "alternativas": {"A": opc_a, "B": opc_b, "C": opc_c, "D": opc_d},
                            "correta": alternativa_correta
                        })
                        soma_valores_atual += valor_questao

                st.markdown("---")
                if round(soma_valores_atual, 2) == round(nota_maxima, 2):
                    st.success(f"✅ Soma dos pontos perfeita: **{soma_valores_atual:.2f} / {nota_maxima:.2f}**")
                else:
                    st.warning(f"⚠️ Atenção: A soma atual está em **{soma_valores_atual:.2f}** pontos. Ajuste para atingir **{nota_maxima:.2f}**.")

                if st.button("🖨️ Gerar e exportar folha de prova com cartão resposta", use_container_width=True, type="primary"):
                    if round(soma_valores_atual, 2) != round(nota_maxima, 2):
                        st.error(f"❌ Não é possível salvar. A soma dos valores das questões ({soma_valores_atual:.2f} pts) difere da Nota Máxima estipulada ({nota_maxima:.2f} pts).")
                    elif any(q["enunciado"].strip() == "" or q["alternativas"]["A"].strip() == "" or q["alternativas"]["B"].strip() == "" or q["alternativas"]["C"].strip() == "" or q["alternativas"]["D"].strip() == "" for q in questoes_dados):
                        st.error("❌ Preenchimento obrigatório: Existem campos de enunciado ou alternativas em branco. Verifique todas as questões.")
                    else:
                        with st.spinner("💾 Gravando dados da avaliação no banco de dados..."):
                            try:
                                banco_dados = conectar_google_sheets()
                                try:
                                    wks_avaliacoes = banco_dados.worksheet("Dados_Avaliacoes")
                                except gspread.exceptions.WorksheetNotFound:
                                    wks_avaliacoes = banco_dados.add_worksheet(title="Dados_Avaliacoes", rows="1000", cols="6")
                                    wks_avaliacoes.append_row(["Data_Criacao", "Responsavel", "Disciplina", "Nota_Maxima", "Qtd_Questoes", "Dados_Questoes_JSON"])
                                
                                dados_questoes_serializados = str([{f"Q{q['numero']}": {"enunciado": q['enunciado'], "pts": q['valor'], "opcoes": q['alternativas'], "gabarito": q['correta']}} for q in questoes_dados])
                                usuario_autor = st.session_state.user_data.get('Professor', 'Admin_Master') # Adjusted to use 'Professor' from session_state
                                timestamp_atual = datetime.now(fuso_roraima).strftime("%d/%m/%Y %H:%M:%S")
                                
                                nova_linha_avaliacao = [
                                    timestamp_atual,
                                    usuario_autor,
                                    disciplina_sel_av,
                                    nota_maxima,
                                    int(num_questoes),
                                    dados_questoes_serializados
                                ]
                                
                                wks_avaliacoes.append_row(nova_linha_avaliacao)
                                st.success("✨ Avaliação criada com sucesso e salva de forma persistente!")
                                st.balloons()
                                st.cache_data.clear()
                                time.sleep(2.0)
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro ao gravar dados no Google Sheets: {e}")

            # --- SUB-ABA: CORREÇÃO DE AVALIAÇÕES ---
            elif aba_av_escolhida == "Correção":
                st.subheader("📸 Leitura Automatizada e Correção por ID")
                st.write("Aponte o cartão-resposta para a câmera ou bipe/digite o ID da avaliação.")
                
                # Campo para receber o ID bipado via leitor de código de barras/digitado de forma rápida
                id_detectado = st.text_input("🔢 ID da Avaliação (Bipado ou Detectado):", key="id_prova_bipado", placeholder="Ex: 1001")
                
                # Abre a câmera imediatamente em tela para captura
                img_file = st.camera_input("Capturar Cartão Resposta", key="camera_correcao_automatica")
                
                # Estrutura lógica de processamento
                if img_file is not None or id_detectado:
                    st.info("🔄 Processando dados da avaliação...")
                    
                    # Se uma imagem foi capturada e o ID ainda não foi digitado, tentamos extrair o ID da prova do cabeçalho
                    if img_file is not None and not id_detectado:
                        # [Lógica do OpenCV/ZBar ou processamento de imagem para ler as bolinhas de ID ou QR Code]
                        # Exemplo fictício da variável que seu leitor extrai da imagem:
                        # id_detectado = extrair_id_da_imagem(img_file)
                        pass

                    if not id_detectado:
                        st.warning("⚠️ Não foi possível identificar o ID da prova automaticamente na imagem. Digite o ID no campo acima para prosseguir.")
                    else:
                        # Carrega dinamicamente a base de dados de gabaritos para encontrar a prova correspondente ao ID
                        try:
                            sh = conectar_google_sheets()
                            wks_gav = sh.worksheet("Gabaritos_Avaliacoes") 
                            dados_gabaritos = wks_gav.get_all_records()
                            df_gabaritos = pd.DataFrame(dados_gabaritos)
                        except Exception as e:
                            df_gabaritos = pd.DataFrame()
                            st.error(f"Erro ao conectar ao banco de dados: {e}")

                        if not df_gabaritos.empty:
                            # Garante que a comparação seja feita como string limpa
                            df_gabaritos['ID_Prova'] = df_gabaritos['ID_Prova'].astype(str).str.strip()
                            prova_alvo = df_gabaritos[df_gabaritos['ID_Prova'] == str(id_detectado).strip()]
                            
                            if prova_alvo.empty:
                                st.error(f"❌ Nenhuma avaliação com o ID '{id_detectado}' foi localizada no banco de dados.")
                            else:
                                dados_da_prova = prova_alvo.iloc[0]
                                st.success(f"🎯 Prova Identificada com Sucesso! | Disciplina: {dados_da_prova.get('Disciplina')} | Turma: {dados_da_prova.get('Turma')}")
                                
                                # --- DAQUI PARA BAIXO O SISTEMA CONTINUA A PROCESSAR AS RESPOSTAS DO CARTÃO ---
                                st.write("Analisando respostas do aluno...")
                                
                                # Aqui o seu código OpenCV existente roda usando os dados_da_prova['Gabarito'] 
                                # para calcular a nota e salvar o resultado automaticamente...

            elif aba_av_escolhida == "Histórico de Notas":
                st.subheader("📋 Histórico Completo de Provas Corrigidas")
                st.markdown("Consulte abaixo todas as avaliações escaneadas pela câmera e arquivadas no sistema:")
                
                if not st.session_state['historico_correcoes']:
                    st.info("ℹ️ Nenhuma folha de respostas foi corrigida nesta sessão até o momento.")
                else:
                    df_historico_exibir = pd.DataFrame(st.session_state['historico_correcoes'])
                    
                    # Formata a visualização da pontuação para melhor leitura do professor
                    df_historico_exibir['Pontuação'] = df_historico_exibir.apply(
                        lambda r: f"{r['Nota Obtida']:.2f} / {r['Nota Máxima']:.2f}", axis=1
                    )
                    
                    # Remove colunas brutas para deixar a tabela visual limpa
                    tabela_limpa = df_historico_exibir[['Data/Hora', 'Aluno', 'Turma', 'Disciplina', 'ID Prova', 'Pontuação']]
                    
                    st.dataframe(tabela_limpa, use_container_width=True)
                    
                    # Botão extra para limpar o histórico caso desejado
                    if st.button("🗑️ Limpar Histórico de Correções", use_container_width=True):
                        st.session_state['historico_correcoes'] = []
                        st.success("Histórico limpo com sucesso!")
                        time.sleep(1)
                        st.rerun()

    elif pagina_atual == "Cadastro" and st.session_state.get('is_master_admin', False):
        st.title("⚙️ Painel de Cadastro")
        abas = ["Turmas/Alunos", "Disciplinas", "Gerenciar Usuários", "Alterar Senha", "Período de Lançamento"]
        # Changed: Use is_master_admin for "Bloqueio Master" tab, and ensure it's specifically 'rodrigo'
        if st.session_state.get('is_master_admin', False) and st.session_state.user_data['Usuario'] == "rodrigo":
            abas.append("Bloqueio Master")
        tabs = st.tabs(abas)
        
        with tabs[0]:
            st.subheader("Gerenciar Alunos e Turmas")
            opcao_cadastro = st.radio("Selecione uma Ação", ["Individual", "Em Massa (Excel/Word)", "Transferir Aluno", "Excluir Aluno", "Limpar turma"])
            
            if opcao_cadastro == "Individual":
                with st.form("form_aluno", clear_on_submit=True):
                    nova_turma = st.text_input("Turma (Ex: 101, 202)")
                    novo_aluno = st.text_input("Nome Completo do Aluno")
                    col_btn_ind, col_msg_ind = st.columns([1, 2])
                    with col_btn_ind:
                        btn_salvar_ind = st.form_submit_button("Salvar Aluno")
                    
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
                                    msg_placeholder_ind = st.empty()
                                    msg_placeholder_ind.success("Aluno cadastrado com sucesso")
                                    st.cache_data.clear()
                                    time.sleep(3)
                                    msg_placeholder_ind.empty()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")
            
            elif opcao_cadastro == "Em Massa (Excel/Word)":
                with st.form("form_aluno_massa", clear_on_submit=True):
                    turma_massa = st.text_input("Turma para todos os alunos (Ex: 101)")
                    lista_nomes = st.text_area("Cole aqui a lista de nomes (um por linha)")
                    col_btn_massa, col_msg_massa = st.columns([1, 2])
                    with col_btn_massa:
                        btn_salvar_massa = st.form_submit_button("Salvar Todos os Alunos")
                    
                    if btn_salvar_massa:
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
                                    with col_msg_massa:
                                        msg_placeholder_massa_err = st.empty()
                                        msg_placeholder_massa_err.error(f"Não foi possível cadastrar: Os seguintes alunos já existem nesta turma: {', '.join(ja_existentes)}")
                                        time.sleep(3)
                                        msg_placeholder_massa_err.empty()
                                elif novas_linhas:
                                    sh = conectar_google_sheets()
                                    wks_a = sh.worksheet("Config_Alunos")
                                    wks_a.append_rows(novas_linhas)
                                    with col_msg_massa:
                                        msg_placeholder_massa = st.empty()
                                        msg_placeholder_massa.success(f"{len(nomes)} alunos cadastrados com sucesso!")
                                        st.cache_data.clear()
                                        time.sleep(3)
                                        msg_placeholder_massa.empty()
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao cadastrar em massa: {e}")

            elif opcao_cadastro == "Transferir Aluno":
                st.subheader("Transferir Aluno de Turma")
                todas_turmas_cadastradas = sorted(df_alunos['Turma'].unique().astype(str))
                turma_orig = st.selectbox("Turma de Origem", [""] + todas_turmas_cadastradas)
                if turma_orig != "":
                    alunos_orig = df_alunos[df_alunos['Turma'].astype(str) == turma_orig]['Nome_Aluno'].tolist()
                    aluno_a_transf = st.selectbox("Selecione o Aluno para Transferir", [""] + sorted(alunos_orig))
                    turma_dest = st.selectbox("Turma de Destino", [""] + todas_turmas_cadastradas)
                    col_transf_btn, col_transf_msg = st.columns([1, 2])
                    with col_transf_btn:
                        executar = st.button("Executar Transferência")
                    if aluno_a_transf != "" and turma_dest != "" and executar:
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
                                with col_transf_msg:
                                    msg_temp = st.empty()
                                    msg_temp.success("Aluno transferido com sucesso")
                                    st.cache_data.clear()
                                    time.sleep(3)
                                    msg_temp.empty()
                                st.rerun()
                            else:
                                st.error("Aluno não encontrado na base de dados para atualização.")
                        except Exception as e:
                            st.error(f"Erro ao transferir aluno: {e}")

            elif opcao_cadastro == "Excluir Aluno":
                st.subheader("Excluir Aluno Específico")
                todas_turmas_exc = sorted(df_alunos['Turma'].unique().astype(str))
                turma_exc = st.selectbox("Selecione a Turma", [""] + todas_turmas_exc)
                if turma_exc != "":
                    alunos_exc = df_alunos[df_alunos['Turma'].astype(str) == turma_exc]['Nome_Aluno'].tolist()
                    aluno_a_excluir = st.selectbox("Selecione o Aluno para Excluir", [""] + sorted(alunos_exc))
                    col_exc_btn, col_exc_msg = st.columns([1, 2])
                    with col_exc_btn:
                        btn_excluir_def = st.button("❌ EXCLUIR ALUNO DEFINITIVAMENTE")
                    if aluno_a_excluir != "" and btn_excluir_def:
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
                                with col_exc_msg:
                                    placeholder_exc_msg = st.empty()
                                    placeholder_exc_msg.success(f"Aluno {aluno_a_excluir} removido com sucesso")
                                    st.cache_data.clear()
                                    time.sleep(3)
                                    placeholder_exc_msg.empty()
                                st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao excluir aluno: {e}")

            elif opcao_cadastro == "Limpar turma":
                st.subheader("Limpar Todos os Alunos de uma Turma")
                todas_turmas_limpar = sorted(df_alunos['Turma'].unique().astype(str))
                turma_alvo_limpar = st.selectbox("Selecione a Turma para APAGAR TODOS os alunos", [""] + todas_turmas_limpar)
                if turma_alvo_limpar != "":
                    st.warning(f"⚠️ ATENÇÃO: Esta ação apagará TODOS os alunos da turma {turma_alvo_limpar}.")
                    confirmacao_turma = st.checkbox(f"Confirmo que desejo apagar todos os alunos da {turma_alvo_limpar}")
                    col_limpar_btn, col_limpar_msg = st.columns([1, 2])
                    with col_limpar_btn:
                        btn_limpar_exec = st.button(f"🚨 APAGAR ALUNOS DA TURMA {turma_alvo_limpar}")
                    if btn_limpar_exec:
                        if confirmacao_turma:
                            try:
                                sh = conectar_google_sheets()
                                wks_a = sh.worksheet("Config_Alunos")
                                data = wks_a.get_all_values()
                                indices_para_deletar = [i + 1 for i, row in enumerate(data) if row[0] == turma_alvo_limpar]
                                if indices_para_deletar:
                                    for idx in reversed(indices_para_deletar):
                                        wks_a.delete_rows(idx)
                                    with col_limpar_msg:
                                        msg_limp_temp = st.empty()
                                        msg_limp_temp.success(f"Todos os alunos da turma {turma_alvo_limpar} foram removidos com sucesso")
                                        st.cache_data.clear()
                                        time.sleep(3)
                                        msg_limp_temp.empty()
                                    st.rerun()
                                else:
                                    st.info("Nenhum aluno encontrado para esta turma.")
                            except Exception as e:
                                st.error(f"Erro ao limpar turma: {e}")
                        else:
                            st.error("Marque a caixa de confirmação.")

        with tabs[1]:
            st.subheader("Gerenciar Disciplinas")
            with st.form("form_disciplina", clear_on_submit=True):
                nova_disc = st.text_input("Nome da Disciplina")
                col_btn_d, col_msg_d = st.columns([1, 2])
                with col_btn_d:
                    btn_cadastrar_disc = st.form_submit_button("Cadastrar Disciplina")
                if btn_cadastrar_disc:
                    if nova_disc:
                        duplicada_disc = df_discs[df_discs['Disciplina'].astype(str).str.upper() == nova_disc.strip().upper()]
                        if not duplicada_disc.empty:
                            with col_msg_d:
                                msg_placeholder_d_err = st.empty()
                                msg_placeholder_d_err.error(f"Erro: A disciplina '{nova_disc}' já está cadastrada.")
                                time.sleep(3)
                                msg_placeholder_d_err.empty()
                        else:
                            try:
                                sh = conectar_google_sheets()
                                try:
                                    wks_d = sh.worksheet("Config_Disciplinas")
                                except:
                                    wks_d = sh.add_worksheet(title="Config_Disciplinas", rows="100", cols="2")
                                    wks_d.append_row(["Disciplina"])
                                wks_d.append_row([nova_disc])
                                with col_msg_d:
                                    msg_placeholder = st.empty()
                                    msg_placeholder.success(f"Disciplina '{nova_disc}' cadastrada com sucesso")
                                    st.cache_data.clear()
                                    time.sleep(3)
                                    msg_placeholder.empty()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")
                    else:
                        st.error("Informe o nome da disciplina.")

            st.divider()
            st.subheader("Excluir Disciplina")
            if not df_discs.empty:
                disc_lista = sorted(df_discs['Disciplina'].unique().astype(str))
                disc_excluir = st.selectbox("Selecione a disciplina para remover", [""] + disc_lista)
                col_exc_d1, col_exc_d2 = st.columns([1, 2])
                with col_exc_d1:
                    btn_remover_disc = st.button("❌ REMOVER DISCIPLINA")
                if btn_remover_disc:
                    if disc_excluir != "":
                        try:
                            sh = conectar_google_sheets()
                            wks_d = sh.worksheet("Config_Disciplinas")
                            celula = wks_d.find(str(disc_excluir))
                            wks_d.delete_rows(celula.row)
                            with col_exc_d2:
                                placeholder_disc_exc = st.empty()
                                placeholder_disc_exc.success(f"Disciplina '{disc_excluir}' removida com sucesso")
                                st.cache_data.clear()
                                time.sleep(3)
                                placeholder_disc_exc.empty()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao excluir: {e}")
                    else:
                        st.error("Selecione uma disciplina.")
            else:
                st.info("Nenhuma disciplina cadastrada.")

        with tabs[2]:
            st.subheader("Cadastrar Novo Professor")
            with st.form("form_prof", clear_on_submit=True):
                novo_prof = st.text_input("Nome do Professor")
                novo_usuario = st.text_input("Nome de Usuário (Login)")
                nova_senha = st.text_input("Senha", type="password", help="Opcional")
                todas_turmas_disp = sorted(df_alunos['Turma'].unique().astype(str))
                turmas_vinculo = st.multiselect("Vincular Turmas", options=todas_turmas_disp)
                if not df_discs.empty:
                    disciplina_opcoes = sorted(list(set(df_discs['Disciplina'].unique().astype(str).tolist() + ["SOE"])))
                else:
                    disciplina_opcoes = ["Artes", "Educação Física", "Inglês", "Espanhol", "Ensino Religioso", "Projeto de Vida", "SOE"]
                disciplinas_vinculo = st.multiselect("Vincular Disciplinas", options=disciplina_opcoes)
                col_btn_salvar, col_msg_salvar = st.columns([1, 2])
                with col_btn_salvar:
                    btn_salvar_prof = st.form_submit_button("Salvar Professor")
                if btn_salvar_prof:
                    if not novo_prof or not novo_usuario:
                        st.error("Por favor, preencha o nome do professor e o nome de usuário.")
                    else:
                        try:
                            sh = conectar_google_sheets()
                            wks_p = sh.worksheet("Config_Professores")
                            
                            # Carrega os usuários que já existem para fazer a checagem (live from sheet)
                            dados_existentes = wks_p.get_all_records()
                            usuarios_cadastrados = [str(linha.get("Usuario", "")).strip().lower() for linha in dados_existentes]
                            
                            usuario_verificar = str(novo_usuario).strip().lower()
                            
                            # VALIDAÇÃO CRÍTICA: Impede se o nome de usuário (login) já existir
                            if usuario_verificar in usuarios_cadastrados:
                                with col_msg_salvar:
                                    msg_placeholder_prof_err = st.empty()
                                    msg_placeholder_prof_err.error(f"❌ Não é possível cadastrar! O usuário '{novo_usuario}' já existe no sistema. Escolha outro nome de usuário para login.")
                                    time.sleep(3)
                                    msg_placeholder_prof_err.empty()
                            else:
                                # Se não existir, faz o cadastro normalmente
                                turmas_str = ", ".join(turmas_vinculo)
                                disciplinas_str = ", ".join(disciplinas_vinculo)
                                senha_final = str(nova_senha) if nova_senha else ""
                                wks_p.append_row([novo_prof, novo_usuario, senha_final, turmas_str, disciplinas_str, "Ativo"])
                                with col_msg_salvar:
                                    msg_placeholder_prof = st.empty()
                                    msg_placeholder_prof.success("Professor cadastrado com sucesso")
                                    st.cache_data.clear()
                                    time.sleep(3)
                                    msg_placeholder_prof.empty()
                                st.rerun()
                                
                        except Exception as e:
                            st.error(f"Erro ao acessar o banco de dados: {e}")
            
            st.divider()
            st.subheader("Editar ou Excluir Usuário Existente")
            lista_usuarios_edit = df_profs['Usuario'].tolist()
            user_selecionado = st.selectbox("Selecione o Usuário para Modificar", [""] + lista_usuarios_edit)
            if user_selecionado != "":
                dados_atuais = df_profs[df_profs['Usuario'] == user_selecionado].iloc[0]
                with st.form("form_editar_usuario"):
                    edit_nome = st.text_input("Alterar Nome do Professor", value=dados_atuais['Professor'])
                    edit_login = st.text_input("Alterar Login (Usuário)", value=dados_atuais['Usuario'])
                    todas_turmas_disp = sorted(df_alunos['Turma'].unique().astype(str))
                    turmas_atuais = str(dados_atuais.get('Turmas', "")).split(", ") if dados_atuais.get('Turmas') else []
                    edit_turmas = st.multiselect("Alterar Turmas", options=todas_turmas_disp, default=[t for t in turmas_atuais if t in todas_turmas_disp])
                    if not df_discs.empty:
                        disciplina_opcoes = sorted(list(set(df_discs['Disciplina'].unique().astype(str).tolist() + ["SOE"])))
                    else:
                        disciplina_opcoes = ["Artes", "Educação Física", "Inglês", "Espanhol", "Ensino Religioso", "Projeto de Vida", "SOE"]
                    disciplinas_atuais = str(dados_atuais.get('Disciplinas', "")).split(", ") if dados_atuais.get('Disciplinas') else []
                    edit_disciplinas = st.multiselect("Alterar Disciplinas", options=disciplina_opcoes, default=[d for d in disciplinas_atuais if d in disciplina_opcoes])
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
                            msg_placeholder_edit = st.empty()
                            msg_placeholder_edit.success(f"Dados de {user_selecionado} atualizados com sucesso!")
                            st.cache_data.clear()
                            time.sleep(3)
                            msg_placeholder_edit.empty()
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
                            msg_placeholder_del = st.empty()
                            msg_placeholder_del.success(f"Usuário {user_selecionado} excluído com sucesso!")
                            st.cache_data.clear()
                            time.sleep(3)
                            msg_placeholder_del.empty()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao excluir: {e}")

        with tabs[3]:
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

        with tabs[4]:
            st.subheader("Configurar Período de Lançamento")
            with st.form("form_periodo"):
                bim_sel = st.selectbox("Bimestre", ["1º Bimestre", "2º Bimestre", "3º Bimestre", "4º Bimestre"])
                data_inicio = st.date_input("Início do Lançamento", format="DD/MM/YYYY")
                data_fim = st.date_input("Fim do Lançamento", format="DD/MM/YYYY")
                col_btn_per, col_msg_per = st.columns([1, 2])
                with col_btn_per:
                    btn_salvar_per = st.form_submit_button("Salvar Período")
                if btn_salvar_per:
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
                        with col_msg_per:
                            msg_placeholder_per = st.empty()
                            msg_placeholder_per.success(f"Período do {bim_sel} configurado com sucesso!")
                            st.cache_data.clear()
                            time.sleep(3)
                            msg_placeholder_per.empty()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar período: {e}")
            st.divider()
            st.subheader("Períodos Configurados")
            if not df_periodos.empty:
                st.dataframe(df_periodos, use_container_width=True)
                col_btn_limp, col_msg_limp = st.columns([1, 2])
                with col_btn_limp:
                    btn_limpar_per = st.button("Limpar Todos os Períodos")
                if btn_limpar_per:
                    try:
                        sh = conectar_google_sheets()
                        wks_per = sh.worksheet("Config_Periodos")
                        rows = len(wks_per.get_all_values())
                        if rows > 1:
                            wks_per.delete_rows(2, rows)
                            with col_msg_limp:
                                msg_placeholder_limp = st.empty()
                                msg_placeholder_limp.success("Todos os períodos foram removidos com sucesso!")
                                st.cache_data.clear()
                                time.sleep(3)
                                msg_placeholder_limp.empty()
                            st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")
            else:
                st.info("Nenhum período configurado.")

        # Changed: Use is_master_admin for "Bloqueio Master" tab, and ensure it's specifically 'rodrigo'
        if st.session_state.get('is_master_admin', False) and st.session_state.user_data['Usuario'] == "rodrigo":
            with tabs[5]:
                st.subheader("🛡️ Controle de Bloqueio Master")
                st.markdown("### 📊 Status Atual de Usuários")
                df_status = df_profs[['Professor', 'Usuario', 'Status']].copy()
                df_status['Status'] = df_status['Status'].apply(lambda x: "🔴 BLOQUEADO" if str(x).upper() == "BLOQUEADO" else "🟢 ATIVO")
                st.table(df_status)
                st.divider()
                user_bloqueio = st.selectbox("Selecione o Usuário para Bloquear/Desbloquear", [""] + ["Todos"] + df_profs['Usuario'].tolist())
                if user_bloqueio != "":
                    if user_bloqueio == "Todos":
                        st.warning("⚠️ Você selecionou TODOS os usuários para bloqueio/desbloqueio em massa.")
                        col_b1, col_b2 = st.columns(2)
                        with col_b1:
                            if st.button("🔴 BLOQUEAR TODOS"):
                                try:
                                    sh = conectar_google_sheets()
                                    wks_p = sh.worksheet("Config_Professores")
                                    data_p = wks_p.get_all_values()
                                    for i in range(2, len(data_p) + 1):
                                        wks_p.update_cell(i, 6, "Bloqueado")
                                    st.success("Todos os usuários foram bloqueados.")
                                    st.cache_data.clear()
                                    time.sleep(2)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro: {e}")
                        with col_b2:
                            if st.button("🟢 DESBLOQUEAR TODOS"):
                                try:
                                    sh = conectar_google_sheets()
                                    wks_p = sh.worksheet("Config_Professores")
                                    data_p = wks_p.get_all_values()
                                    for i in range(2, len(data_p) + 1):
                                        wks_p.update_cell(i, 6, "Ativo")
                                    st.success("Todos os usuários foram desbloqueados.")
                                    st.cache_data.clear()
                                    time.sleep(2)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro: {e}")
                    else:
                        dados_bloqueio = df_profs[df_profs['Usuario'] == user_bloqueio].iloc[0]
                        status_atual = str(dados_bloqueio.get("Status", "Ativo"))
                        st.write(f"Status atual de **{user_bloqueio}**: {status_atual}")
                        col_b1, col_b2 = st.columns(2)
                        with col_b1:
                            if st.button(f"🔴 BLOQUEAR {user_bloqueio}"):
                                try:
                                    sh = conectar_google_sheets()
                                    wks_p = sh.worksheet("Config_Professores")
                                    celula = wks_p.find(str(user_bloqueio))
                                    wks_p.update_cell(celula.row, 6, "Bloqueado")
                                    st.success(f"Usuário {user_bloqueio} bloqueado.")
                                    st.cache_data.clear()
                                    time.sleep(2)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro: {e}")
                        with col_b2:
                            if st.button(f"🟢 DESBLOQUEAR {user_bloqueio}"):
                                try:
                                    sh = conectar_google_sheets()
                                    wks_p = sh.worksheet("Config_Professores")
                                    celula = wks_p.find(str(user_bloqueio))
                                    wks_p.update_cell(celula.row, 6, "Ativo")
                                    st.success(f"Usuário {user_bloqueio} desbloqueado.")
                                    st.cache_data.clear()
                                    time.sleep(2)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro: {e}")

    elif pagina_atual == "Agendamento de Equipamentos":
        st.title("📅 Gerenciamento de Equipamentos")
        st.subheader("Escola Diva Lima")
        
        # 1. Identifica o professor logado com segurança
        usuario_logado = st.session_state.user_data['Usuario']
        nome_professor_logado = st.session_state.user_data['Professor']
        st.info(f"👤 **Usuário Conectado:** {nome_professor_logado}")
        
        # Criação das duas abas na interface
        aba_cadastrar, aba_visualizar = st.tabs(["🆕 Realizar Agendamento", "📋 Visualizar Agendamentos"])
        
        # ---------------------------------------------------------------------
        # ABA 1: FORMULÁRIO DE CADASTRO DE AGENDAMENTO
        # ---------------------------------------------------------------------
        with aba_cadastrar:
            st.subheader("🗓️ Realizar Agendamento de Equipamento")
            
            # Trava de Segurança: Apenas ADM MASTER acessa durante a manutenção
            if not st.session_state.get('is_master_admin', False):
                st.info("🛠️ **Sistema em Manutenção Preventiva**\n\nEstamos atualizando a ferramenta de agendamentos para trazer melhorias! O recurso estará liberado para todos os professores em breve. Agradecemos a compreensão.")
            else:
                st.warning("⚡ **Acesso Administrativo Ativo:** Você está visualizando esta aba porque está logado como ADM MASTER durante os testes de atualização.")
                
                # 2. Carrega as turmas vinculadas ao professor logado para evitar componentes vazios
                try:
                    sh = conectar_google_sheets()
                    df_p = pd.DataFrame(sh.worksheet("Config_Professores").get_all_records())
                    
                    # Filtra na tabela onde a coluna Usuario bate com o professor logado
                    dados_prof = df_p[df_p["Usuario"] == usuario_logado]
                    # Como estamos no bloco de 'is_master_admin', sempre mostra todas as turmas
                    df_a = pd.DataFrame(sh.worksheet("Config_Alunos").get_all_records())
                    if "Turma" in df_a.columns:
                        turmas_disponiveis = sorted(df_a["Turma"].dropna().unique().tolist())
                    else:
                        turmas_disponiveis = ["Regular A", "Regular B"] # Fallback
                except Exception as e:
                    st.error(f"Erro ao carregar turmas: {e}")
                    turmas_disponiveis = ["Erro ao carregar turmas"]

                if not turmas_disponiveis or turmas_disponiveis == ["Erro ao carregar turmas"]:
                    st.warning("⚠️ Não foi possível carregar as turmas. Por favor, verifique a configuração ou tente novamente.")
                else:
                    # Componentes visuais organizados
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        turma_selecionada = st.selectbox("Selecione a Turma:", turmas_disponiveis, key="agend_turma")
                        
                        # Novo campo para selecionar o período logo abaixo da turma
                        periodo_selecionado = st.selectbox("Selecione o Período:", ["Matutino", "Vespertino"], key="agend_periodo")
                        
                        # Lista de equipamentos com a Caixa de som incluída
                        equipamentos_disponiveis = ["Tablets (Maleta)", "TV", "Datashow", "Notebook", "Caixa de som"]
                        equipamento_selecionado = st.selectbox("Selecione o Equipamento:", equipamentos_disponiveis, key="agend_equip")
                        
                        # Verificação dos Tablets alterada para menu de seleção (selectbox) de 1 a 30
                        if "Tablets" in equipamento_selecionado:
                            opcoes_quantidade = list(range(1, 31))  # Cria a lista de 1 a 30
                            quantidade_tablets = st.selectbox(
                                "Selecione a quantidade de Tablets (1 a 30)", 
                                options=opcoes_quantidade,
                                index=0,  # Começa marcado no número 1
                                key="agend_qtd_tablets"
                            )
                            equipamento = f"Tablets (Maleta) ({quantidade_tablets} unidades)"
                        else:
                            equipamento = equipamento_selecionado
                        
                        # Filtra os horários disponíveis com base no período selecionado
                        if periodo_selecionado == "Matutino":
                            tempos_disponiveis = [
                                "1º Tempo (Matutino)", "2º Tempo (Matutino)", 
                                "3º Tempo (Matutino)", "4º Tempo (Matutino)"
                            ]
                        else: # Vespertino
                            tempos_disponiveis = [
                                "1º Tempo (Vespertino)", "2º Tempo (Vespertino)", 
                                "3º Tempo (Vespertino)", "4º Tempo (Vespertino)"
                            ]
                        tempo_aula = st.selectbox("Tempo de Aula:", tempos_disponiveis, key="agend_tempo")
                        
                    with col2:
                        # Data de Registro automática capturada do Relógio do Sistema Operacional
                        data_registro = datetime.now(fuso_roraima).strftime("%d/%m/%Y")
                        st.text_input("Data de Registro (Hoje):", value=data_registro, disabled=True, key="agend_reg")
                        
                        # Data de Uso usando o seletor de calendário nativo do Streamlit
                        data_uso = st.date_input("Data de Uso do Equipamento:", value=data_atual, format="DD/MM/YYYY", key="agend_uso")
                        data_uso_formatada = data_uso.strftime("%d/%m/%Y")

                    # Novo campo para o professor digitar o objetivo ou observações
                    observacoes = st.text_area("Objetivo / Observações sobre o agendamento", placeholder="Ex: Aula prática sobre o conteúdo X / Uso dos tablets para pesquisa em grupo...")

                    st.markdown("---")
                    
                    # Botão para processar e salvar no banco de dados do Sheets
                    if st.button("💾 Confirmar Agendamento do Equipamento", use_container_width=True, key="btn_confirmar_agendamento"):
                        try:
                            sh = conectar_google_sheets()
                            
                            # Tenta acessar ou cria a aba de agendamentos caso ela não exista na planilha
                            try:
                                wks_a = sh.worksheet("Config_Agendamentos")
                            except:
                                wks_a = sh.add_worksheet(title="Config_Agendamentos", rows="1000", cols="7") # Changed cols to 7
                                wks_a.append_row(["Professor", "Turma", "Equipamento", "Data Registro", "Data Uso", "Tempo", "Observacoes"]) # Added "Observacoes"
                            
                            # Verifica duplicidade (Evita conflito de agendamento do mesmo equipamento no mesmo dia/tempo)
                            dados_agendados = wks_a.get_all_records()
                            conflito = False
                            
                            if dados_agendados:
                                df_agendados = pd.DataFrame(dados_agendados)
                                # Verifica se o mesmo equipamento já está reservado no mesmo dia e tempo
                                filtro_conflito = df_agendados[
                                    (df_agendados["Equipamento"] == equipamento) & 
                                    (df_agendados["Data Uso"] == data_uso_formatada) & 
                                    (df_agendados["Tempo"] == tempo_aula)
                                ]
                                if not filtro_conflito.empty:
                                    conflito = True
                            
                            if conflito:
                                st.error(f"❌ Não é possível agendar! O equipamento '{equipamento}' já está reservado para o dia {data_uso_formatada} no {tempo_aula}.")
                            else:
                                # Registra a nova linha se estiver livre
                                wks_a.append_row([
                                    str(nome_professor_logado),
                                    str(turma_selecionada),
                                    str(equipamento),
                                    str(data_registro),
                                    str(data_uso_formatada),
                                    str(tempo_aula),
                                    str(observacoes)
                                ])
                                st.success(f"✅ Agendamento de {equipamento} realizado com sucesso!")
                                st.cache_data.clear()
                                time.sleep(1.5)
                                st.rerun()
                                
                        except Exception as e:
                            st.error(f"Erro ao salvar os dados na planilha: {e}")

        # ---------------------------------------------------------------------
        # ABA 2: TABELA DE VISUALIZAÇÃO E GERENCIAMENTO (ADM)
        # ---------------------------------------------------------------------
        with aba_visualizar:
            st.markdown("### 📋 Escala de Uso de Equipamentos")
            st.write("Consulte e gerencie abaixo a lista completa de agendamentos realizados:")
            
            try:
                sh = conectar_google_sheets()
                wks_a = sh.worksheet("Config_Agendamentos")
                dados_tabela = wks_a.get_all_records()

                if dados_tabela:
                    df_tabela = pd.DataFrame(dados_tabela)
                    
                    # Cria um índice temporário para sabermos exatamente qual linha alterar/deletar no Sheets
                    # No gspread, a primeira linha de dados após o cabeçalho é a linha 2
                    df_tabela["linha_sheets"] = range(2, len(df_tabela) + 2)
                    
                    colunas_ordenadas = ["Data Uso", "Tempo", "Equipamento", "Turma", "Professor", "Data Registro", "Observacoes", "linha_sheets"] # Added "Observacoes"
                    if all(col in df_tabela.columns for col in colunas_ordenadas):
                        df_exibicao = df_tabela[colunas_ordenadas]
                    else:
                        df_exibicao = df_tabela.copy()
                    
                    # Filtro por equipamento
                    filtro_equip = st.multiselect("Filtrar por Equipamento:", options=["Tablets (Maleta)", "TV", "Datashow", "Notebook", "Caixa de som"], default=[], key="adm_filtro_equip")
                    if filtro_equip:
                        df_exibicao = df_exibicao[df_exibicao["Equipamento"].isin(filtro_equip)]

                    # Exibe a tabela sem mostrar a coluna de controle interno 'linha_sheets' para o usuário
                    st.dataframe(
                        df_exibicao.drop(columns=["linha_sheets"], errors="ignore"), 
                        use_container_width=True, 
                        hide_index=True
                    )
                    
                    st.markdown("---")
                    
                    # --- ÁREA EXCLUSIVA DE GERENCIAMENTO / ADM ---
                    # Changed: Use is_master_admin for admin check
                    is_admin = st.session_state.get('is_master_admin', False)

                    if is_admin:
                        st.subheader("🛠️ Painel de Controle do Administrador")
                        
                        # Criamos uma lista de opções legíveis para selecionar qual agendamento manipular
                        opcoes_selecao = []
                        for idx, row in df_exibicao.iterrows():
                            # Embed linha_sheets directly into the option string
                            opcoes_selecao.append(f"{row['linha_sheets']} - {row['Equipamento']} - {row['Turma']} ({row['Data Uso']} no {row['Tempo']})")
                        
                        if opcoes_selecao: # Only show selectbox if there are options
                            agend_selecionado_texto = st.selectbox("Selecione um agendamento para Modificar ou Excluir:", opcoes_selecao)
                            
                            # Extract linha_sheets_alvo directly from the selected string
                            linha_sheets_alvo = int(agend_selecionado_texto.split(' - ')[0])
                            
                            # Find the corresponding row in df_exibicao using linha_sheets
                            selected_row_data = df_exibicao[df_exibicao['linha_sheets'] == linha_sheets_alvo].iloc[0]
                            
                            col_adm1, col_adm2, col_adm3 = st.columns(3)
                            
                            # 1. BOTAO EXCLUIR SELECIONADO
                            with col_adm1:
                                if st.button("🗑️ Excluir Selecionado", use_container_width=True, type="secondary"):
                                    try:
                                        # Exclui a linha específica no Google Sheets
                                        wks_a.delete_rows(linha_sheets_alvo)
                                        st.success("✅ Agendamento excluído com sucesso!")
                                        st.cache_data.clear()
                                        time.sleep(1.5)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro ao excluir linha: {e}")
                            
                            # 2. BOTAO EDITAR SELECIONADO
                            with col_adm2:
                                expander_editar = st.expander("📝 Editar Selecionado")
                                with expander_editar:
                                    dado_antigo = selected_row_data # Use selected_row_data
                                    
                                    # Updated options for editing equipment
                                    equipamentos_edit_opcoes = ["Tablets (Maleta)", "TV", "Datashow", "Notebook", "Caixa de som"]
                                    
                                    # Determine initial index for selectbox
                                    try:
                                        initial_equip_index = next(i for i, opt in enumerate(equipamentos_edit_opcoes) if opt in dado_antigo["Equipamento"])
                                    except StopIteration:
                                        initial_equip_index = 0 # Default to first option if not found
                                        
                                    novo_equip_raw = st.selectbox("Novo Equipamento:", equipamentos_edit_opcoes, index=initial_equip_index, key="ed_eq")
                                    
                                    novo_equip_final = novo_equip_raw
                                    if "Tablets" in novo_equip_raw:
                                        # Extract current quantity if it exists in the string, otherwise default to 1
                                        import re
                                        match = re.search(r'\((\d+)\sunidades\)', dado_antigo["Equipamento"])
                                        current_qty = int(match.group(1)) if match else 1
                                        
                                        edit_quantidade_tablets = st.number_input(
                                            "Nova quantidade de Tablets (1 a 30)",
                                            min_value=1,
                                            max_value=30,
                                            value=current_qty,
                                            step=1,
                                            key="ed_qtd_tablets"
                                        )
                                        novo_equip_final = f"Tablets (Maleta) ({edit_quantidade_tablets} unidades)"
                                    
                                    novo_tempo = st.selectbox("Novo Tempo:", ["1º Tempo (Matutino)", "2º Tempo (Matutino)", "3º Tempo (Matutino)", "4º Tempo (Matutino)", "5º Tempo (Matutino)", "1º Tempo (Vespertino)", "2º Tempo (Vespertino)", "3º Tempo (Vespertino)", "4º Tempo (Vespertino)", "5º Tempo (Vespertino)"], index=["1º Tempo (Matutino)", "2º Tempo (Matutino)", "3º Tempo (Matutino)", "4º Tempo (Matutino)", "5º Tempo (Matutino)", "1º Tempo (Vespertino)", "2º Tempo (Vespertino)", "3º Tempo (Vespertino)", "4º Tempo (Vespertino)", "5º Tempo (Vespertino)"].index(dado_antigo["Tempo"]), key="ed_tp")
                                    nova_observacao = st.text_area("Novas Observações:", value=dado_antigo["Observacoes"], key="ed_obs") # Added new text_area for editing
                                    
                                    if st.button("💾 Salvar Alterações", use_container_width=True):
                                        try:
                                            # Atualiza as células correspondentes (Colunas: 3=Equipamento, 6=Tempo, 7=Observacoes)
                                            wks_a.update_cell(linha_sheets_alvo, 3, str(novo_equip_final))
                                            wks_a.update_cell(linha_sheets_alvo, 6, str(novo_tempo))
                                            wks_a.update_cell(linha_sheets_alvo, 7, str(nova_observacao)) # Updated Observacoes
                                            st.success("✅ Agendamento atualizado!")
                                            st.cache_data.clear()
                                            time.sleep(1.5)
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Erro ao editar: {e}")
                            
                            # 3. BOTAO EXCLUIR TUDO (PERIGO)
                            with col_adm3:
                                confirmar_deletar_tudo = st.checkbox("⚠️ Liberar botão 'Excluir Todos'")
                                if confirmar_deletar_tudo:
                                    if st.button("🚨 EXCLUIR TODOS OS AGENDAMENTOS", use_container_width=True, type="primary"):
                                        try:
                                            # Limpa todas as linhas mantendo apenas o cabeçalho (linha 1)
                                            wks_a.resize(rows=1)
                                            wks_a.resize(rows=1000)
                                            st.success("💥 Todos os agendamentos foram limpos do banco de dados!")
                                            st.cache_data.clear()
                                            time.sleep(1.5)
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Erro ao limpar tabela: {e}")
                        else:
                            st.info("Nenhum agendamento corresponde ao filtro aplicado ou não há agendamentos para gerenciar.")
                    else:
                        st.caption("ℹ️ Recursos de edição e exclusão de reservas estão disponíveis apenas para administradores.")
                else:
                    st.info("ℹ️ Nenhum agendamento foi registrado até o momento.")
                    
            except Exception as e:
                st.error(f"Erro ao carregar o painel de gerenciamento: {e}")

    elif pagina_atual == "Cadastro":
        st.error("Acesso restrito.")
        st.session_state.pagina = "Registro"
        st.rerun()
