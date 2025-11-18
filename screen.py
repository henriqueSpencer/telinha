import streamlit as st
import pandas as pd
import pickle
import plotly.express as px
from pathlib import Path

# ==================== CONFIGURAÇÃO INICIAL ====================
st.set_page_config(
    page_title="Dashboard Sell-in/Sell-out - Grupos - BioWell",
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
        df['mes_ano_dt'] = pd.to_datetime(df['mes_ano'], format='%m-%Y').dt.date

        # Retornar apenas as colunas necessárias já renomeadas
        df_final = df[[
            'cliente_nome',
            'cnpj_matriz',
            'produto_codigo',
            'produto_descricao',
            'qtd_vendida_para_farmacia',
            'qtd_vendida_para_cliente',
            'diferenca',
            'mes_ano_dt'  # Manter para filtro de data
        ]].copy()

        # Renomear colunas
        df_final.columns = [
            'Grupo',
            'CNPJ',
            'Produto',
            'Descrição',
            'Sell-in',
            'Sell-out',
            'Diferença',
            'mes_ano_dt'
        ]

        return df_final

    except FileNotFoundError:
        st.error("Arquivo não encontrado: input_files/analise_cruzada.pkl")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()


# ==================== CALCULAR SOMAS ACUMULATIVAS ====================
def calculate_cumsums(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula as somas acumulativas baseadas no dataframe filtrado.
    As cumsums são calculadas apenas para os dados no dataframe fornecido,
    resetando no início do período filtrado.
    """
    df = df.copy()
    
    # Estoque Total por Produto (agrupado por Descrição)
    df = df.sort_values(['Descrição', 'mes_ano_dt'])
    df['Estoque Total por Produto'] = df.groupby('Descrição')['Diferença'].cumsum()
    
    # Estoque por Grupo (agrupado por Grupo)
    df = df.sort_values(['Grupo', 'mes_ano_dt'])
    df['Estoque por Grupo'] = df.groupby('Grupo')['Diferença'].cumsum()
    
    # Sell-in por Grupo (agrupado por Grupo)
    df = df.sort_values(['Grupo', 'mes_ano_dt'])
    df['Sell-in por Grupo'] = df.groupby('Grupo')['Sell-in'].cumsum()
    
    # Sell-out por Grupo (agrupado por Grupo)
    df = df.sort_values(['Grupo', 'mes_ano_dt'])
    df['Sell-out por Grupo'] = df.groupby('Grupo')['Sell-out'].cumsum()
    
    # Estoque por Produto e Grupo (agrupado por Descrição e Grupo)
    df = df.sort_values(['Descrição', 'Grupo', 'mes_ano_dt'])
    df['Estoque por Produto e Grupo'] = df.groupby(['Descrição', 'Grupo'])['Diferença'].cumsum()
    
    return df


# ==================== APLICAÇÃO PRINCIPAL ====================
def main():
    # Título
    st.title("💊 Dashboard Sell-in/Sell-out - Grupos - BioWell")

    # Carregar dados
    df = load_data()

    if df.empty:
        st.warning("Nenhum dado disponível")
        return

    # Sidebar - Filtros
    st.sidebar.header("🔍 Filtros")

    # Filtro de Data
    if 'mes_ano_dt' in df.columns:
        min_date = df['mes_ano_dt'].min()
        max_date = df['mes_ano_dt'].max()

        date_range = st.sidebar.date_input(
            "Período:",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            format="DD-MM-YYYY"
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
            (df_filtered['mes_ano_dt'] >= start_date) &
            (df_filtered['mes_ano_dt'] <= end_date)
            ]

    if df_filtered.empty:
        st.warning("Nenhum dado encontrado com os filtros aplicados")
        return

    # Calcular somas acumulativas baseadas no período filtrado
    df_filtered = calculate_cumsums(df_filtered)

    # Abas principais
    tab1, tab2 = st.tabs(["📊 Acompanhamento de Estoque", "🔄 Giro de Estoque"])

    # ==================== ABA 1: ACOMPANHAMENTO DE ESTOQUE ====================
    with tab1:
        st.header("Detalhes por Grupo e Produto")

        # Gráfico de Estoque
        if farmacia_selecionada == 'All' and produto_selecionado == 'All':
            fig = px.line(
                    df_grafico,
                    x='mes_ano_dt',
                    y='Estoque Geral',
                    title=f'Estoque, Sell-in e Sell-out Geral',
                    markers=True
                )
                # Adicionar linha de Sell-in (verde)
                fig.add_trace(px.line(
                    df_grafico,
                    x='mes_ano_dt',
                    y='Sell-in Geral',
                    markers=True,
                    color_discrete_sequence=['green']
                ).data[0].update(name='Sell-in'))
                
                # Adicionar linha de Sell-out (vermelho)
                fig.add_trace(px.line(
                    df_grafico,
                    x='mes_ano_dt',
                    y='Sell-out por Geral',
                    markers=True,
                    color_discrete_sequence=['red']
                ).data[0].update(name='Sell-out'))
                
                # Atualizar o nome da linha de estoque
                fig.data[0].name = 'Estoque Geral'
                
                # Configurar hover personalizado para cada linha
                fig.data[0].hovertemplate = '<b>Estoque Geral</b><br>' + \
                                          'Período: %{x}<br>' + \
                                          'Valor: %{y:,.0f}<br>' + \
                                          '<extra></extra>'
                
                fig.data[1].hovertemplate = '<b>Sell-in Geral</b><br>' + \
                                          'Período: %{x}<br>' + \
                                          'Valor: %{y:,.0f}<br>' + \
                                          '<extra></extra>'
                
                fig.data[2].hovertemplate = '<b>Sell-out Geral</b><br>' + \
                                          'Período: %{x}<br>' + \
                                          'Valor: %{y:,.0f}<br>' + \
                                          '<extra></extra>'
                
                fig.update_layout(
                    xaxis_title='Período',
                    yaxis_title='Quantidade',
                    height=400,
                    legend=dict(
                        yanchor="top",
                        y=0.99,
                        xanchor="left",
                        x=0.01
                    ),
                    hovermode='x unified'  # Mostra todos os valores no mesmo ponto
                )
                st.plotly_chart(fig, width='stretch')
        else:
            # Ordenar dados para o gráfico
            df_grafico = df_filtered.sort_values(['mes_ano_dt'])

            # if produto_selecionado != 'All' and farmacia_selecionada == 'All':
            #     # Mostrar Estoque Total por Produto
            #     fig = px.line(
            #         df_grafico,
            #         x='mes_ano_dt',
            #         y='Estoque Total por Produto',
            #         title=f'Estoque Total - {produto_selecionado}',
            #         markers=True
            #     )
            #     fig.update_layout(
            #         xaxis_title='Período',
            #         yaxis_title='Estoque Acumulado',
            #         height=400
            #     )
            #     st.plotly_chart(fig, width='stretch')

            if produto_selecionado == 'All' and farmacia_selecionada != 'All':
                fig = px.line(
                    df_grafico,
                    x='mes_ano_dt',
                    y='Estoque por Grupo',
                    title=f'Estoque, Sell-in e Sell-out por Grupo - {farmacia_selecionada}',
                    markers=True
                )
                # Adicionar linha de Sell-in (verde)
                fig.add_trace(px.line(
                    df_grafico,
                    x='mes_ano_dt',
                    y='Sell-in por Grupo',
                    markers=True,
                    color_discrete_sequence=['green']
                ).data[0].update(name='Sell-in'))
                
                # Adicionar linha de Sell-out (vermelho)
                fig.add_trace(px.line(
                    df_grafico,
                    x='mes_ano_dt',
                    y='Sell-out por Grupo',
                    markers=True,
                    color_discrete_sequence=['red']
                ).data[0].update(name='Sell-out'))
                
                # Atualizar o nome da linha de estoque
                fig.data[0].name = 'Estoque por Grupo'
                
                # Configurar hover personalizado para cada linha
                fig.data[0].hovertemplate = '<b>Estoque por Grupo</b><br>' + \
                                          'Período: %{x}<br>' + \
                                          'Valor: %{y:,.0f}<br>' + \
                                          '<extra></extra>'
                
                fig.data[1].hovertemplate = '<b>Sell-in por Grupo</b><br>' + \
                                          'Período: %{x}<br>' + \
                                          'Valor: %{y:,.0f}<br>' + \
                                          '<extra></extra>'
                
                fig.data[2].hovertemplate = '<b>Sell-out por Grupo</b><br>' + \
                                          'Período: %{x}<br>' + \
                                          'Valor: %{y:,.0f}<br>' + \
                                          '<extra></extra>'
                
                fig.update_layout(
                    xaxis_title='Período',
                    yaxis_title='Quantidade',
                    height=400,
                    legend=dict(
                        yanchor="top",
                        y=0.99,
                        xanchor="left",
                        x=0.01
                    ),
                    hovermode='x unified'  # Mostra todos os valores no mesmo ponto
                )
                st.plotly_chart(fig, width='stretch')

            elif produto_selecionado != 'All' and farmacia_selecionada != 'All':
                # Mostrar Estoque por Farmácia específica com Sell-in e Sell-out
                fig = px.line(
                    df_grafico,
                    x='mes_ano_dt',
                    y='Estoque por Produto e Grupo',
                    title=f'Estoque, Sell-in e Sell-out - {produto_selecionado} - {farmacia_selecionada}',
                    markers=True
                )
                
                # Adicionar linha de Sell-in (verde)
                fig.add_trace(px.line(
                    df_grafico,
                    x='mes_ano_dt',
                    y='Sell-in',
                    markers=True,
                    color_discrete_sequence=['green']
                ).data[0].update(name='Sell-in'))
                
                # Adicionar linha de Sell-out (vermelho)
                fig.add_trace(px.line(
                    df_grafico,
                    x='mes_ano_dt',
                    y='Sell-out',
                    markers=True,
                    color_discrete_sequence=['red']
                ).data[0].update(name='Sell-out'))
                
                # Atualizar o nome da linha de estoque
                fig.data[0].name = 'Estoque por Produto e Grupo'
                
                # Configurar hover personalizado para cada linha
                fig.data[0].hovertemplate = '<b>Estoque por Produto e Grupo</b><br>' + \
                                          'Período: %{x}<br>' + \
                                          'Valor: %{y:,.0f}<br>' + \
                                          '<extra></extra>'
                
                fig.data[1].hovertemplate = '<b>Sell-in</b><br>' + \
                                          'Período: %{x}<br>' + \
                                          'Valor: %{y:,.0f}<br>' + \
                                          '<extra></extra>'
                
                fig.data[2].hovertemplate = '<b>Sell-out</b><br>' + \
                                          'Período: %{x}<br>' + \
                                          'Valor: %{y:,.0f}<br>' + \
                                          '<extra></extra>'
                
                fig.update_layout(
                    xaxis_title='Período',
                    yaxis_title='Quantidade',
                    height=400,
                    legend=dict(
                        yanchor="top",
                        y=0.99,
                        xanchor="left",
                        x=0.01
                    ),
                    hovermode='x unified'  # Mostra todos os valores no mesmo ponto
                )
                st.plotly_chart(fig, width='stretch')

        # Ordenar por mês/ano, farmácia e produto
        df_tabela = df_filtered.sort_values(['mes_ano_dt', 'Grupo', 'Descrição'])

        # Exibir tabela (com as 5 colunas principais)
        st.dataframe(
            df_tabela[['mes_ano_dt', 'Grupo', 'Descrição', 'Sell-in', 'Sell-out', 'Diferença']],
            width='stretch',
            height=600, 
            column_config={
                "mes_ano_dt": st.column_config.DateColumn(
                    "Mês/Ano",
                    format="MM-YYYY" 
                )
            }
        )

        # Informações na sidebar
        st.sidebar.markdown("---")
        st.sidebar.header("📊 Resumo")

        st.sidebar.info(f"""
        **Dados filtrados:**
        - Grupos: {df_filtered['Grupo'].nunique()}
        - Produtos: {df_filtered['Descrição'].nunique()}
        - Total registros: {len(df_filtered)}
        - Período: {df_filtered['mes_ano_dt'].min().strftime('%d-%m-%Y')} a {df_filtered['mes_ano_dt'].max().strftime('%d-%m-%Y')}
        """)

    # ==================== ABA 2: GIRO DE ESTOQUE (VAZIA) ====================
    with tab2:
        st.header("Giro de Estoque")
        st.info("Esta funcionalidade será implementada em breve.")


if __name__ == "__main__":
    main()