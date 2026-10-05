import pandas as pd


# ============================================================
# CONFIGURAÇÕES
# ============================================================

ARQUIVO = "Teste_Monetização_-_Ad_Monetization_Engineering_Intern.xlsx"
ABA = "database"

# Thresholds de queda
THRESHOLD_RECEITA = -3          # %
THRESHOLD_IMPRESSOES = -3       # %
THRESHOLD_FILL_RATE = -0.2      # pontos percentuais
THRESHOLD_CPM = -5              # %

# Dimensões que serão monitoradas
DIMENSOES = [
    "Ad Network",
    "Platform",
    "Country",
    "Ad Type"
]


# ============================================================
# LEITURA DA BASE
# ============================================================

print("\nLendo base de dados...")

df = pd.read_excel(
    ARQUIVO,
    sheet_name=ABA
)

# Garantir que a coluna Day seja uma data
df["Day"] = pd.to_datetime(df["Day"])

# Ordenar os dados
df = df.sort_values("Day")


# ============================================================
# FUNÇÃO PARA CALCULAR MÉTRICAS
# ============================================================

def calcular_metricas(dados, agrupamento):

    resultado = dados.groupby(agrupamento).agg(
        Attempts=("Attempts", "sum"),
        Responses=("Responses", "sum"),
        Impressions=("Impressions", "sum"),
        Revenue=("Est. Revenue", "sum")
    ).reset_index()

    # --------------------------------------------------------
    # Fill Rate
    # --------------------------------------------------------

    resultado["Fill Rate"] = 0.0

    resultado.loc[
        resultado["Attempts"] > 0,
        "Fill Rate"
    ] = (
        resultado.loc[
            resultado["Attempts"] > 0,
            "Responses"
        ]
        /
        resultado.loc[
            resultado["Attempts"] > 0,
            "Attempts"
        ]
    )

    # --------------------------------------------------------
    # CPM
    # --------------------------------------------------------

    resultado["CPM"] = 0.0

    resultado.loc[
        resultado["Impressions"] > 0,
        "CPM"
    ] = (
        resultado.loc[
            resultado["Impressions"] > 0,
            "Revenue"
        ]
        /
        resultado.loc[
            resultado["Impressions"] > 0,
            "Impressions"
        ]
        * 1000
    )

    return resultado


# ============================================================
# ALERTAS
# ============================================================

alertas = []


def adicionar_alerta(
    data,
    nivel,
    dimensao,
    valor,
    metrica,
    atual,
    anterior=None,
    variacao=None,
    motivo=""
):

    alertas.append({
        "Data": data,
        "Nível": nivel,
        "Dimensão": dimensao,
        "Valor": valor,
        "Métrica": metrica,
        "Valor Atual": atual,
        "Valor Anterior": anterior,
        "Variação": variacao,
        "Motivo": motivo
    })


# ============================================================
# 1. MONITORAMENTO DO APP X COMO UM TODO
# ============================================================

print("Analisando performance geral do App X...")

diario = calcular_metricas(
    df,
    ["Day"]
)

diario = diario.sort_values("Day")


