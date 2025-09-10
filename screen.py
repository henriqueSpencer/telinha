import streamlit as st
import pandas as pd
import pickle
import plotly.express as px
from pathlib import Path

# ==================== CONFIGURAÇÃO INICIAL ====================
st.set_page_config(
    page_title="Dashboard Sell-in/Sell-out - Farmácias - BioWell",
    page_icon="💊",
    layout="wide"
)


# ==================== CARREGAR DADOS ====================

@st.cache_data
def load_data_from_file(path: Path) -> pd.DataFrame:
    with open(path, 'rb') as f:
        df = pickle.load(f)
    return df


def load_data():
    """Carrega dados do arquivo pickle"""
    try:
        # Caminho relativo ao app
        data_path = Path(__file__).parent / "input_files" / "analise_cruzada.pkl"

        if data_path.exists():
            df = load_data_from_file(data_path)
        else:
            st.warning("Arquivo local não encontrado. Envie o .pkl para carregar os dados.")
            uploaded = st.file_uploader("Envie o arquivo analise_cruzada.pkl", type=["pkl"])
            if not uploaded:
                return pd.DataFrame()
            df = pickle.load(uploaded)

        # Conversão da data
        df['mes_ano_dt'] = pd.to_datetime(df['mes_ano'], format='%m-%Y')

        # Colunas acumulativas
        df = df.sort_values(['produto_codigo', 'mes_ano_dt'])
        df['estoque_acumulado_produto'] = df.groupby('produto_codigo')['diferenca'].cumsum()

        df = df.sort_values(['cnpj_matriz', 'mes_ano_dt'])
        df['estoque_acumulado_cliente'] = df.groupby('cnpj_matriz')['diferenca'].cumsum()

        df = df.sort_values(['produto_codigo', 'cnpj_matriz', 'mes_ano_dt'])
        df['estoque_acumulado_produto_cliente'] = df.groupby(['produto_codigo', 'cnpj_matriz'])[
            'diferenca'].cumsum()

        # Retornar apenas as colunas necessárias já renomeadas
        df_final = df[[
            'mes_ano',
            'cliente_nome',
            'cnpj_matriz',
            'produto_codigo',
            'produto_descricao',
            'qtd_vendida_para_farmacia',
            'qtd_vendida_para_cliente',
            'diferenca',
            'estoque_acumulado_produto',
            'estoque_acumulado_cliente',
            'estoque_acumulado_produto_cliente',
            'mes_ano_dt'  # Manter para filtro de data
        ]].copy()

        # Renomear colunas
        df_final.columns = [
            'Mês/Ano',
            'Grupo',
            'CNPJ',
            'Produto',
            'Descrição',
            'Sell-in',
            'Sell-out',
            'Diferença',
            'Estoque Total por Produto',
            'Estoque por Grupo',
            'Estoque por Produto e Grupo',
            'mes_ano_dt'
        ]

        return df_final

    except FileNotFoundError:
        st.error("Arquivo não encontrado: input_files/analise_cruzada.pkl")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()


