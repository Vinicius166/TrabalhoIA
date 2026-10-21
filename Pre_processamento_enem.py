# Autores: Pedro Henrique Siqueira de Paula Peixoto,
#          Rafael Dayvid de Melo Freitas,
#          Thales Henrique Marques Lázaro,
#          Vinícius Duarte de Carvalho.

# Pega os microdados dos ENEM de 2022 e 2023 e processa eles, excluindo pessoas que não estiveram presentes em algum dia da prova, 
# também tirou as que tiverem a nota da redação zerada ou ausente, e por fim os treineiros, mantendo, 
# número de inscrição, faixa etária, sexo, cor/raça, tipo da escola que estudou e as 25 questões socioeconômicas,
# cria as colunas das faixas de sálario per capita minima e máxima usando a faixa de salários da família e quantidade de membros 
# salva tudo no mesmo arquivo csv (enem_treino.csv), junto com uma nova coluna do ano de origem da linha.

import sys

import pandas as pd 
import numpy as np

ARQUIVOS = {
    2022: "MICRODADOS_ENEM_2022.csv",
    2023: "MICRODADOS_ENEM_2023.csv",
}
if len(sys.argv) == 3:
    ARQUIVOS = {2022: sys.argv[1], 2023: sys.argv[2]}

# Colunas que vão para o arquivo final
COLUNAS = (
    ["NU_INSCRICAO", "TP_FAIXA_ETARIA", "TP_SEXO", "TP_COR_RACA", "TP_ESCOLA"]
    + [f"Q{i:03d}" for i in range(1, 26)]   # questões socioeconômicas Q001 a Q025
)

# Filtro: só quem fez todas as provas e a redação, e não é treineiro, se True, as colunas usadas no filtro são lidas, mas não vão para o arquivo final
FILTRAR_PARTICIPANTES = True
COLUNAS_FILTRO = ["IN_TREINEIRO", "NU_NOTA_REDACAO","TP_PRESENCA_CN", "TP_PRESENCA_CH", "TP_PRESENCA_LC", "TP_PRESENCA_MT"]

SALARIO_MINIMO = {2022: 1212.00, 2023: 1320.00}

LIMITES_RENDA = {
    2022: [1212, 1818, 2424, 3030, 3636, 4848, 6060, 7272, 8484, 9696,
           10908, 12120, 14544, 18180, 24240],
    2023: [1320, 1980, 2640, 3300, 3960, 5280, 6600, 7920, 9240, 10560,
           11880, 13200, 15840, 19800, 26400],
}

SAIDA = "enem_treino.csv" 

SEP, ENCODING = ";", "latin-1"   # formato dos microdados do Inep

def montar_faixas(limites):
    # Devolve letra: (mínimo, máximo) em R$. O mínimo de cada faixa é o teto da anterior A -> (0, 0). Q -> (último teto, NaN), porque 'acima de X' não tem limite máximo
    faixas = {"A": (0.0, 0.0)}
    inferior = 0.0
    for letra, teto in zip("BCDEFGHIJKLMNOP", limites):
        faixas[letra] = (inferior, float(teto))
        inferior = float(teto)
    faixas["Q"] = (inferior, np.nan)
    return faixas

def criar_renda_per_capita(df, ano):
    # Cria SAL_PER_CAPITA_MIN e SAL_PER_CAPITA_MAX: a faixa de renda familiar em salários mínimos do ano, dividida pelo número de pessoas da casa
    sm = SALARIO_MINIMO[ano]
    faixas = montar_faixas(LIMITES_RENDA[ano])
    minimo = df["Q006"].map({k: v[0] for k, v in faixas.items()})
    maximo = df["Q006"].map({k: v[1] for k, v in faixas.items()})
    pessoas = pd.to_numeric(df["Q005"], errors="coerce")
    pessoas = pessoas.where(pessoas > 0)   # 0 ou negativo vira ausente
 
    df["SAL_PER_CAPITA_MIN"] = (minimo / sm / pessoas).round(4)
    df["SAL_PER_CAPITA_MAX"] = (maximo / sm / pessoas).round(4)
    return df

def ler_colunas(caminho, colunas): 
    # vai ler as colunas,e se faltar alguma ele avisa
    cabecalho = pd.read_csv(caminho, sep=SEP, encoding=ENCODING, nrows=0).columns
    faltando = [c for c in colunas if c not in cabecalho]
    if faltando:
        raise ValueError(f"Colunas não encontradas em {caminho}: {faltando}")
    return pd.read_csv(caminho, sep=SEP, encoding=ENCODING, usecols=colunas)


def processar(ano, caminho, primeiro): 
    # separa as linhas uteis filtrando nesse primeiro momento, se a pessoa participou de todos os dias, se a redação não foi anulada e se não é treineiro
    df = ler_colunas(caminho, COLUNAS + COLUNAS_FILTRO)
    total = len(df)
 
    # Filtros: presente nas 4 provas, redação diferente de zero e não treineiro
    presente = (df[["TP_PRESENCA_CN", "TP_PRESENCA_CH", "TP_PRESENCA_LC", "TP_PRESENCA_MT"]] == 1).all(axis=1)
    redacao_ok = df["NU_NOTA_REDACAO"] > 0          # nota 0 ou ausente fica de fora
    nao_treineiro = df["IN_TREINEIRO"] == 0
    df = df[presente & redacao_ok & nao_treineiro].copy()
 
    # Renda per capita (em salários mínimos) a partir de Q006 e Q005
    df = criar_renda_per_capita(df, ano)
 
    df = df[COLUNAS + ["SAL_PER_CAPITA_MIN", "SAL_PER_CAPITA_MAX"]].copy()
    # Pandas lê Q005 como decimal (4.0); volta para inteiro (4)
    df["Q005"] = pd.to_numeric(df["Q005"], errors="coerce").astype("Int64")
    # Ano do ENEM, logo depois do número de inscrição (permite separar treino e teste depois)
    df.insert(1, "NU_ANO", ano)
 
    # O primeiro ano cria o arquivo (com cabeçalho); os seguintes são acrescentados no fim
    df.to_csv(SAIDA, sep=";", index=False, encoding="utf-8",
              mode="w" if primeiro else "a", header=primeiro)
 
    print(f"ENEM {ano}: {total:,} linhas lidas -> {len(df):,} salvas em {SAIDA} ({len(df.columns)} colunas)\n")
    return len(df)

def mostrar_faixas(ano):
    #Imprime as faixas usadas (R$ e salários mínimos) para conferir com o dicionário
    sm = SALARIO_MINIMO[ano]
    print(f"Faixas de renda {ano} (salário mínimo R$ {sm:,.2f}):")
    for letra, (mn, mx) in montar_faixas(LIMITES_RENDA[ano]).items():
        teto = "sem limite" if np.isnan(mx) else f"R$ {mx:,.2f} = {mx / sm:g} SM"
        print(f"  {letra}: de R$ {mn:,.2f} ({mn / sm:g} SM) até {teto}")
    print("\n")

if __name__ == "__main__":
    total = 0
    for i, (ano, caminho) in enumerate(ARQUIVOS.items()):
        mostrar_faixas(ano)
        total += processar(ano, caminho, primeiro=(i == 0))
    print(f"\nArquivo final: {SAIDA} com {total:,} linhas")