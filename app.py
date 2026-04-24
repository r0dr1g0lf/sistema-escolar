import streamlit as st
import pandas as pd
from datetime import datetime

# LINK DA SUA PLANILHA (Formato para leitura direta)
SHEET_ID = "1ci4AdQq5jIFNsyas7I3zw9Y9RcdMnTME"

def ler_planilha(aba):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={aba}"
    return pd.read_csv(url)

# Configuração da página
st.set_page_config(page_title="Sistema Escola Diva", layout="centered")

# Carregamento de dados iniciais
try:
    df_profs = ler_planilha("Config_Professores")
    df_alunos = ler_planilha("Config_Alunos")
except:
    st.error("Erro ao conectar com a planilha. Verifique se ela está como 'Editor' para qualquer pessoa com o link.")
    st.stop()

# Controle de Sessão
if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.user_data = None

# TELA DE LOGIN
if not st.session_state.logado:
    st.title("🔑 Acesso ao Sistema")
    user_input = st.text_input("Usuário")
    pass_input = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        # Verifica se o usuário e senha existem na planilha
        match = df_profs[(df_profs['Usuario'] == user_input) & (df_profs['Senha'].astype(str) == pass_input)]
        
        if not match.empty:
            st.session_state.logado = True
            st.session_state.user_data = match.iloc[0].to_dict()
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")

# INTERFACE APÓS LOGIN
else:
    prof_nome = st.session_state.user_data['Professor']
    st.sidebar.write(f"Usuário: **{prof_nome}**")
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    st.title("📝 Registro de Ocorrências")
    
    with st.form("registro_form"):
        # 1. Seleção de Turma (baseada no que o prof atende ou todas)
        turmas_disponiveis = df_alunos['Turma'].unique()
        turma_sel = st.selectbox("Selecione a Turma", turmas_disponiveis)
        
        # 2. Seleção de Aluno (Filtra apenas alunos daquela turma)
        lista_alunos = df_alunos[df_alunos['Turma'] == turma_sel]['Nome_Aluno'].tolist()
        aluno_sel = st.selectbox("Selecione o Aluno", lista_alunos)
        
        # 3. Informações Pré-Preenchidas
        disciplina = st.selectbox("Disciplina", ["Artes", "Educação Física", "Inglês", "Espanhol", "Ensino Religioso", "Projeto de Vida"])
        periodo = st.selectbox("Período", ["1º Bimestre", "2º Bimestre", "3º Bimestre", "4º Bimestre"])
        tipo = st.radio("Tipo de Ocorrência", ["Indisciplina", "Falta de Material", "Não realizou tarefa", "Elogio/Destaque", "Atraso"])
        
        descricao = st.text_area("Detalhes Adicionais (opcional)")
        
        enviar = st.form_submit_button("Salvar na Planilha")

    if enviar:
        # Preparando a linha para salvar
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        # FORMATO PARA VOCÊ COPIAR E COLAR NA PLANILHA (Já que a escrita direta exige chaves de API mais complexas)
        st.success(f"Registro gerado para {aluno_sel}!")
        st.info("Copie a linha abaixo e cole na aba 'Registros_Ocorrencias':")
        linha_csv = f"{agora};{prof_nome};{turma_sel};{aluno_sel};{disciplina};{periodo};{tipo};{descricao}"
        st.code(linha_csv)
