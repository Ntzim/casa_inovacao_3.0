import streamlit as st
import pandas as pd
import random
from io import BytesIO

# Inicializar lista global de sorteados na session_state
if 'sorteados_geral' not in st.session_state:
    st.session_state.sorteados_geral = pd.DataFrame(columns=['Name', 'ID', 'Cota', 'Curso'])

# Função para verificar se um candidato já foi sorteado
def ja_sorteado(name, id_):
    df = st.session_state.sorteados_geral
    return ((df['ID'] == id_) | (df['Name'] == name)).any()

# Função para realizar sorteio por grupo com verificação rigorosa de duplicados por ID e Nome
def realizar_sorteio_por_grupo(df, quantidade_por_grupo, curso):
    ganhadores_por_grupo = {}

    # Remove candidatos já sorteados por ID ou Name
    df = df[~df.apply(lambda row: ja_sorteado(row['Name'], row['ID']), axis=1)]

    df_ampla_concorrencia = df[df['Cota'] == 'Ampla Concorrência']

    for grupo, quantidade in quantidade_por_grupo.items():
        if grupo == 'Ampla Concorrência':
            continue

        df_grupo = df[df['Cota'] == grupo]
        total_grupo = len(df_grupo)

        if total_grupo > 0:
            quantidade_real = min(quantidade, total_grupo)
            ganhadores = df_grupo.sample(n=quantidade_real, random_state=random.randint(0, 10000))

            # Completa com ampla concorrência se faltar candidatos
            if quantidade_real < quantidade and not df_ampla_concorrencia.empty:
                vagas_restantes = quantidade - quantidade_real
                extras = df_ampla_concorrencia.sample(n=min(vagas_restantes, len(df_ampla_concorrencia)), random_state=random.randint(0, 10000))
                df_ampla_concorrencia = df_ampla_concorrencia.drop(extras.index)
                ganhadores = pd.concat([ganhadores, extras])

            ganhadores_por_grupo[grupo] = ganhadores

        else:
            st.warning(f"Não há candidatos no grupo '{grupo}'. Vagas serão preenchidas pela ampla concorrência.")
            if not df_ampla_concorrencia.empty:
                extras = df_ampla_concorrencia.sample(n=min(quantidade, len(df_ampla_concorrencia)), random_state=random.randint(0, 10000))
                df_ampla_concorrencia = df_ampla_concorrencia.drop(extras.index)
                ganhadores_por_grupo[grupo] = extras

    # Sorteio de ampla concorrência
    total_ampla = len(df_ampla_concorrencia)
    quantidade_ampla = quantidade_por_grupo.get('Ampla Concorrência', 0)
    if total_ampla > 0:
        quantidade_real = min(quantidade_ampla, total_ampla)
        ganhadores_ampla = df_ampla_concorrencia.sample(n=quantidade_real, random_state=random.randint(0, 10000))
        ganhadores_por_grupo['Ampla Concorrência'] = ganhadores_ampla

    ganhadores_df = pd.concat(ganhadores_por_grupo.values()).drop_duplicates(subset=['ID', 'Name'])

    # Preenche até 27 ganhadores no total
    vagas_faltantes = 27 - len(ganhadores_df)
    if vagas_faltantes > 0:
        candidatos_restantes = df[~df.apply(lambda row: (row['ID'] in ganhadores_df['ID'].values) or (row['Name'] in ganhadores_df['Name'].values), axis=1)]
        if not candidatos_restantes.empty:
            extras = candidatos_restantes.sample(n=min(vagas_faltantes, len(candidatos_restantes)), random_state=random.randint(0, 10000))
            ganhadores_df = pd.concat([ganhadores_df, extras])
        else:
            st.warning("Não há candidatos suficientes para completar os 27 ganhadores.")

    # Atualiza lista geral
    ganhadores_df['Curso'] = curso
    st.session_state.sorteados_geral = pd.concat(
        [st.session_state.sorteados_geral, ganhadores_df[['Name', 'ID', 'Cota', 'Curso']]]
    ).drop_duplicates(subset=['ID', 'Name'])

    return ganhadores_df