for i in range(1, len(diario)):

    atual = diario.iloc[i]
    anterior = diario.iloc[i - 1]

    data = atual["Day"].date()

    # --------------------------------------------------------
    # VARIAÇÃO DA RECEITA
    # --------------------------------------------------------

    if anterior["Revenue"] > 0:

        variacao = (
            (atual["Revenue"] - anterior["Revenue"])
            / anterior["Revenue"]
            * 100
        )

        if variacao < THRESHOLD_RECEITA:

            adicionar_alerta(
                data,
                "ALERTA",
                "App X",
                "Geral",
                "Receita",
                atual["Revenue"],
                anterior["Revenue"],
                variacao,
                "Queda relevante na receita"
            )

    # --------------------------------------------------------
    # VARIAÇÃO DAS IMPRESSÕES
    # --------------------------------------------------------

    if anterior["Impressions"] > 0:

        variacao = (
            (atual["Impressions"] - anterior["Impressions"])
            / anterior["Impressions"]
            * 100
        )

        if variacao < THRESHOLD_IMPRESSOES:

            adicionar_alerta(
                data,
                "ALERTA",
                "App X",
                "Geral",
                "Impressões",
                atual["Impressions"],
                anterior["Impressions"],
                variacao,
                "Queda relevante nas impressões"
            )

    # --------------------------------------------------------
    # VARIAÇÃO DO FILL RATE
    # --------------------------------------------------------

    variacao = (
        atual["Fill Rate"] - anterior["Fill Rate"]
    ) * 100

    if variacao < THRESHOLD_FILL_RATE:

        adicionar_alerta(
            data,
            "ALERTA",
            "App X",
            "Geral",
            "Fill Rate",
            atual["Fill Rate"] * 100,
            anterior["Fill Rate"] * 100,
            variacao,
            "Queda relevante no Fill Rate"
        )

    # --------------------------------------------------------
    # VARIAÇÃO DO CPM
    # --------------------------------------------------------

    if anterior["CPM"] > 0:

        variacao = (
            (atual["CPM"] - anterior["CPM"])
            / anterior["CPM"]
            * 100
        )

        if variacao < THRESHOLD_CPM:

            adicionar_alerta(
                data,
                "ALERTA",
                "App X",
                "Geral",
                "CPM",
                atual["CPM"],
                anterior["CPM"],
                variacao,
                "Queda relevante no CPM"
            )


# ============================================================
# 2. MONITORAMENTO DAS DIMENSÕES
# ============================================================

