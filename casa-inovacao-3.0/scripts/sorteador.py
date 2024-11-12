import streamlit as st
import pandas as pd
import random
from io import BytesIO

# Inicializar lista global de sorteados na session_state
if 'sorteados_geral' not in st.session_state:
    st.session_state.sorteados_geral = pd.DataFrame(columns=['Name', 'ID', 'Cota'])

# Função para realizar sorteio por grupo com verificação rigorosa de duplicados
def realizar_sorteio_por_grupo(df, quantidade_por_grupo, curso):
    ganhadores_por_grupo = {}
    
    # Remover candidatos já sorteados em qualquer curso
    df = df[~df['ID'].isin(st.session_state.sorteados_geral['ID'])]
    
    # Filtra para ampla concorrência
    df_ampla_concorrencia = df[df['Cota'] == 'Ampla Concorrência']
    
    for grupo, quantidade in quantidade_por_grupo.items():
        if grupo == 'Ampla Concorrência':
            continue  # Deixamos o sorteio de ampla concorrência para o final
        
        df_grupo = df[df['Cota'] == grupo]
        total_grupo = len(df_grupo)
        
        if total_grupo > 0:
            quantidade_real = min(quantidade, total_grupo)
            ganhadores = df_grupo.sample(n=quantidade_real, random_state=random.randint(0, 10000))
            
            # Preenche com ampla concorrência se faltarem vagas
            if quantidade_real < quantidade and not df_ampla_concorrencia.empty:
                vagas_restantes = quantidade - quantidade_real
                ganhadores_extra = df_ampla_concorrencia.sample(n=min(vagas_restantes, len(df_ampla_concorrencia)), random_state=random.randint(0, 10000))
                df_ampla_concorrencia = df_ampla_concorrencia.drop(ganhadores_extra.index)
                ganhadores = pd.concat([ganhadores, ganhadores_extra])
            
            ganhadores_por_grupo[grupo] = ganhadores
        else:
            st.warning(f"Não há candidatos no grupo '{grupo}'. Vagas preenchidas pela ampla concorrência.")
            if not df_ampla_concorrencia.empty:
                ganhadores_extra = df_ampla_concorrencia.sample(n=min(quantidade, len(df_ampla_concorrencia)), random_state=random.randint(0, 10000))
                df_ampla_concorrencia = df_ampla_concorrencia.drop(ganhadores_extra.index)
                ganhadores_por_grupo[grupo] = ganhadores_extra
    
    # Sorteio de ampla concorrência com as vagas restantes
    total_ampla_concorrencia = len(df_ampla_concorrencia)
    quantidade_ampla = quantidade_por_grupo['Ampla Concorrência']
    quantidade_real = min(quantidade_ampla, total_ampla_concorrencia)
    if total_ampla_concorrencia > 0:
        ganhadores_ampla = df_ampla_concorrencia.sample(n=quantidade_real, random_state=random.randint(0, 10000))
        ganhadores_por_grupo['Ampla Concorrência'] = ganhadores_ampla
    
    # Verificação final para garantir a quantidade exata de sorteados por grupo
    ganhadores_df = pd.concat(ganhadores_por_grupo.values()).drop_duplicates(subset=['ID'])
    
    # Verificar e preencher vagas restantes se o total for inferior a 27
    vagas_faltantes = 27 - len(ganhadores_df)
    if vagas_faltantes > 0:
        candidatos_restantes = df[~df['ID'].isin(ganhadores_df['ID'])]
        
        if not candidatos_restantes.empty:
            ganhadores_extra = candidatos_restantes.sample(n=min(vagas_faltantes, len(candidatos_restantes)), random_state=random.randint(0, 10000))
            ganhadores_df = pd.concat([ganhadores_df, ganhadores_extra])
        else:
            st.warning("Não há candidatos suficientes para completar o sorteio com 27 ganhadores.")

    # Adiciona os ganhadores à lista global de sorteados
    ganhadores_df['Curso'] = curso
    st.session_state.sorteados_geral = pd.concat([st.session_state.sorteados_geral, ganhadores_df[['Name', 'ID', 'Cota', 'Curso']]]).drop_duplicates(subset=['ID'])
    
    return ganhadores_df

# Função para baixar o arquivo Excel
def baixar_excel(df, filename):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Ganhadores')
    processed_data = output.getvalue()
    return processed_data

# Configuração da aplicação
st.title("Sorteio Edital | Casa da Inovação")
st.image(r'C:\Users\natan\Documents\Besouro\ID_CASA_INOVACAO 1.png')

# Seletores de curso
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
    'CRIAÇÃO DE APLICATIVOS 18+| Tarde',
    'INTRODUÇÃO AO MUNDO DIGITAL E PACOTE OFFICE | Noite',
    'MARKETING DIGITAL | Noite',
])

# Upload do arquivo Excel
uploaded_file = st.file_uploader("Escolha um arquivo Excel", type=["xlsx", "xls"])

if uploaded_file is not None:
    # Leitura do arquivo Excel
    df = pd.read_excel(uploaded_file)
    
    # Verifica se algum candidato já foi sorteado (apenas pelo ID)
    candidatos_ja_sorteados = df[df['ID'].isin(st.session_state.sorteados_geral['ID'])]

    # Remove os candidatos já sorteados do DataFrame original
    df = df[~df['ID'].isin(candidatos_ja_sorteados['ID'])]

    # Exibe aviso se algum candidato foi removido
    if not candidatos_ja_sorteados.empty:
        lista_candidatos = "\n".join([f"ID: {row['ID']}, Nome: {row['Name']}" for index, row in candidatos_ja_sorteados.iterrows()])
        
    # Mostrar os primeiros registros do arquivo carregado
    st.write(f"Primeiros registros do arquivo ({curso_selecionado}):")
    st.dataframe(df.head())

    # Definição das quantidades de vagas por grupo
    quantidade_por_grupo = {
            'Ampla Concorrência': 15,
            'Negro ou Pardo': 3,
            'Pessoa com deficiência - PCD': 3,
            'Estudante de escola pública': 3,
            'Beneficiário Socioassistencial': 3
        }
    
    # Botão para realizar o sorteio
    if st.button(f"Realizar Sorteio para {curso_selecionado}"):
        ganhadores = realizar_sorteio_por_grupo(df, quantidade_por_grupo, curso_selecionado)
        
        if not ganhadores.empty:
            st.write(f"**{curso_selecionado}** - Lista de ganhadores:")
            st.dataframe(ganhadores)

            # Adicionar botão para baixar o Excel dos ganhadores do curso atual
            excel_data = baixar_excel(ganhadores, 'ganhadores.xlsx')
            st.download_button(
                label="Baixar lista de ganhadores",
                data=excel_data,
                file_name=f'{curso_selecionado.replace(" | ", "_").replace(" ", "_")}_ganhadores.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            st.warning("Nenhum ganhador foi selecionado. Verifique se há candidatos nos grupos especificados.")
    
    # Botão para baixar a lista geral de sorteados
    if st.button("Finalizar Sorteios e Baixar Lista Geral de Sorteados"):
        excel_data_geral = baixar_excel(st.session_state.sorteados_geral, 'sorteados_geral.xlsx')
        st.download_button(
            label="Baixar lista geral de sorteados",
            data=excel_data_geral,
            file_name='sorteados_geral.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
