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
                        st.info("Usuários SOE não possuem permissão para editar ou excluir registros.")
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
        st.title("🚨 Registro de Ocorrências")
        tab_oc1, tab_oc2 = st.tabs(["Nova Ocorrência", "Visualizar Ocorrências"])
        
        with tab_oc1:
            if is_soe:
                st.info("Você está logado como SOE. Este módulo é apenas para visualização.")
            
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
                    bimestre_ativo = st.selectbox("📅 Selecione o Bimestre Vigente:", bimestres_disponiveis, key="bim_oc")
                else:
                    bimestre_ativo = bimestres_disponiveis[0]
                    st.info(f"📅 Período de lançamento aberto: **{bimestre_ativo}**")
            
            if st.session_state.get('is_master_admin', False) or is_soe:
                todas_turmas = sorted(df_alunos['Turma'].unique().astype(str))
            else:
                turmas_vinc = str(st.session_state.user_data.get('Turmas', "")).split(", ")
                todas_turmas = sorted([t.strip() for t in turmas_vinc if t.strip()])
                
            col_oc1, col_oc2 = st.columns([1, 4])
            with col_oc1:
                turma_sel_oc = st.selectbox("1. Selecione a Turma", todas_turmas, key="turma_oc")
            with col_oc2:
                alunos_da_turma_oc = df_alunos[df_alunos['Turma'].astype(str) == turma_sel_oc]['Nome_Aluno'].tolist()
                aluno_sel_oc = st.selectbox("2. Selecione o Aluno", sorted(alunos_da_turma_oc), key="aluno_oc")
                
            with st.form("form_ocorrencia", clear_on_submit=True):
                opcoes_motivos = [
                    "Agressão Física", "Agressão Verbal / Ofensa", "Uso de Celular em Sala",
                    "Indisciplina Grave", "Desrespeito ao Professor/Funcionário", "Vandalismo / Dano ao Patrimônio",
                    "Falta de Material Recorrente", "Recusa a Realizar Atividades", "Outros (Especificar nas observações)"
                ]
                motivos_selecionados = st.multiselect("Motivos da Ocorrência", options=opcoes_motivos)
                obs_oc = st.text_area("Detalhamento da Ocorrência (Obrigatório)")
                
                col_salvar_oc, col_mensagem_oc = st.columns([1, 2])
                with col_salvar_oc:
                    btn_salvar_oc = st.form_submit_button("REGISTRAR OCORRÊNCIA", disabled=(bimestre_ativo == "Bloqueado" or is_soe))
                    
            if btn_salvar_oc:
                if is_soe:
                    st.error("Usuários SOE não possuem permissão para realizar registros.")
                elif not motivos_selecionados:
                    with col_mensagem_oc:
                        st.error("Por favor, selecione pelo menos um motivo para a ocorrência.")
                elif not obs_oc.strip():
                    with col_mensagem_oc:
                        st.error("Por favor, faça o detalhamento obrigatório da ocorrência.")
                else:
                    try:
                        sh = conectar_google_sheets()
                        wks = sh.worksheet("Registros_Ocorrencias")
                        
                        motivos_formatados = "OCORRÊNCIA: " + ", ".join(motivos_selecionados)
                        
                        nova_linha_oc = [
                            datetime.now(fuso_roraima).strftime("%d/%m/%Y %H:%M:%S"),
                            prof_nome,
                            turma_sel_oc,
                            aluno_sel_oc,
                            "Ocorrência Disciplinar",
                            bimestre_ativo,
                            motivos_formatados,
                            obs_oc
                        ]
                        
                        wks.append_row(nova_linha_oc)
                        with col_mensagem_oc:
                            st.success("✅ Ocorrência registrada com sucesso!")
                            time.sleep(1.5)
                            st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar ocorrência: {e}")
                        
        with tab_oc2:
            st.subheader("📋 Painel de Consulta de Ocorrências")
            try:
                sh = conectar_google_sheets()
                wks_reg = sh.worksheet("Registros_Ocorrencias")
                dados_brutos = wks_reg.get_all_values()
                
                if len(dados_brutos) > 1:
                    df_all = pd.DataFrame(dados_brutos[1:], columns=dados_brutos[0])
                    df_oc = df_all[df_all[df_all.columns[6]].astype(str).str.contains("OCORRÊNCIA:", na=False)].copy()
                    
                    if not df_oc.empty:
                        colunas_oc = df_oc.columns.tolist()
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            lista_turmas_oc = ["Todas"] + sorted(df_oc[colunas_oc[2]].unique().astype(str).tolist())
                            t_filtro_oc = st.selectbox("Filtrar por Turma", lista_turmas_oc, key="f_t_oc")
                        with c2:
                            lista_alunos_oc = ["Todos"] + sorted(df_oc[df_oc[colunas_oc[2]].astype(str) == t_filtro_oc][colunas_oc[3]].unique().astype(str).tolist()) if t_filtro_oc != "Todas" else ["Todos"] + sorted(df_oc[colunas_oc[3]].unique().astype(str).tolist())
                            a_filtro_oc = st.selectbox("Filtrar por Aluno", lista_alunos_oc, key="f_a_oc")
                            
                        df_oc_filtrado = df_oc.copy()
                        if t_filtro_oc != "Todas":
                            df_oc_filtrado = df_oc_filtrado[df_oc_filtrado[colunas_oc[2]].astype(str) == t_filtro_oc]
                        if a_filtro_oc != "Todos":
                            df_oc_filtrado = df_oc_filtrado[df_oc_filtrado[colunas_oc[3]].astype(str) == a_filtro_oc]
                            
                        df_oc_exibicao = df_oc_filtrado.rename(columns={
                            colunas_oc[0]: "Data/Hora",
                            colunas_oc[1]: "Professor",
                            colunas_oc[2]: "Turma",
                            colunas_oc[3]: "Aluno",
                            colunas_oc[5]: "Bimestre",
                            colunas_oc[6]: "Motivos",
                            colunas_oc[7]: "Detalhamento"
                        })
                        
                        st.dataframe(df_oc_exibicao[["Data/Hora", "Turma", "Aluno", "Professor", "Bimestre", "Motivos", "Detalhamento"]], use_container_width=True, hide_index=True)
                    else:
                        st.info("ℹ️ Nenhuma ocorrência registrada até o momento.")
                else:
                    st.info("ℹ️ Nenhuma ocorrência encontrada na planilha.")
            except Exception as e:
                st.error(f"Erro ao carregar painel de ocorrências: {e}")

    elif pagina_atual == "Agendamento de Equipamentos":
        st.title("📅 Agendamento de Equipamentos")
        st.markdown("---")
        
        # Bloco limpo, seguro e pronto para receber a nova estrutura na aba isolada
        st.info("🔄 Este módulo de agendamento está pronto para ser reestruturado de forma totalmente isolada. Aguardando a definição do novo layout.")

    elif pagina_atual == "Cadastro":
        st.error("Acesso restrito.")
        st.session_state.pagina = "Registro"
        st.rerun()

    elif pagina_atual == "Segurança":
        st.title("🔒 Alterar Senha de Acesso")
        with st.form("form_senha"):
            senha_atual = st.text_input("Senha Atual", type="password")
            nova_senha = st.text_input("Nova Senha", type="password")
            confirma_senha = st.text_input("Confirme a Nova Senha", type="password")
            btn_senha = st.form_submit_button("ATUALIZAR SENHA")
            
        if btn_senha:
            if not senha_atual or not nova_senha or not confirma_senha:
                st.error("Todos os campos de senha são obrigatórios.")
            elif nova_senha != confirma_senha:
                st.error("A nova senha e a confirmação não coincidem.")
            elif senha_atual != str(st.session_state.user_data['Senha']).strip():
                st.error("A senha atual informada está incorreta.")
            else:
                try:
                    sh = conectar_google_sheets()
                    wks_p = sh.worksheet("Config_Professores")
                    celula = wks_p.find(str(st.session_state.user_data['Usuario']))
                    wks_p.update_cell(celula.row, 3, str(nova_senha).strip())
                    st.success("Senha atualizada com sucesso! Por segurança, faça login novamente.")
                    st.session_state.user_data['Senha'] = str(nova_senha).strip()
                    st.cache_data.clear()
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao atualizar senha no banco: {e}")
