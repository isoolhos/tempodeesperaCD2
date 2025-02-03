import cx_Oracle
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import time
from config import senha, user, host, porta, service_name

# 📌 **Lista de usuários autorizados**
usuarios = {
    "admin": "iso300",
    "medicos": "medicos",
    "atendimento": "atendimento",
    "fabiana": "fabiana"
}

# 📌 **Verifica se o usuário já está logado**
if "logado" not in st.session_state:
    st.session_state.logado = False

# 📌 **Tela de Login**
if not st.session_state.logado:
    st.title("🔒 Login")

    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    botao_login = st.button("Entrar")

    if botao_login:
        if usuario in usuarios and usuarios[usuario] == senha:
            st.session_state.logado = True
            st.session_state.usuario = usuario  # Salva o usuário logado
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos! ❌")

# 📌 **Se o usuário estiver logado, mostra o conteúdo**
if st.session_state.logado:
    # Centralizar a logo da empresa
    st.markdown(
        """
        <div style="display: flex; justify-content: center; align-items: center; margin-bottom: 20px;">
            <img src="https://d2q79iu7y748jz.cloudfront.net/s/_squarelogo/256x256/ca7be833f39e1d0ef52b233d5b757915" alt="Logo da Empresa" style="width: 150px;">
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Configuração do título do Streamlit
    st.title("📊 Tempo de Atendimento no CD")

    # 📌 **Criar menu lateral para navegação entre páginas**
    pagina = st.sidebar.radio("📍 Selecione a Página", ["Lista de Pacientes", "Dashboard"])

    # 📌 **Botão para Logout**
    if st.sidebar.button("🔓 Sair"):
        st.session_state.logado = False
        st.rerun()

    # 📌 **Mensagem de boas-vindas**
    st.sidebar.write(f"👤 Usuário logado: **{st.session_state.usuario}**")

    # Configuração da conexão com Oracle
    usuario_db = user
    senha_db = senha
    host = host
    porta = porta
    service_name = service_name

    # 📌 **Função para obter os dados do banco de dados**
    def obter_dados():
        try:
            dsn_tns = cx_Oracle.makedsn(host, porta, service_name=service_name)
            conexao = cx_Oracle.connect(user=usuario_db, password=senha_db, dsn=dsn_tns)
            cursor = conexao.cursor()

            query = """
            SELECT status, agenda, nomepac, 
                to_char(HORA_INI,'hh24:mi:ss') as INI_CD,
                round(((sysdate - HORA_INI)* 1440),2) as tempocd     
            FROM (
                SELECT substr(obter_descricao_padrao('STATUS_PACIENTE_AGENDA', 'DS_STATUS_PACIENTE', NR_SEQ_STATUS_PAC),1,100) as status,
                    obter_desc_agenda(cd_agenda) as agenda,
                    obter_nome_pf(cd_pessoa_fisica) as nomepac,
                    case 
                        when substr(obter_descricao_padrao('STATUS_PACIENTE_AGENDA', 'DS_STATUS_PACIENTE', NR_SEQ_STATUS_PAC),1,100) = ('CD Térreo')   
                        then (Select max(dt_historico) 
                                from agenda_paciente_hist b
                                where b.nr_seq_agenda = a.NR_SEQUENCIA
                                and ds_historico like '%para CD Térreo%')
                        when substr(obter_descricao_padrao('STATUS_PACIENTE_AGENDA', 'DS_STATUS_PACIENTE', NR_SEQ_STATUS_PAC),1,100) = ('Dilatação/CD')   
                        then (Select max(dt_historico) 
                                from agenda_paciente_hist b
                                where b.nr_seq_agenda = a.NR_SEQUENCIA
                                and ds_historico like '%para Dilatação/CD%')
                        else (Select max(dt_historico)
                                from agenda_paciente_hist b
                                where b.nr_seq_agenda = a.NR_SEQUENCIA
                                and ds_historico like '%para CD 1º Piso%')
                    end as HORA_INI
                FROM AGENDA_PACIENTE A
                WHERE TRUNC(HR_INICIO) = trunc(sysdate)
                AND substr(obter_descricao_padrao('STATUS_PACIENTE_AGENDA', 'DS_STATUS_PACIENTE', NR_SEQ_STATUS_PAC),1,100) 
                    IN ('CD Térreo', 'CD 1º Piso', 'Dilatação/CD')
                and obter_desc_agenda(cd_agenda) not like '%Bloco%'
                and cd_agenda not in (112,113)
            )
            ORDER BY 1, 5 DESC
            """

            cursor.execute(query)
            colunas = [col[0] for col in cursor.description]
            dados = cursor.fetchall()
            cursor.close()
            conexao.close()

            df = pd.DataFrame(dados, columns=colunas)

            return df

        except Exception as e:
            st.error(f"Erro ao conectar ao banco de dados: {e}")
            return pd.DataFrame()

    # **Se estiver na página de lista de pacientes**
    if pagina == "Lista de Pacientes":
        df = obter_dados()

        if df.empty:
            st.warning("⚠️ Nenhum dado encontrado.")
        else:
            df.columns = df.columns.str.upper()
            df = df.rename(columns={
                "STATUS": "Status",
                "AGENDA": "Agenda",
                "NOMEPAC": "Nome do Paciente",
                "INI_CD": "Hora Inicial",
                "TEMPOCD": "Tempo de Espera (min)"
            })

            # 📌 **Corrigir a numeração começando em 1**
            df.index = df.index + 1

            st.markdown("### 🏥 Pacientes em Espera - **CD TÉRREO**")
            st.write(df[df["Status"] == "CD Térreo"])

            st.markdown("### 🏥 Pacientes em Espera - **1º PISO**")
            st.write(df[df["Status"] == "CD 1º Piso"])

            st.markdown("### 🏥 Pacientes em Espera - **Dilatação/CD**")
            st.write(df[df["Status"] == "Dilatação/CD"])

    # **Se estiver na página de Dashboard**
    elif pagina == "Dashboard":
        df = obter_dados()

        if df.empty:
            st.warning("⚠️ Nenhum dado encontrado para exibir os gráficos.")
        else:
            df.columns = df.columns.str.upper()
            df = df.rename(columns={
                "STATUS": "Status",
                "AGENDA": "Agenda",
                "NOMEPAC": "Nome do Paciente",
                "INI_CD": "Hora Inicial",
                "TEMPOCD": "Tempo de Espera (min)"
            })

            # **Gráfico de Barras - Pacientes por Status**
            if "Status" in df.columns:
                status_counts = df["Status"].value_counts()
                fig_bar, ax_bar = plt.subplots()
                ax_bar.bar(status_counts.index, status_counts.values, color=["royalblue", "limegreen", "silver"])
                ax_bar.set_title("📊 Pacientes por Status")
                ax_bar.set_ylabel("Número de Pacientes")
                st.pyplot(fig_bar)

            # **Lista de Pacientes que ficaram mais de 42 minutos**
            df_excedentes = df[df["Tempo de Espera (min)"] > 42]
            if not df_excedentes.empty:
                st.markdown("### ⏳ Pacientes que ficaram mais de **42 minutos (hoje)**")
                st.write(df_excedentes)

            # **Gráfico de Pizza - Distribuição por Agenda**
            if "Agenda" in df.columns:
                agenda_counts = df["Agenda"].value_counts()
                fig_pizza, ax_pizza = plt.subplots(figsize=(6, 6))
                ax_pizza.pie(agenda_counts, labels=agenda_counts.index, autopct="%1.1f%%", startangle=140, colors=plt.cm.Paired.colors)
                ax_pizza.set_title("📊 Distribuição de Pacientes por Agenda")
                st.pyplot(fig_pizza)
