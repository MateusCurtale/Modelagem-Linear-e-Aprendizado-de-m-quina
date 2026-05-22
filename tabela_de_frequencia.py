"""
Cria tabelas de frequencia para uma variavel quantitativa discreta e
uma variavel quantitativa continua.

Uso:
    python tabela_de_frequencia.py
    python tabela_de_frequencia.py caminho/para/outra_base.csv
"""

from pathlib import Path
import math
import sys

import pandas as pd


# Define o arquivo CSV usado quando nenhum caminho e informado no terminal.
CAMINHO_PADRAO = Path(__file__).with_name("planilha_goodwe.csv")

# Escolhe uma variavel quantitativa discreta: valores inteiros contaveis.
VARIAVEL_DISCRETA = "Uso Médio (usuários/dia)"

# Escolhe uma variavel quantitativa continua: valor numerico que pode variar em escala decimal.
VARIAVEL_CONTINUA = "Custo (USD/kWh)"


def carregar_base(caminho_arquivo):
    """Le o arquivo CSV e devolve os dados em um DataFrame do pandas."""
    caminho_arquivo = Path(caminho_arquivo)

    # Interrompe o programa com uma mensagem clara se o arquivo nao existir.
    if not caminho_arquivo.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {caminho_arquivo}")

    return pd.read_csv(caminho_arquivo)


def validar_colunas(base, colunas):
    """Confere se as colunas escolhidas realmente existem na base."""
    colunas_faltantes = [coluna for coluna in colunas if coluna not in base.columns]

    # Mostra as colunas disponiveis para facilitar a correcao do nome.
    if colunas_faltantes:
        colunas_disponiveis = ", ".join(base.columns)
        raise ValueError(
            f"Coluna(s) nao encontrada(s): {colunas_faltantes}\n"
            f"Colunas disponiveis: {colunas_disponiveis}"
        )


def preparar_coluna_numerica(base, coluna):
    """Converte uma coluna para numero e remove valores vazios ou invalidos."""
    dados = pd.to_numeric(base[coluna], errors="coerce").dropna()

    # A tabela de frequencia precisa de pelo menos um valor numerico valido.
    if dados.empty:
        raise ValueError(f"A coluna '{coluna}' nao possui valores numericos validos.")

    return dados


def criar_tabela_discreta(base, coluna):
    """Monta a tabela de frequencia para a variavel quantitativa discreta."""
    dados = preparar_coluna_numerica(base, coluna)

    # Conta quantas vezes cada valor aparece e ordena do menor para o maior.
    tabela = (
        dados.value_counts()
        .sort_index()
        .rename_axis(coluna)
        .reset_index(name="fi")
    )

    # Calcula frequencia relativa, percentual e frequencias acumuladas.
    total = tabela["fi"].sum()
    tabela["fr"] = (tabela["fi"] / total).round(4)
    tabela["%"] = (tabela["fr"] * 100).round(2)
    tabela["Fi"] = tabela["fi"].cumsum()
    tabela["% acumulado"] = ((tabela["Fi"] / total) * 100).round(2)

    return tabela, dados


def calcular_quantidade_classes(total_registros):
    """Calcula a quantidade de classes pela regra de Sturges."""
    if total_registros <= 1:
        return 1

    return math.ceil(1 + 3.322 * math.log10(total_registros))


def formatar_intervalo(intervalo):
    """Deixa cada intervalo da tabela continua mais legivel."""
    return f"{intervalo.left:.2f} a {intervalo.right:.2f}"


def criar_tabela_continua(base, coluna):
    """Monta a tabela de frequencia para a variavel quantitativa continua."""
    dados = preparar_coluna_numerica(base, coluna)

    # A regra de Sturges cria uma quantidade equilibrada de classes.
    quantidade_classes = calcular_quantidade_classes(len(dados))

    # Agrupa os valores numericos em intervalos, pois variaveis continuas
    # costumam ter muitos valores diferentes.
    classes = pd.cut(dados, bins=quantidade_classes, include_lowest=True)

    # Conta os valores em cada intervalo e mantem a ordem natural das classes.
    tabela = (
        classes.value_counts()
        .sort_index()
        .rename_axis("Classe")
        .reset_index(name="fi")
    )

    # Calcula frequencia relativa, percentual e frequencias acumuladas.
    total = tabela["fi"].sum()
    tabela["Classe"] = tabela["Classe"].apply(formatar_intervalo)
    tabela["fr"] = (tabela["fi"] / total).round(4)
    tabela["%"] = (tabela["fr"] * 100).round(2)
    tabela["Fi"] = tabela["fi"].cumsum()
    tabela["% acumulado"] = ((tabela["Fi"] / total) * 100).round(2)

    return tabela, dados