# Função para baixar o arquivo Excel
def baixar_excel(df, filename):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Ganhadores')
    return output.getvalue()

# Título e imagem
st.title("Sorteio Edital | Casa da Inovação")
st.image('casa-inovacao-3.0/imagens/ID_CASA_INOVACAO 1.png')

# Exibe o total acumulado de sorteados
st.info(f"🎉 Total geral de sorteados até agora: **{len(st.session_state.sorteados_geral)}**")

# Curso selecionado
curso_selecionado = st.selectbox("Selecione o curso", [
    'INCLUSÃO DIGITAL 50+  | Manhã',
    'CRIAÇÃO DE GAMES KIDS | Manhã',
    'INTRODUÇÃO À ROBÓTICA KIDS | Manhã',
    'INTRODUÇÃO À ROBÓTICA TEENS  | Manhã',
    'CRIAÇÃO DE APLICATIVOS | Tarde',
    'CRIAÇÃO DE GAMES KIDS| Tarde',
    'DIGITAL INFLUENCER| Tarde',
    'CRIAÇÃO DE GAMES TEEENS | Tarde',
    'INTRODUÇÃO À ROBÓTICA KIDS| Tarde',
    'INCLUSÃO DIGITAL 50+| Tarde',
    'INTRODUÇÃO AO MUNDO DIGITAL E PACOTE OFFICE | Noite',
    'MARKETING DIGITAL | Noite',
])

# Upload do arquivo
uploaded_file = st.file_uploader("Escolha um arquivo Excel", type=["xlsx", "xls"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # Remover candidatos já sorteados (ID ou Name)
    df = df[~df.apply(lambda row: ja_sorteado(row['Name'], row['ID']), axis=1)]

    st.write(f"Primeiros registros do arquivo ({curso_selecionado}):")
    st.dataframe(df.head())

    quantidade_por_grupo = {
        'Ampla Concorrência': 15,
        'Negro ou Pardo': 3,
        'Pessoa com deficiência - PCD': 3,
        'Estudante de escola pública': 3,
        'Beneficiário Socioassistencial': 3
    }

    if st.button(f"Realizar Sorteio para {curso_selecionado}"):
        ganhadores = realizar_sorteio_por_grupo(df, quantidade_por_grupo, curso_selecionado)
        if not ganhadores.empty:
            st.write(f"**{curso_selecionado}** - Lista de ganhadores:")
            st.dataframe(ganhadores)

            # Contagem de sorteados
            st.success(f"✅ Total de sorteados neste curso: **{len(ganhadores)}**")
            st.info(f"📌 Total geral de sorteados: **{len(st.session_state.sorteados_geral)}**")

            # Contagem por grupo de cota
            st.subheader("Distribuição por Grupo de Cota:")
            contagem_por_grupo = ganhadores['Cota'].value_counts()
            for grupo, qtd in contagem_por_grupo.items():
                st.write(f"- {grupo}: {qtd} sorteado(s)")

            excel_data = baixar_excel(ganhadores, 'ganhadores.xlsx')
            st.download_button(
                label="📥 Baixar lista de ganhadores",
                data=excel_data,
                file_name=f'{curso_selecionado.replace(" | ", "_").replace(" ", "_")}_ganhadores.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            st.warning("Nenhum ganhador foi selecionado.")

    if st.button("📦 Finalizar Sorteios e Baixar Lista Geral de Sorteados"):
        excel_data_geral = baixar_excel(st.session_state.sorteados_geral, 'sorteados_geral.xlsx')
        st.download_button(
            label="📥 Baixar lista geral de sorteados",
            data=excel_data_geral,
            file_name='sorteados_geral.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
