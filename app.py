import streamlit as st
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Sistema Escolar Diva", layout="wide")

# Simulação de um banco de dados simples (Lista de usuários)
# Em um sistema real, isso ficaria escondido
usuarios = {
    "admin": {"senha": "123", "perfil": "ADM"},
    "professor": {"senha": "456", "perfil": "USER"}
}

# Funções de Controle de Acesso
if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.perfil = None

def login():
    st.title("🔑 Acesso ao Sistema")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if usuario in usuarios and usuarios[usuario]["senha"] == senha:
            st.session_state.logado = True
            st.session_state.perfil = usuarios[usuario]["perfil"]
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos")

# Interface após o Login
if not st.session_state.logado:
    login()
else:
    st.sidebar.title(f"Bem-vindo, {st.session_state.perfil}")
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    # --- ÁREA DO ADMINISTRADOR ---
    if st.session_state.perfil == "ADM":
        st.header("🛠 Painel de Administração")
        
        aba1, aba2 = st.tabs(["Cadastrar Questões", "Gerenciar Professores"])
        
        with aba1:
            st.subheader("Nova Questão")
            with st.form("form_adm"):
                pergunta = st.text_area("Pergunta")
                correta = st.text_input("Resposta Correta")
                op2 = st.text_input("Opção 2")
                op3 = st.text_input("Opção 3")
                op4 = st.text_input("Opção 4")
                
                if st.form_submit_button("Salvar Questão"):
                    # Aqui criamos o formato que você pediu: Pergunta;Resposta;...
                    linha = f"{pergunta};{correta};{op2};{op3};{op4}"
                    st.success(f"Questão cadastrada com sucesso!")
                    st.code(linha) # Mostra como ficou o texto
        
        with aba2:
            st.write("Aqui você poderá cadastrar novos professores no futuro.")

    # --- ÁREA DO PROFESSOR (USER) ---
    else:
        st.header("📝 Área do Professor")
        st.info("Olá! Aqui você pode alimentar as informações do conselho de classe.")
        # Espaço para o professor trabalhar
        ocorrencia = st.text_area("Descreva a ocorrência do aluno:")
        if st.button("Enviar Relatório"):
            st.success("Relatório enviado para o banco de dados!")