def gerar_insights_discreta(tabela, dados, coluna):
    """Gera dois comentarios interpretando a tabela da variavel discreta."""
    maior_frequencia = tabela["fi"].max()
    valores_moda = tabela.loc[tabela["fi"] == maior_frequencia, coluna].tolist()
    percentual_moda = (maior_frequencia / len(dados)) * 100
    mediana = dados.median()

    # Insight 1: identifica o(s) valor(es) mais frequente(s) da variavel discreta.
    if len(valores_moda) == 1:
        insight_moda = (
            f"# Insight 1: O valor mais frequente de '{coluna}' é "
            f"{valores_moda[0]:.0f}, presente em {maior_frequencia} registros "
            f"({percentual_moda:.2f}% da base)."
        )
    else:
        valores_formatados = ", ".join(f"{valor:.0f}" for valor in valores_moda)
        insight_moda = (
            f"# Insight 1: Os valores mais frequentes de '{coluna}' são "
            f"{valores_formatados}, cada um com {maior_frequencia} registros "
            f"({percentual_moda:.2f}% da base)."
        )

    # Insight 2: usa a mediana para resumir a distribuicao dos valores discretos.
    insight_mediana = (
        f"# Insight 2: A mediana de '{coluna}' é {mediana:.0f}; isso indica que "
        f"aproximadamente metade dos registros possui até {mediana:.0f} usos por dia."
    )

    return [insight_moda, insight_mediana]


def gerar_insights_continua(tabela, dados, coluna):
    """Gera dois comentarios interpretando a tabela da variavel continua."""
    classe_mais_frequente = tabela.loc[tabela["fi"].idxmax()]
    media = dados.mean()
    mediana = dados.median()

    # Insight 1: destaca a faixa de valores com maior concentracao de registros.
    insight_classe = (
        f"# Insight 1: A classe mais frequente de '{coluna}' é "
        f"{classe_mais_frequente['Classe']}, com {classe_mais_frequente['fi']} "
        f"registros ({classe_mais_frequente['%']:.2f}% da base)."
    )

    # Insight 2: compara media e mediana para observar a direcao da distribuicao.
    # A tolerancia evita interpretar como diferenca relevante valores quase iguais.
    diferenca = media - mediana
    if abs(diferenca) <= 0.005:
        interpretacao = (
            "a media e a mediana ficaram praticamente iguais, sugerindo uma "
            "distribuicao equilibrada de preços"
        )
    elif diferenca > 0:
        interpretacao = "a media ficou acima da mediana, sugerindo alguns valores mais altos"
    else:
        interpretacao = "a media ficou abaixo da mediana, sugerindo alguns valores mais baixos"

    insight_media = (
        f"# Insight 2: A media de '{coluna}' e {media:.3f}, enquanto a mediana "
        f"e {mediana:.3f}; {interpretacao}."
    )

    return [insight_classe, insight_media]


def imprimir_resultado(titulo, tabela, insights):
    """Exibe uma tabela de frequencia seguida dos insights em formato de comentario."""
    print("\n" + titulo)
    print("-" * len(titulo))
    print(tabela.to_string(index=False))
    print()

    # Os insights sao impressos com # para aparecerem como comentarios.
    for insight in insights:
        print(insight)


def main():
    """Executa o fluxo completo do programa."""
    # Se o usuario informar um caminho no terminal, usa esse arquivo.
    # Caso contrario, usa o CSV padrao que esta na mesma pasta do script.
    caminho_base = Path(sys.argv[1]) if len(sys.argv) > 1 else CAMINHO_PADRAO

    # Carrega e valida a base antes de gerar as tabelas.
    base = carregar_base(caminho_base)
    validar_colunas(base, [VARIAVEL_DISCRETA, VARIAVEL_CONTINUA])

    # Cria a tabela e os insights da variavel quantitativa discreta.
    tabela_discreta, dados_discretos = criar_tabela_discreta(base, VARIAVEL_DISCRETA)
    insights_discretos = gerar_insights_discreta(
        tabela_discreta,
        dados_discretos,
        VARIAVEL_DISCRETA,
    )

    # Cria a tabela e os insights da variavel quantitativa continua.
    tabela_continua, dados_continuos = criar_tabela_continua(base, VARIAVEL_CONTINUA)
    insights_continuos = gerar_insights_continua(
        tabela_continua,
        dados_continuos,
        VARIAVEL_CONTINUA,
    )

    # Mostra os resultados finais no terminal.
    imprimir_resultado(
        f"Tabela de frequencia - variavel discreta: {VARIAVEL_DISCRETA}",
        tabela_discreta,
        insights_discretos,
    )
    imprimir_resultado(
        f"Tabela de frequencia - variavel continua: {VARIAVEL_CONTINUA}",
        tabela_continua,
        insights_continuos,
    )


if __name__ == "__main__":
    main()
