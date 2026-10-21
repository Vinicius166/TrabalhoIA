# Autores: Pedro Henrique Siqueira de Paula Peixoto,
#          Rafael Dayvid de Melo Freitas,
#          Thales Henrique Marques Lázaro,
#          Vinícius Duarte de Carvalho.

# Separa, do arquivo processado, dois grupos aleatórios e diferentes de linhas:
#    Um para validação (enem_validacao.csv) e outro para teste (enem_teste.csv). As linhas sorteadas são retiradas do arquivo principal, que passa a ser a base de treino.
# Lembrando o arquivo principal é sobrescrito (sem as linhas retiradas). Por isso o script se recusa a rodar de novo 
# se o arquivo de validação ou de teste já existir, o que retiraria mais linhas por engano. Para refazer a separação, rode o pré-processamento
# de novo (ele recria o arquivo principal completo) e apague os dois arquivos gerados.

import os
import sys

import pandas as pd

PRINCIPAL = sys.argv[1] if len(sys.argv) > 1 else "enem_treino.csv"
ENEM_VALIDACAO = "enem_validacao.csv"
ENEM_TESTE = "enem_teste.csv"
N_VALIDACAO = 200_000
N_TESTE = 200_000
SEMENTE = 42          # fixa o sorteio: rodando de novo com o mesmo arquivo, sai o mesmo resultado

SEP = ";"
# Colunas guardadas como "category" para gastar muito menos memória com 3,9 milhões de linhas
CATEGORICAS = ["TP_SEXO"] + [f"Q{i:03d}" for i in range(1, 26) if i != 5]


def gravar(df, caminho):
    df.to_csv(caminho, sep=SEP, index=False, encoding="utf-8")


def main():
    for arq in (ENEM_VALIDACAO, ENEM_TESTE):
        if os.path.exists(arq):
            sys.exit(f" O arquivo {arq} já existe. A separação já foi feita; não rode de novo para não retirar mais linhas do arquivo principal (leia o aviso no topo do script).")

    dtypes = {c: "category" for c in CATEGORICAS}
    dtypes["Q005"] = "Int64"   # inteiro que aceita vazio (evita 4 virar 4.0)
    df = pd.read_csv(PRINCIPAL, sep=SEP, encoding="utf-8", dtype=dtypes)
    total = len(df)
    if total <= N_VALIDACAO + N_TESTE:
        sys.exit(f"O arquivo tem só {total:,} linhas, pouco para tirar "
                 f"{N_VALIDACAO:,} + {N_TESTE:,}.")
    print(f"{PRINCIPAL}: {total:,} linhas\n")

    # Validação: sorteio entre todas as linhas
    validacao = df.sample(n=N_VALIDACAO, random_state=SEMENTE)
    df = df.drop(index=validacao.index)
    gravar(validacao, ENEM_VALIDACAO)
    print(f"Validação: {len(validacao):,} linhas -> {ENEM_VALIDACAO} "
          f"(restam {len(df):,} no principal)\n")

    # Teste: sorteio só entre as linhas que sobraram
    teste = df.sample(n=N_TESTE, random_state=SEMENTE)
    df = df.drop(index=teste.index)
    gravar(teste, ENEM_TESTE)
    print(f"Teste: {len(teste):,} linhas -> {ENEM_TESTE} (restam {len(df):,} no principal)\n")

    # Atualiza o arquivo principal (grava num temporário e só então troca, para não perder o arquivo original se algo falhar no meio da gravação)
    temporario = PRINCIPAL + ".tmp"
    gravar(df, temporario)
    os.replace(temporario, PRINCIPAL)
    print(f"{PRINCIPAL} atualizado: {len(df):,} linhas (base de treino)\n")

    # Conferência: nenhum aluno aparece em dois arquivos
    ids = [set(validacao["NU_INSCRICAO"]), set(teste["NU_INSCRICAO"]), set(df["NU_INSCRICAO"])]
    repetidos = len(ids[0] & ids[1]) + len(ids[0] & ids[2]) + len(ids[1] & ids[2])
    print(f"Conferência: {repetidos} inscrições repetidas entre os três arquivos; "
          f"soma das linhas = {len(validacao) + len(teste) + len(df):,} (original: {total:,})")

if __name__ == "__main__":
    main()