# ==================== APLICAÇÃO PRINCIPAL ====================
def main():
    # Título
    st.title("💊 Dashboard Sell-in/Sell-out - Farmácias - BioWell")

    # Carregar dados
    df = load_data()

    if df.empty:
        st.warning("Nenhum dado disponível")
        return

    # Sidebar - Filtros
    st.sidebar.header("🔍 Filtros")

    # Filtro de Data
    if 'mes_ano_dt' in df.columns:
        min_date = df['mes_ano_dt'].min().date()
        max_date = df['mes_ano_dt'].max().date()

        date_range = st.sidebar.date_input(
            "Período:",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

        # Garantir que sempre temos dois valores (início e fim)
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
        else:
            # Se apenas uma data selecionada, usar como início e fim
            start_date = end_date = date_range if not isinstance(date_range, tuple) else date_range[0]

    # Filtro de Produto (seleção única com opção All)
    produtos_disponiveis = ['All'] + sorted(df['Descrição'].unique())
    produto_selecionado = st.sidebar.selectbox(
        "Produto:",
        options=produtos_disponiveis,
        index=0  # Default: All
    )

    # Filtro de Farmácia (seleção única com opção All)
    farmacias_disponiveis = ['All'] + sorted(df['Grupo'].unique())
    farmacia_selecionada = st.sidebar.selectbox(
        "Grupo:",
        options=farmacias_disponiveis,
        index=0  # Default: All
    )

    # Aplicar filtros
    df_filtered = df.copy()

    if farmacia_selecionada != 'All':
        df_filtered = df_filtered[df_filtered['Grupo'] == farmacia_selecionada]

    if produto_selecionado != 'All':
        df_filtered = df_filtered[df_filtered['Descrição'] == produto_selecionado]

    # Aplicar filtro de data
    if 'mes_ano_dt' in df_filtered.columns:
        df_filtered = df_filtered[
            (df_filtered['mes_ano_dt'].dt.date >= start_date) &
            (df_filtered['mes_ano_dt'].dt.date <= end_date)
            ]

    if df_filtered.empty:
        st.warning("Nenhum dado encontrado com os filtros aplicados")
        return

    # Abas principais
    tab1, tab2 = st.tabs(["📊 Acompanhamento de Estoque", "🔄 Giro de Estoque"])

    # ==================== ABA 1: ACOMPANHAMENTO DE ESTOQUE ====================
    with tab1:
        st.header("Detalhes por Farmácia e Produto")

        # Gráfico de Estoque
        if farmacia_selecionada == 'All' and produto_selecionado == 'All':
            st.info("🔍 Selecione um Grupo ou um Produto para visualizar o gráfico de estoque")
        else:
            # Ordenar dados para o gráfico
            df_grafico = df_filtered.sort_values(['mes_ano_dt'])

            if produto_selecionado != 'All' and farmacia_selecionada == 'All':
                # Mostrar Estoque Total por Produto
                fig = px.line(
                    df_grafico,
                    x='mes_ano_dt',
                    y='Estoque Total por Produto',
                    title=f'Estoque Total - {produto_selecionado}',
                    markers=True
                )
                fig.update_layout(
                    xaxis_title='Período',
                    yaxis_title='Estoque Acumulado',
                    height=400
                )
                st.plotly_chart(fig, width='stretch')

            elif produto_selecionado == 'All' and farmacia_selecionada != 'All':
                fig = px.line(
                    df_grafico,
                    x='mes_ano_dt',
                    y='Estoque por Grupo',
                    title=f'Estoque por Grupo - {farmacia_selecionada}',
                    markers=True
                )
                fig.update_layout(
                    xaxis_title='Período',
                    yaxis_title='Estoque Acumulado',
                    height=400
                )
                st.plotly_chart(fig, width='stretch')


            elif produto_selecionado != 'All' and farmacia_selecionada != 'All':
                # Mostrar Estoque por Farmácia específica
                fig = px.line(
                    df_grafico,
                    x='mes_ano_dt',
                    y='Estoque por Produto e Grupo',
                    title=f'Estoque - {produto_selecionado} - {farmacia_selecionada}',
                    markers=True
                )
                fig.update_layout(
                    xaxis_title='Período',
                    yaxis_title='Estoque Acumulado',
                    height=400
                )
                st.plotly_chart(fig, width='stretch')

        # Ordenar por mês/ano, farmácia e produto
        df_tabela = df_filtered.sort_values(['mes_ano_dt', 'Grupo', 'Descrição'])

        # Exibir tabela (com as 5 colunas principais)
        st.dataframe(
            df_tabela[['Mês/Ano', 'Grupo', 'Descrição', 'Sell-in', 'Sell-out', 'Diferença']],
            width='stretch',
            height=600
        )

        # Informações na sidebar
        st.sidebar.markdown("---")
        st.sidebar.header("📊 Resumo")

        st.sidebar.info(f"""
        **Dados filtrados:**
        - Farmácias: {df_filtered['Grupo'].nunique()}
        - Produtos: {df_filtered['Descrição'].nunique()}
        - Total registros: {len(df_filtered)}
        - Período: {df_filtered['Mês/Ano'].min()} a {df_filtered['Mês/Ano'].max()}
        """)

    # ==================== ABA 2: GIRO DE ESTOQUE (VAZIA) ====================
    with tab2:
        st.header("Giro de Estoque")
        st.info("Esta funcionalidade será implementada em breve.")


if __name__ == "__main__":
    main()