for dimensao in DIMENSOES:

    print(f"Analisando {dimensao}...")

    dados = calcular_metricas(
        df,
        ["Day", dimensao]
    )

    valores = dados[dimensao].dropna().unique()

    for valor in valores:

        historico = dados[
            dados[dimensao] == valor
        ].sort_values("Day")

        # ----------------------------------------------------
        # ALERTAS DE ZERO
        # ----------------------------------------------------

        for i in range(len(historico)):

            atual = historico.iloc[i]

            data = atual["Day"].date()

            # ------------------------------------------------
            # IMPRESSÕES = 0
            # ------------------------------------------------

            if atual["Impressions"] == 0:

                anterior = None

                if i > 0:
                    anterior = historico.iloc[i - 1]

                # Se tinha impressões anteriormente,
                # o alerta é mais crítico
                if (
                    anterior is not None
                    and anterior["Impressions"] > 0
                ):

                    adicionar_alerta(
                        data,
                        "CRÍTICO",
                        dimensao,
                        valor,
                        "Impressões",
                        0,
                        anterior["Impressions"],
                        -100,
                        "A dimensão tinha impressões no dia anterior e passou para zero"
                    )

                else:

                    adicionar_alerta(
                        data,
                        "ATENÇÃO",
                        dimensao,
                        valor,
                        "Impressões",
                        0,
                        motivo="Dimensão apresentou zero impressões"
                    )

            # ------------------------------------------------
            # RECEITA = 0
            # ------------------------------------------------

            if atual["Revenue"] == 0:

                anterior = None

                if i > 0:
                    anterior = historico.iloc[i - 1]

                if (
                    anterior is not None
                    and anterior["Revenue"] > 0
                ):

                    adicionar_alerta(
                        data,
                        "CRÍTICO",
                        dimensao,
                        valor,
                        "Receita",
                        0,
                        anterior["Revenue"],
                        -100,
                        "A dimensão tinha receita no dia anterior e passou para zero"
                    )

                else:

                    adicionar_alerta(
                        data,
                        "ATENÇÃO",
                        dimensao,
                        valor,
                        "Receita",
                        0,
                        motivo="Dimensão apresentou receita igual a zero"
                    )

            # ------------------------------------------------
            # RESPONSES = 0
            # ------------------------------------------------

            if (
                atual["Responses"] == 0
                and atual["Attempts"] > 0
            ):

                adicionar_alerta(
                    data,
                    "ATENÇÃO",
                    dimensao,
                    valor,
                    "Responses",
                    0,
                    motivo="Existem oportunidades de anúncio, mas nenhuma resposta"
                )

        # ----------------------------------------------------
        # COMPARAÇÃO DIA A DIA
        # ----------------------------------------------------

        for i in range(1, len(historico)):

            atual = historico.iloc[i]
            anterior = historico.iloc[i - 1]

            data = atual["Day"].date()

            # -----------------------------------------------
            # RECEITA
            # -----------------------------------------------

            if anterior["Revenue"] > 0:

                variacao = (
                    (atual["Revenue"] - anterior["Revenue"])
                    / anterior["Revenue"]
                    * 100
                )

                if (
                    variacao < THRESHOLD_RECEITA
                    and atual["Revenue"] > 0
                ):

                    adicionar_alerta(
                        data,
                        "ALERTA",
                        dimensao,
                        valor,
                        "Receita",
                        atual["Revenue"],
                        anterior["Revenue"],
                        variacao,
                        "Queda relevante na receita"
                    )

            # -----------------------------------------------
            # IMPRESSÕES
            # -----------------------------------------------

            if anterior["Impressions"] > 0:

                variacao = (
                    (atual["Impressions"] - anterior["Impressions"])
                    / anterior["Impressions"]
                    * 100
                )

                if (
                    variacao < THRESHOLD_IMPRESSOES
                    and atual["Impressions"] > 0
                ):

                    adicionar_alerta(
                        data,
                        "ALERTA",
                        dimensao,
                        valor,
                        "Impressões",
                        atual["Impressions"],
                        anterior["Impressions"],
                        variacao,
                        "Queda relevante nas impressões"
                    )

            # -----------------------------------------------
            # FILL RATE
            # -----------------------------------------------

            variacao = (
                atual["Fill Rate"]
                - anterior["Fill Rate"]
            ) * 100

            if variacao < THRESHOLD_FILL_RATE:

                adicionar_alerta(
                    data,
                    "ALERTA",
                    dimensao,
                    valor,
                    "Fill Rate",
                    atual["Fill Rate"] * 100,
                    anterior["Fill Rate"] * 100,
                    variacao,
                    "Queda relevante no Fill Rate"
                )

            # -----------------------------------------------
            # CPM
            # -----------------------------------------------

            if anterior["CPM"] > 0:

                variacao = (
                    (atual["CPM"] - anterior["CPM"])
                    / anterior["CPM"]
                    * 100
                )

                if (
                    variacao < THRESHOLD_CPM
                    and atual["CPM"] > 0
                ):

                    adicionar_alerta(
                        data,
                        "ALERTA",
                        dimensao,
                        valor,
                        "CPM",
                        atual["CPM"],
                        anterior["CPM"],
                        variacao,
                        "Queda relevante no CPM"
                    )


# ============================================================
# 3. ORGANIZAÇÃO DOS ALERTAS
# ============================================================

resultado = pd.DataFrame(alertas)


if resultado.empty:

    print("\n======================================")
    print("NENHUM ALERTA ENCONTRADO")
    print("======================================")

else:

    # Ordenar primeiro pelos mais graves
    ordem_nivel = {
        "CRÍTICO": 0,
        "ALERTA": 1,
        "ATENÇÃO": 2
    }

    resultado["Ordem"] = (
        resultado["Nível"]
        .map(ordem_nivel)
    )

    resultado = resultado.sort_values(
        ["Data", "Ordem"]
    )

    resultado = resultado.drop(
        columns=["Ordem"]
    )

    # --------------------------------------------------------
    # FORMATAÇÃO
    # --------------------------------------------------------

    pd.set_option(
        "display.max_rows",
        None
    )

    pd.set_option(
        "display.max_columns",
        None
    )

    pd.set_option(
        "display.width",
        200
    )

    print("\n")
    print("======================================")
    print("     ALERTAS DE PERFORMANCE")
    print("======================================\n")

    print(
        resultado.to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # SALVAR RESULTADO
    # --------------------------------------------------------

    resultado.to_excel(
        "alertas_performance.xlsx",
        index=False
    )

    print("\n")
    print("======================================")
    print("Arquivo gerado:")
    print("alertas_performance.xlsx")
    print("======================================")