import streamlit as st
import pandas as pd
from datetime import datetime

# LINK DA SUA PLANILHA
SHEET_ID = "1ci4AdQq5jIFNsyas7I3zw9Y9RcdMnTME"

# Função com 'cache_data' para carregar os dados mas permitir atualização
@st.cache_data(ttl=60) # O site limpa o cache a cada 60 segundos automaticamente
def ler_planilha(aba):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={aba}"
    # Adicionamos o parâmetro on_bad_lines para evitar erros se houver linhas vazias na planilha
    return pd.read_csv(url, on_bad_lines='skip')

# Configuração da página
st.set_page_config(page_title="Sistema Escola Diva", layout="centered")

# Tente carregar os dados
try:
    df_profs = ler_planilha("Config_Professores")
    df_alunos = ler_planilha("Config_Alunos")
except Exception as e:
    st.error(f"Erro ao ler a planilha: {e}")
    st.stop()

# Controle de Login
if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.user_data = None

if not st.session_state.logado:
    st.title("🔑 Acesso ao Sistema")
    user_input = st.text_input("Usuário")
    pass_input = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        match = df_profs[(df_profs['Usuario'] == user_input) & (df_profs['Senha'].astype(str) == pass_input)]
        if not match.empty:
            st.session_state.logado = True
            st.session_state.user_data = match.iloc[0].to_dict()
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")

else:
    prof_nome = st.session_state.user_data['Professor']
    st.sidebar.write(f"Conectado como: **{prof_nome}**")
    
    # Botão para forçar atualização dos dados da planilha
    if st.sidebar.button("Atualizar Dados da Planilha"):
        st.cache_data.clear()
        st.rerun()

    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    st.title("📝 Registro de Ocorrências")
    
    # --- FILTRO DE TURMA E ALUNO ---
    # Pegamos as turmas únicas da planilha de alunos
    todas_turmas = sorted(df_alunos['Turma'].unique().astype(str))
    
    turma_sel = st.selectbox("1. Escolha a Turma", todas_turmas, key="turma_selecionada")

    # Filtramos os alunos APENAS da turma selecionada
    alunos_filtrados = df_alunos[df_alunos['Turma'].astype(str) == turma_sel]['Nome_Aluno'].tolist()

    if alunos_filtrados:
        aluno_sel = st.selectbox("2. Escolha o Aluno", sorted(alunos_filtrados), key="aluno_selecionado")
    else:
        st.warning("Nenhum aluno encontrado para esta turma na planilha.")
        aluno_sel = None

    # --- RESTANTE DO FORMULÁRIO ---
    with st.form("form_ocorrencia", clear_on_submit=True):
        disciplina = st.selectbox("Disciplina", ["Artes", "Educação Física", "Inglês", "Espanhol", "Ensino Religioso", "Projeto de Vida"])
        periodo = st.selectbox("Período", ["1º Bimestre", "2º Bimestre", "3º Bimestre", "4º Bimestre"])
        tipo = st.radio("Tipo de Ocorrência", ["Indisciplina", "Falta de Material", "Não realizou tarefa", "Elogio/Destaque", "Atraso"])
        descricao = st.text_area("Detalhes Adicionais")
        
        enviar = st.form_submit_button("Gerar Registro")

    if enviar and aluno_sel:
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        st.success(f"Registro gerado com sucesso para {aluno_sel}!")
        
        # Mostra o resultado para copiar
        resultado = f"{agora};{prof_nome};{turma_sel};{aluno_sel};{disciplina};{periodo};{tipo};{descricao}"
        st.info("Copie e cole na aba 'Registros_Ocorrencias':")
        st.code(resultado)
