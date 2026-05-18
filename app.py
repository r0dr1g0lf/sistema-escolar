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
        df_age = pd.DataFrame(sh.worksheet("Agendamentos").get_all_records())
    except Exception:
        df_age = pd.DataFrame(columns=["ID", "Professor", "Recurso", "Data", "Turno", "Horário", "Turma", "Disciplina", "Data Registro"])
        
    return df_p, df_a, df_age

def gerar_id_unico(df_age):
    if df_age.empty:
        return 1
    if "ID" in df_age.columns:
        try:
            ids_validos = pd.to_numeric(df_age["ID"], errors='coerce').dropna().astype(int)
            if not ids_validos.empty:
                return int(ids_validos.max() + 1)
        except Exception:
            pass
    return len(df_age) + 1

def formatar_data_br(data_obj):
    if isinstance(data_obj, str):
        try:
            data_obj = datetime.strptime(data_obj, "%Y-%m-%d").date()
        except Exception:
            return data_obj
    return data_obj.strftime("%d/%m/%Y")

def main():
    st.set_page_config(page_title="Sistema de Gestão Escolar", page_icon="🏫", layout="wide")
    
    if "usuario" not in st.session_state:
        st.session_state.usuario = None
    if "perfil" not in st.session_state:
        st.session_state.perfil = None
    if "pagina" not in st.session_state:
        st.session_state.pagina = "Login"
        
    try:
        df_p, df_a, df_age = carregar_dados()
    except Exception as e:
        st.error(f"Erro crítico ao conectar com o banco de dados: {e}")
        st.info("Verifique suas credenciais e conexão com a internet.")
        st.stop()
        
    pagina_atual = st.session_state.pagina
    
    if pagina_atual == "Login":
        st.markdown("<h2 style='text-align: center;'>🏫 Sistema União - Escola Diva Lima</h2>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align: center; color: gray;'>Acesso ao Sistema</h4>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("form_login"):
                usuario_input = st.text_input("Usuário / Matrícula").strip()
                senha_input = st.text_input("Senha", type="password").strip()
                botao_entrar = st.form_submit_with_button("Entrar", use_container_width=True, type="primary")
                
                if botao_entrar:
                    if usuario_input == "admin" and senha_input == "admin123":
                        st.session_state.usuario = "Administrador"
                        st.session_state.perfil = "Admin"
                        st.session_state.pagina = "Registro"
                        st.success("Login efetuado com sucesso como Administrador!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        usuario_encontrado = False
                        if not df_p.empty and "Nome" in df_p.columns and "Senha" in df_p.columns:
                            linha_p = df_p[(df_p["Nome"].astype(str) == usuario_input) & (df_p["Senha"].astype(str) == senha_input)]
                            if not linha_p.empty:
                                st.session_state.usuario = usuario_input
                                st.session_state.perfil = "Professor"
                                st.session_state.pagina = "Registro"
                                usuario_encontrado = True
                                st.success(f"Bem-vindo(a), Prof. {usuario_input}!")
                                time.sleep(1)
                                st.rerun()
                                
                        if not usuario_encontrado:
                            st.error("Usuário ou senha incorretos. Tente novamente.")
                            
    elif pagina_atual in ["Registro", "Agendamentos", "Relatórios", "Configurações", "Cadastro"]:
        with st.sidebar:
            st.markdown(f"### 👤 {st.session_state.usuario}")
            st.caption(f"Nível de Acesso: **{st.session_state.perfil}**")
            st.markdown("---")
            
            if st.button("📝 Notas e Frequência", use_container_width=True, type="secondary" if pagina_atual != "Registro" else "primary"):
                st.session_state.pagina = "Registro"
                st.rerun()
                
            if st.button("📅 Agendamento de Recursos", use_container_width=True, type="secondary" if pagina_atual != "Agendamentos" else "primary"):
                st.session_state.pagina = "Agendamentos"
                st.rerun()
                
            if st.button("📊 Relatórios Disponíveis", use_container_width=True, type="secondary" if pagina_atual != "Relatórios" else "primary"):
                st.session_state.pagina = "Relatórios"
                st.rerun()
                
            if st.session_state.perfil == "Admin":
                if st.button("⚙️ Configurações Gerais", use_container_width=True, type="secondary" if pagina_atual != "Configurações" else "primary"):
                    st.session_state.pagina = "Configurações"
                    st.rerun()
                    
            st.markdown("---")
            if st.button("🚪 Sair do Sistema", use_container_width=True):
                st.session_state.usuario = None
                st.session_state.perfil = None
                st.session_state.pagina = "Login"
                st.rerun()
                
        if pagina_atual == "Registro":
            st.title("📝 Notas, Frequência e Conteúdos Curriculares")
            st.write(f"Data de operação: {formatar_data_br(data_atual)}")
            
            if df_p.empty:
                st.warning("Não há professores configurados no sistema. Vá em Configurações.")
                st.stop()
                
            if st.session_state.perfil == "Admin":
                professores_lista = sorted(list(df_p["Nome"].unique()))
                prof_selecionado = st.selectbox("Selecione o Professor para lançamentos:", professores_lista)
            else:
                prof_selecionado = st.session_state.usuario
                
            dados_prof = df_p[df_p["Nome"] == prof_selecionado]
            
            if dados_prof.empty:
                st.error("Erro ao carregar atribuições do professor.")
                st.stop()
                
            turmas_vinculadas = []
            for col in ["Turma 1", "Turma 2", "Turma 3", "Turma 4", "Turma 5"]:
                if col in dados_prof.columns:
                    val = str(dados_prof.iloc[0][col]).strip()
                    if val and val != "nan" and val != "":
                        turmas_vinculadas.append(val)
                        
            disciplinas_vinculadas = []
            for col in ["Disciplina 1", "Disciplina 2", "Disciplina 3", "Disciplina 4", "Disciplina 5"]:
                if col in dados_prof.columns:
                    val = str(dados_prof.iloc[0][col]).strip()
                    if val and val != "nan" and val != "":
                        disciplinas_vinculadas.append(val)
                        
            turmas_vinculadas = sorted(list(set(turmas_vinculadas)))
            disciplinas_vinculadas = sorted(list(set(disciplinas_vinculadas)))
            
            if not turmas_vinculadas:
                st.warning("Este professor não possui turmas vinculadas em seu cadastro.")
                st.stop()
            if not disciplinas_vinculadas:
                st.warning("Este professor não possui disciplinas vinculadas em seu cadastro.")
                st.stop()
                
            c1, c2 = st.columns(2)
            with c1:
                turma_sel = st.selectbox("Selecione a Turma:", turmas_vinculadas)
            with c2:
                dis_sel = st.selectbox("Selecione a Disciplina:", disciplinas_vinculadas)
                
            aba_notas, aba_freq, aba_cont = st.tabs(["📊 Lançamento de Notas", "📅 Controle de Frequência", "📖 Conteúdo Ministrado"])
            
            sh = conectar_google_sheets()
            nome_aba_notas = f"Notas_{turma_sel}_{dis_sel}".replace("/", "_").replace(" ", "_")
            
            try:
                wks_n = sh.worksheet(nome_aba_notas)
                dados_notas_brutos = wks_n.get_all_records()
                df_notas_atual = pd.DataFrame(dados_notas_brutos)
            except Exception:
                df_notas_atual = pd.DataFrame()
                
            alunos_turma = []
            if not df_a.empty and "Nome Aluno" in df_a.columns and "Turma" in df_a.columns:
                df_filtrado_a = df_a[df_a["Turma"].astype(str) == str(turma_sel)]
                alunos_turma = sorted(list(df_filtrado_a["Nome Aluno"].unique()))
                
            if not alunos_turma:
                st.info(f"Nenhum aluno cadastrado para a turma {turma_sel} na aba Config_Alunos.")
                st.stop()
                
            with aba_notas:
                st.subheader(f"Avaliações - {turma_sel} - {dis_sel}")
                
                if df_notas_atual.empty:
                    df_grid = pd.DataFrame({"Aluno": alunos_turma})
                    df_grid["Nota 1 (Bim 1)"] = 0.0
                    df_grid["Nota 2 (Bim 1)"] = 0.0
                    df_grid["Nota 3 (Bim 1)"] = 0.0
                    df_grid["Recuperação 1"] = ""
                    df_grid["Nota 1 (Bim 2)"] = 0.0
                    df_grid["Nota 2 (Bim 2)"] = 0.0
                    df_grid["Nota 3 (Bim 2)"] = 0.0
                    df_grid["Recuperação 2"] = ""
                else:
                    df_grid = pd.DataFrame({"Aluno": alunos_turma})
                    colunas_padrao = ["Nota 1 (Bim 1)", "Nota 2 (Bim 1)", "Nota 3 (Bim 1)", "Recuperação 1", "Nota 1 (Bim 2)", "Nota 2 (Bim 2)", "Nota 3 (Bim 2)", "Recuperação 2"]
                    for c in colunas_padrao:
                        if c in df_notas_atual.columns:
                            mapeamento = dict(zip(df_notas_atual["Aluno"].astype(str), df_notas_atual[c]))
                            df_grid[c] = df_grid["Aluno"].astype(str).map(mapeamento)
                        else:
                            df_grid[c] = "" if "Recuperação" in c else 0.0
                            
                for c in df_grid.columns:
                    if c != "Aluno" and "Recuperação" not in c:
                        df_grid[c] = pd.to_numeric(df_grid[c], errors='coerce').fillna(0.0)
                        
                st.caption("💡 Clique duas vezes na célula para editar os valores de nota e recuperação dos alunos abaixo:")
                df_editado_notas = st.data_editor(df_grid, use_container_width=True, hide_index=True, key="editor_notas_sistema")
                
                if st.button("💾 Salvar Planilha de Notas", type="primary"):
                    try:
                        try:
                            wks_n = sh.worksheet(nome_aba_notas)
                            sh.del_worksheet(wks_n)
                        except Exception:
                            pass
                            
                        wks_n = sh.add_worksheet(title=nome_aba_notas, rows=len(df_editado_notas)+10, cols=15)
                        df_salvar = df_editado_notas.copy()
                        wks_n.update([df_salvar.columns.values.tolist()] + df_salvar.fillna("").values.tolist())
                        st.success(f"🎉 Notas salvas com sucesso para {turma_sel} - {dis_sel}!")
                        st.cache_data.clear()
                    except Exception as ex:
                        st.error(f"Erro ao salvar na planilha de Notas: {ex}")
                        
            with aba_freq:
                st.subheader(f"Diário de Frequência - {turma_sel} - {dis_sel}")
                
                nome_aba_freq = f"Freq_{turma_sel}_{dis_sel}".replace("/", "_").replace(" ", "_")
                try:
                    wks_f = sh.worksheet(nome_aba_freq)
                    df_freq_atual = pd.DataFrame(wks_f.get_all_records())
                except Exception:
                    df_freq_atual = pd.DataFrame()
                    
                data_chamada = st.date_input("Data da Chamada/Frequência:", data_atual, key="data_chamada_id")
                data_chamada_str = data_chamada.strftime("%d/%m/%Y")
                
                st.write(f"Registrando faltas para o dia: **{data_chamada_str}**")
                
                df_chamada_dia = pd.DataFrame({"Aluno": alunos_turma})
                
                lista_faltas_existentes = []
                if not df_freq_atual.empty and "Aluno" in df_freq_atual.columns and data_chamada_str in df_freq_atual.columns:
                    df_freq_atual[data_chamada_str] = df_freq_atual[data_chamada_str].astype(str).str.upper()
                    for idx, row in df_freq_atual.iterrows():
                        if str(row[data_chamada_str]).strip() in ["F", "FALTA"]:
                            lista_faltas_existentes.append(str(row["Aluno"]).strip())
                            
                df_chamada_dia["Presença"] = df_chamada_dia["Aluno"].apply(lambda x: "🔴 FALTA" if str(x).strip() in lista_faltas_existentes else "🟢 PRESENTE")
                
                df_editado_freq = st.data_editor(
                    df_chamada_dia,
                    column_config={
                        "Presença": st.column_config.SelectboxColumn(
                            "Status de Presença",
                            help="Selecione se o aluno estava presente ou faltou",
                            width="medium",
                            options=["🟢 PRESENTE", "🔴 FALTA"],
                            required=True,
                        )
                    },
                    use_container_width=True,
                    hide_index=True,
                    key="editor_frequencia_dia"
                )
                
                if st.button("💾 Salvar Chamada do Dia", type="primary"):
                    try:
                        if df_freq_atual.empty:
                            df_nova_freq = pd.DataFrame({"Aluno": alunos_turma})
                            for col_data in [data_chamada_str]:
                                mapa_status = dict(zip(df_editado_freq["Aluno"], df_editado_freq["Presença"]))
                                df_nova_freq[col_data] = df_nova_freq["Aluno"].map(mapa_status).apply(lambda x: "F" if "FALTA" in str(x) else "P")
                        else:
                            df_nova_freq = pd.DataFrame({"Aluno": alunos_turma})
                            colunas_antigas = [c for c in df_freq_atual.columns if c != "Aluno"]
                            for c in colunas_antigas:
                                mapa_antigo = dict(zip(df_freq_atual["Aluno"].astype(str), df_freq_atual[c]))
                                df_nova_freq[c] = df_nova_freq["Aluno"].astype(str).map(mapa_antigo).fillna("P")
                                
                            mapa_status = dict(zip(df_editado_freq["Aluno"], df_editado_freq["Presença"]))
                            df_nova_freq[data_chamada_str] = df_nova_freq["Aluno"].map(mapa_status).apply(lambda x: "F" if "FALTA" in str(x) else "P")
                            
                        try:
                            wks_f = sh.worksheet(nome_aba_freq)
                            sh.del_worksheet(wks_f)
                        except Exception:
                            pass
                            
                        wks_f = sh.add_worksheet(title=nome_aba_freq, rows=len(df_nova_freq)+10, cols=max(20, len(df_nova_freq.columns)+5))
                        wks_f.update([df_nova_freq.columns.values.tolist()] + df_nova_freq.fillna("P").values.tolist())
                        st.success(f"🎉 Diário de frequência salvo com sucesso para o dia {data_chamada_str}!")
                        st.cache_data.clear()
                    except Exception as ex:
                        st.error(f"Erro ao salvar frequência na planilha: {ex}")
                        
            with aba_cont:
                st.subheader(f"Registro de Conteúdo Ministrado - {turma_sel} - {dis_sel}")
                
                nome_aba_cont = f"Cont_{turma_sel}_{dis_sel}".replace("/", "_").replace(" ", "_")
                try:
                    wks_c = sh.worksheet(nome_aba_cont)
                    df_cont_atual = pd.DataFrame(wks_c.get_all_records())
                except Exception:
                    df_cont_atual = pd.DataFrame(columns=["Data", "Aulas", "Conteúdo Selecionado / Descrição Detalhada"])
                    
                with st.form("form_conteudo_novo"):
                    data_cont_input = st.date_input("Data do Conteúdo:", data_atual, key="data_conteudo_key")
                    qtd_aulas = st.number_input("Quantidade de Horas/Aulas:", min_value=1, max_value=10, value=2)
                    texto_conteudo = st.text_area("Descreva o conteúdo curricular que foi trabalhado em sala de aula:", height=100)
                    btn_salvar_cont = st.form_submit_with_button("Gravar Registro de Conteúdo", type="primary")
                    
                    if btn_salvar_cont:
                        if not texto_conteudo.strip():
                            st.error("Por favor, preencha a descrição do conteúdo antes de salvar.")
                        else:
                            try:
                                nova_linha = {
                                    "Data": data_cont_input.strftime("%d/%m/%Y"),
                                    "Aulas": int(qtd_aulas),
                                    "Conteúdo Selecionado / Descrição Detalhada": texto_conteudo.strip()
                                }
                                df_novo_cont = pd.concat([df_cont_atual, pd.DataFrame([nova_linha])], ignore_index=True)
                                
                                try:
                                    wks_c = sh.worksheet(nome_aba_cont)
                                    sh.del_worksheet(wks_c)
                                except Exception:
                                    pass
                                    
                                wks_c = sh.add_worksheet(title=nome_aba_cont, rows=len(df_novo_cont)+15, cols=5)
                                wks_c.update([df_novo_cont.columns.values.tolist()] + df_novo_cont.fillna("").values.tolist())
                                st.success("🎉 Conteúdo curricular registrado e anexado ao diário de classe com sucesso!")
                                st.cache_data.clear()
                                time.sleep(1)
                                st.rerun()
                            except Exception as ex:
                                st.error(f"Erro ao salvar o conteúdo na planilha externa: {ex}")
                                
                if not df_cont_atual.empty:
                    st.markdown("---")
                    st.write("📖 **Histórico de Conteúdos Lançados Neste Bimestre:**")
                    st.dataframe(df_cont_atual, use_container_width=True, hide_index=True)
                    
        elif pagina_atual == "Agendamentos":
            st.title("📅 Reserva e Agendamento de Recursos Pedagógicos")
            
            # --- ADICIONADO: BOTÃO PARA LIMPAR CACHE DIRETAMENTE NA TELA ---
            if st.button("🔄 Atualizar Banco de Dados (Limpar Cache)"):
                st.cache_data.clear()
                st.success("Banco de dados atualizado! Carregando registros mais recentes...")
                time.sleep(1)
                st.rerun()
            st.markdown("---")
            
            lista_recursos = ["Tablets (Maleta)", "TV Retrátil / Smart TV", "DataShow / Projetor", "Notebook Lenovo"]
            turnos_disponiveis = ["Matutino", "Vespertino", "Noturno"]
            horarios_disponiveis = [
                "1º Horário", "2º Horário", "3º Horário", "4º Horário", "5º Horário",
                "1º e 2º Horário", "3º e 4º Horário", "Todos os Horários do Turno"
            ]
            
            aba_fazer_reserva, aba_ver_reservas = st.tabs(["🆕 Realizar Novo Agendamento", "📋 Painel de Controle e Recursos Ocupados"])
            
            with aba_fazer_reserva:
                st.subheader("Formulário de Reserva")
                
                if df_p.empty:
                    st.warning("Não há professores cadastrados no sistema.")
                    st.stop()
                    
                lista_prof_agendamento = sorted(list(df_p["Nome"].unique()))
                
                if st.session_state.perfil == "Admin":
                    prof_da_reserva = st.selectbox("Selecione o Professor solicitante:", lista_prof_agendamento, key="prof_res_admin")
                else:
                    prof_da_reserva = st.session_state.usuario
                    st.info(f"Agendamento vinculado ao seu perfil: **Prof. {prof_da_reserva}**")
                    
                dados_prof_res = df_p[df_p["Nome"] == prof_da_reserva]
                turmas_res_lista = []
                if not dados_prof_res.empty:
                    for col in ["Turma 1", "Turma 2", "Turma 3", "Turma 4", "Turma 5"]:
                        if col in dados_prof_res.columns:
                            val = str(dados_prof_res.iloc[0][col]).strip()
                            if val and val != "nan" and val != "":
                                turmas_res_lista.append(val)
                                
                disciplinas_res_lista = []
                if not dados_prof_res.empty:
                    for col in ["Disciplina 1", "Disciplina 2", "Disciplina 3", "Disciplina 4", "Disciplina 5"]:
                        if col in dados_prof_res.columns:
                            val = str(dados_prof_res.iloc[0][col]).strip()
                            if val and val != "nan" and val != "":
                                disciplinas_res_lista.append(val)
                                
                turmas_res_lista = sorted(list(set(turmas_res_lista)))
                disciplinas_res_lista = sorted(list(set(disciplinas_res_lista)))
                
                if not turmas_res_lista:
                    turmas_res_lista = ["Não Especificada / Geral"]
                if not disciplinas_res_lista:
                    disciplinas_res_lista = ["Geral / Uso Livre"]
                    
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    recurso_sel = st.selectbox("Escolha o Equipamento/Recurso:", lista_recursos)
                    data_reserva_sel = st.date_input("Selecione a Data da Reserva:", data_atual, key="dt_res_pedag")
                    turno_reserva_sel = st.selectbox("Selecione o Turno:", turnos_disponiveis)
                with col_r2:
                    horario_reserva_sel = st.selectbox("Selecione o Horário de Uso:", horarios_disponiveis)
                    turma_reserva_sel = st.selectbox("Selecione a Turma que utilizará:", turmas_res_lista)
                    dis_reserva_sel = st.selectbox("Selecione a Disciplina aplicada:", disciplinas_res_lista)
                    
                if st.button("🚀 Confirmar e Bloquear Recurso", type="primary", use_container_width=True):
                    data_reserva_str = data_reserva_sel.strftime("%Y-%m-%d")
                    
                    conflito = False
                    if not df_age.empty:
                        df_filtrado_conflito = df_age[
                            (df_age["Recurso"].astype(str) == str(recurso_sel)) &
                            (df_age["Data"].astype(str) == str(data_reserva_str)) &
                            (df_age["Turno"].astype(str) == str(turno_reserva_sel))
                        ]
                        
                        for idx, row in df_filtrado_conflito.iterrows():
                            h_existente = str(row["Horário"])
                            if h_existente == "Todos os Horários do Turno" or horario_reserva_sel == "Todos os Horários do Turno":
                                conflito = True
                                break
                            if h_existente == horario_reserva_sel:
                                conflito = True
                                break
                            if ("1º e 2º" in h_existente and "1º Horário" in horario_reserva_sel) or ("1º e 2º" in h_existente and "2º Horário" in horario_reserva_sel):
                                conflito = True
                                break
                            if ("3º e 4º" in h_existente and "3º Horário" in horario_reserva_sel) or ("3º e 4º" in h_existente and "4º Horário" in horario_reserva_sel):
                                conflito = True
                                break
                            if ("1º Horário" in h_existente and "1º e 2º" in horario_reserva_sel) or ("2º Horário" in h_existente and "1º e 2º" in horario_reserva_sel):
                                conflito = True
                                break
                            if ("3º Horário" in h_existente and "3º e 4º" in horario_reserva_sel) or ("4º Horário" in h_existente and "3º e 4º" in horario_reserva_sel):
                                conflito = True
                                break
                                
                    if conflito:
                        st.error(f"❌ Impossível Agendar! O recurso '{recurso_sel}' já está reservado nesta data ({data_reserva_sel.strftime('%d/%m/%Y')}), no turno {turno_reserva_sel} e horário selecionado. Por favor, escolha outro período ou equipamento.")
                    else:
                        try:
                            sh = conectar_google_sheets()
                            try:
                                wks_a = sh.worksheet("Agendamentos")
                            except Exception:
                                wks_a = sh.add_worksheet(title="Agendamentos", rows=1000, cols=10)
                                wks_a.update([["ID", "Professor", "Recurso", "Data", "Turno", "Horário", "Turma", "Disciplina", "Data Registro"]])
                                
                            id_novo = gerar_id_unico(df_age)
                            timestamp_agora = datetime.now(fuso_roraima).strftime("%d/%m/%Y %H:%M:%S")
                            
                            nova_linha_reserva = [
                                str(id_novo),
                                str(prof_da_reserva),
                                str(recurso_sel),
                                str(data_reserva_str),
                                str(turno_reserva_sel),
                                str(horario_reserva_sel),
                                str(turma_reserva_sel),
                                str(dis_reserva_sel),
                                str(timestamp_agora)
                            ]
                            
                            wks_a.append_row(nova_linha_reserva)
                            st.success(f"🎉 Reserva realizada com sucesso! ID do Agendamento: {id_novo}. O equipamento foi bloqueado para seu uso.")
                            st.cache_data.clear()
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Erro ao processar gravação da reserva na planilha: {ex}")
                            
            with aba_ver_reservas:
                st.subheader("Painel de Agendamentos Cadastrados")
                
                try:
                    sh = conectar_google_sheets()
                    wks_a = sh.worksheet("Agendamentos")
                    df_exibir = pd.DataFrame(wks_a.get_all_records())
                    
                    if not df_exibir.empty:
                        df_exibir["ID"] = pd.to_numeric(df_exibir["ID"], errors='coerce').fillna(0).astype(int)
                        
                        def converter_data_para_exibicao(d_str):
                            try:
                                return datetime.strptime(str(d_str).strip(), "%Y-%m-%d").strftime("%d/%m/%Y")
                            except Exception:
                                return d_str
                                
                        df_exibir["Data de Uso"] = df_exibir["Data"].apply(converter_data_para_exibicao)
                        
                        col_f1, col_f2 = st.columns(2)
                        with col_f1:
                            filtro_recurso = st.selectbox("Filtrar Ocupação por Recurso:", ["Todos os Equipamentos"] + lista_recursos)
                        with col_f2:
                            filtro_data_busca = st.date_input("Filtrar por Data Específica (Opcional):", value=None, key="busca_dt_res")
                            
                        df_filtrado_grid = df_exibir.copy()
                        if filtro_recurso != "Todos os Equipamentos":
                            df_filtrado_grid = df_filtrado_grid[df_filtrado_grid["Recurso"].astype(str) == str(filtro_recurso)]
                        if filtro_data_busca is not None:
                            dt_busca_str = filtro_data_busca.strftime("%Y-%m-%d")
                            df_filtrado_grid = df_filtrado_grid[df_filtrado_grid["Data"].astype(str) == str(dt_busca_str)]
                            
                        if not df_filtrado_grid.empty:
                            ordem_colunas = ["ID", "Professor", "Recurso", "Data de Uso", "Turno", "Horário", "Turma", "Disciplina", "Data Registro"]
                            df_filtrado_grid = df_filtrado_grid[[c for c in ordem_colunas if c in df_filtrado_grid.columns]]
                            
                            st.dataframe(df_filtrado_grid.sort_values(by="ID", ascending=False), use_container_width=True, hide_index=True)
                            
                            if st.session_state.perfil == "Admin":
                                st.markdown("---")
                                st.subheader("🗑️ Cancelamento de Reservas (Área Técnica)")
                                
                                ids_cancelamento = sorted(list(df_filtrado_grid["ID"].unique()))
                                id_cancelar_sel = st.selectbox("Selecione o código (ID) do agendamento para remover do sistema:", ids_cancelamento)
                                
                                if st.button("💥 Cancelar e Excluir Agendamento Selecionado", type="primary"):
                                    try:
                                        dados_completos_planilha = wks_a.get_all_records()
                                        linha_indice_gspread = None
                                        
                                        for i, r in enumerate(dados_completos_planilha):
                                            if str(r.get("ID")).strip() == str(id_cancelar_sel).strip():
                                                linha_indice_gspread = i + 2
                                                break
                                                
                                        if linha_indice_gspread:
                                            wks_a.delete_rows(linha_indice_gspread)
                                            st.success(f"🔥 O agendamento de ID {id_cancelar_sel} foi cancelado e a linha foi removida da planilha!")
                                            st.cache_data.clear()
                                            time.sleep(1.5)
                                            st.rerun()
                                        else:
                                            st.error("Não foi possível encontrar a linha correspondente a esse ID no Google Sheets.")
                                    except Exception as e:
                                        st.error(f"Erro ao deletar linha de agendamento: {e}")
                                        
                                st.markdown("---")
                                if st.checkbox("⚠️ ATENÇÃO: Habilitar opção de Limpeza Total da Tabela"):
                                    if st.button("🚨 APAGAR ABSOLUTAMENTE TODOS OS AGENDAMENTOS", use_container_width=True, type="primary"):
                                        try:
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
                        st.info("ℹ️ Nenhum agendamento foi registrado até o momento.")
                        
                except Exception as e:
                    st.error(f"Erro ao carregar o painel de gerenciamento: {e}")

        elif pagina_atual == "Relatórios":
            st.title("📊 Painel de Relatórios Consolidados e Impressão")
            st.write("Exibição e exportação de dados pedagógicos e frequência.")
            
            sh = conectar_google_sheets()
            todas_abas = sh.worksheets()
            nomes_abas = [w.title for w in todas_abas]
            
            abas_notas_disponiveis = [n for n in nomes_abas if n.startswith("Notas_")]
            abas_freq_disponiveis = [n for n in nomes_abas if n.startswith("Freq_")]
            
            tipo_relatorio = st.radio("Selecione o tipo de relatório que deseja gerar:", ["Boletim Informativo de Notas", "Ficha Conclusiva de Frequência"])
            
            if tipo_relatorio == "Boletim Informativo de Notas":
                if not abas_notas_disponiveis:
                    st.info("Nenhuma planilha de Notas foi gerada até o momento para compor relatórios.")
                else:
                    aba_escolhida = st.selectbox("Selecione a Turma e Disciplina cadastrada:", abas_notas_disponiveis)
                    try:
                        df_rel_n = pd.DataFrame(sh.worksheet(aba_escolhida).get_all_records())
                        if df_rel_n.empty:
                            st.warning("A planilha selecionada está vazia.")
                        else:
                            st.markdown(f"### Boletim de Desempenho Escolar: `{aba_escolhida}`")
                            st.dataframe(df_rel_n, use_container_width=True, hide_index=True)
                            
                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                                df_rel_n.to_excel(writer, index=False, sheet_name='Boletim')
                            dados_excel = output.getvalue()
                            
                            st.download_button(
                                label="📥 Exportar Boletim para Excel (.xlsx)",
                                data=dados_excel,
                                file_name=f"Relatorio_{aba_escolhida}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    except Exception as e:
                        st.error(f"Erro ao processar dados de notas: {e}")
                        
            elif tipo_relatorio == "Ficha Conclusiva de Frequência":
                if not abas_freq_disponiveis:
                    st.info("Nenhuma planilha de Frequência foi gerada até o momento para compor relatórios.")
                else:
                    aba_escolhida_f = st.selectbox("Selecione a Frequência da Turma e Disciplina:", abas_freq_disponiveis)
                    try:
                        df_rel_f = pd.DataFrame(sh.worksheet(aba_escolhida_f).get_all_records())
                        if df_rel_f.empty:
                            st.warning("A planilha de frequência está vazia.")
                        else:
                            st.markdown(f"### Controle de Faltas Consolidado: `{aba_escolhida_f}`")
                            st.dataframe(df_rel_f, use_container_width=True, hide_index=True)
                            
                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                                df_rel_f.to_excel(writer, index=False, sheet_name='Frequencia')
                            dados_excel_f = output.getvalue()
                            
                            st.download_button(
                                label="📥 Exportar Ficha de Frequência para Excel (.xlsx)",
                                data=dados_excel_f,
                                file_name=f"Relatorio_Frequencia_{aba_escolhida_f}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    except Exception as e:
                        st.error(f"Erro ao processar dados de frequência: {e}")

        elif pagina_atual == "Configurações":
            if st.session_state.perfil != "Admin":
                st.error("Acesso negado.")
                st.stop()
                
            st.title("⚙️ Painel de Configurações Administrativas")
            
            menu_config = st.tabs(["👥 Cadastro de Professores", "👶 Cadastro de Alunos", "📋 Gerenciar Estrutura de Abas"])
            
            with menu_config[0]:
                st.subheader("Gerenciar Professores Cadastrados no Sistema")
                st.dataframe(df_p, use_container_width=True, hide_index=True)
                
                with st.expander("➕ Cadastrar / Modificar Professor Individualmente"):
                    with st.form("form_add_prof"):
                        nome_p_novo = st.text_input("Nome do Professor / Login").strip()
                        senha_p_novo = st.text_input("Senha de Acesso", type="password").strip()
                        
                        col_t1, col_t2 = st.columns(2)
                        with col_t1:
                            t1 = st.text_input("Turma 1").strip()
                            t2 = st.text_input("Turma 2").strip()
                            t3 = st.text_input("Turma 3").strip()
                            t4 = st.text_input("Turma 4").strip()
                            t5 = st.text_input("Turma 5").strip()
                        with col_t2:
                            d1 = st.text_input("Disciplina 1").strip()
                            d2 = st.text_input("Disciplina 2").strip()
                            d3 = st.text_input("Disciplina 3").strip()
                            d4 = st.text_input("Disciplina 4").strip()
                            d5 = st.text_input("Disciplina 5").strip()
                            
                        btn_salvar_prof_ind = st.form_submit_with_button("Salvar Professor no Banco de Dados", type="primary")
                        
                        if btn_salvar_prof_ind:
                            if not nome_p_novo or not len(senha_p_novo):
                                st.error("Nome do Professor e Senha são campos obrigatórios.")
                            else:
                                try:
                                    sh = conectar_google_sheets()
                                    wks_p = sh.worksheet("Config_Professores")
                                    
                                    dados_p_brutos = wks_p.get_all_records()
                                    df_p_temp = pd.DataFrame(dados_p_brutos)
                                    
                                    linha_existente_index = None
                                    if not df_p_temp.empty and "Nome" in df_p_temp.columns:
                                        for i, r in enumerate(dados_p_brutos):
                                            if str(r.get("Nome")).strip() == str(nome_p_novo).strip():
                                                linha_existente_index = i + 2
                                                break
                                                
                                    nova_linha_p = [nome_p_novo, senha_p_novo, t1, t2, t3, t4, t5, d1, d2, d3, d4, d5]
                                    
                                    if linha_existente_index:
                                        wks_p.update(range_name=f"A{linha_existente_index}:L{linha_existente_index}", values=[nova_linha_p])
                                        st.success(f"🔄 Cadastro do professor '{nome_p_novo}' foi atualizado com sucesso!")
                                    else:
                                        wks_p.append_row(nova_linha_p)
                                        st.success(f"🎉 Novo professor '{nome_p_novo}' gravado com sucesso!")
                                        
                                    st.cache_data.clear()
                                    time.sleep(1.5)
                                    st.rerun()
                                except Exception as ex:
                                    st.error(f"Erro ao interagir com a planilha Config_Professores: {ex}")
                                    
                with st.expander("🗑️ Excluir Professor do Sistema"):
                    if not df_p.empty and "Nome" in df_p.columns:
                        prof_deletar_lista = sorted(list(df_p["Nome"].unique()))
                        prof_remover = st.selectbox("Selecione o professor para remover permanentemente:", prof_deletar_lista)
                        
                        if st.button("💥 Remover Cadastro do Professor", type="primary"):
                            try:
                                sh = conectar_google_sheets()
                                wks_p = sh.worksheet("Config_Professores")
                                dados_p_brutos = wks_p.get_all_records()
                                
                                idx_remover_gspread = None
                                for i, r in enumerate(dados_p_brutos):
                                    if str(r.get("Nome")).strip() == str(prof_remover).strip():
                                        idx_remover_gspread = i + 2
                                        break
                                        
                                if idx_remover_gspread:
                                    wks_p.delete_rows(idx_remover_gspread)
                                    st.success(f"🔥 Professor '{prof_remover}' removido das configurações com sucesso!")
                                    st.cache_data.clear()
                                    time.sleep(1.5)
                                    st.rerun()
                                else:
                                    st.error("Não foi possível localizar o índice da linha na planilha.")
                            except Exception as ex:
                                st.error(f"Erro ao deletar linha de professor: {ex}")
                                
            with menu_config[1]:
                st.subheader("Gerenciar Alunos Matriculados por Turma")
                st.dataframe(df_a, use_container_width=True, hide_index=True)
                
                with st.expander("➕ Adicionar Alunos em Lote (Copia/Cola do Excel)"):
                    st.write("Insira os dados organizados em duas colunas: a primeira contendo o nome completo do aluno e a segunda contendo a turma respectiva.")
                    lista_texto_colar = st.text_area("Lista de Alunos para Adicionar (Cole do Excel):", placeholder="Exemplo:\nJoão Silva\t1º Ano A\nMaria Oliveira\t2º Ano B", height=150)
                    
                    if st.button("💾 Adicionar Alunos na Planilha", type="primary"):
                        if not lista_texto_colar.strip():
                            st.error("Nenhum dado foi inserido na caixa de texto.")
                        else:
                            linhas_processadas = []
                            for linha in lista_texto_colar.strip().split("\n"):
                                partes = linha.split("\t")
                                if len(partes) >= 2:
                                    linhas_processadas.append([partes[0].strip(), partes[1].strip()])
                                else:
                                    partes_espaco = linha.rsplit(" ", 1)
                                    if len(partes_espaco) >= 2:
                                        linhas_processadas.append([partes_espaco[0].strip(), partes_espaco[1].strip()])
                                        
                            if not linhas_processadas:
                                st.error("Não foi possível interpretar o formato do texto inserido. Certifique-se de usar tabulação ou espaço para separar o nome da turma.")
                            else:
                                try:
                                    sh = conectar_google_sheets()
                                    wks_a = sh.worksheet("Config_Alunos")
                                    wks_a.append_rows(linhas_processadas)
                                    st.success(f"🎉 Sucesso! {len(linhas_processadas)} novos alunos inseridos na tabela Config_Alunos!")
                                    st.cache_data.clear()
                                    time.sleep(1.5)
                                    st.rerun()
                                except Exception as ex:
                                    st.error(f"Erro ao anexar os alunos no Google Sheets: {ex}")
                                    
                with st.expander("🗑️ Limpar Absolutamente Toda a Lista de Alunos"):
                    st.warning("Esta operação vai apagar todas as linhas da tabela de alunos (Config_Alunos), deixando apenas a linha de cabeçalho.")
                    if st.checkbox("Confirmo que quero zerar as matrículas de alunos"):
                        if st.button("🚨 APAGAR TODOS OS ALUNOS", type="primary"):
                            try:
                                sh = conectar_google_sheets()
                                wks_a = sh.worksheet("Config_Alunos")
                                wks_a.resize(rows=1)
                                wks_a.resize(rows=1000)
                                st.success("💥 Banco de dados de alunos redefinido com sucesso!")
                                st.cache_data.clear()
                                time.sleep(1.5)
                                st.rerun()
                            except Exception as ex:
                                st.error(f"Erro ao redimensionar/limpar a aba de alunos: {ex}")
                                
            with menu_config[2]:
                st.subheader("Manutenção e Reset do Banco de Dados do Google Sheets")
                st.write("Lista completa de abas ativas detectadas no arquivo conectado:")
                st.write(nomes_abas)
                
                with st.expander("❌ Apagar Aba Específica do Diário de Classe (Notas/Frequência)"):
                    st.warning("Use esta opção para deletar planilhas geradas de turmas/disciplinas específicas caso precise reiniciar os lançamentos daquele componente.")
                    abas_deletaveis = [n for n in nomes_abas if n.startswith("Notas_") or n.startswith("Freq_") or n.startswith("Cont_")]
                    
                    if not abas_deletaveis:
                        st.info("Nenhuma aba dinâmica passível de remoção automática foi encontrada.")
                    else:
                        aba_alvo_remocao = st.selectbox("Selecione a aba que deseja DELETAR permanentemente:", abas_deletaveis)
                        if st.checkbox(f"Estou ciente de que os dados da aba '{aba_alvo_remocao}' serão destruídos"):
                            if st.button("🔥 Confirmar e Destruir Aba Selecionada", type="primary"):
                                try:
                                    sh = conectar_google_sheets()
                                    wks_alvo = sh.worksheet(aba_alvo_remocao)
                                    sh.del_worksheet(wks_alvo)
                                    st.success(f"💥 A aba '{aba_alvo_remocao}' foi deletada com sucesso!")
                                    st.cache_data.clear()
                                    time.sleep(1.5)
                                    st.rerun()
                                except Exception as ex:
                                    st.error(f"Erro ao remover a aba: {ex}")

if __name__ == "__main__":
    main()
