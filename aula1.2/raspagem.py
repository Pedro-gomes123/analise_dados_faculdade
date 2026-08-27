from curl_cffi import requests
from bs4 import BeautifulSoup as bs
from urllib.parse import urljoin
import os


URL = "https://dados.recife.pe.gov.br/dataset/?groups=saude&tags=samu"

PASTA_DESTINO = "/Users/pedrodecarvalhogomes/klaus/aula_dados/aula1.2"


def criar_sessao():

    sessao = requests.Session(
        impersonate="chrome"
    )

    header = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/149.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,"
                  "application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    }

    sessao.headers.update(header)

    return sessao


def extrair(url):

    sessao = criar_sessao()

    requisicao = sessao.get(url)

    requisicao.raise_for_status()

    site = bs(
        requisicao.text,
        "html.parser"
    )

    return site


def encontrar_datasets():

    site = extrair(URL)

    datasets = []

    for link in site.select("h2 a"):

        nome = link.get_text(
            " ",
            strip=True
        )

        href = link.get("href")

        if not href:
            continue

        datasets.append({
            "nome": nome,
            "url": urljoin(URL, href)
        })

    return datasets


def encontrar_csv(url_dataset):

    site = extrair(url_dataset)

    recursos = []

    # Todos os links da página
    for link in site.find_all("a"):

        href = link.get("href")

        if not href:
            continue

        texto = link.get_text(
            " ",
            strip=True
        ).lower()

        href_lower = href.lower()

        # Procuramos o recurso CSV
        if (
            ".csv" in href_lower
            or "csv" in texto
        ):

            url_csv = urljoin(
                url_dataset,
                href
            )

            recursos.append(url_csv)

    return list(dict.fromkeys(recursos))


def baixar_arquivo(url_csv, nome_arquivo):

    sessao = criar_sessao()

    resposta = sessao.get(
        url_csv,
        timeout=60
    )

    resposta.raise_for_status()

    caminho = os.path.join(
        PASTA_DESTINO,
        nome_arquivo
    )

    with open(
        caminho,
        "wb"
    ) as arquivo:

        arquivo.write(
            resposta.content
        )

    print(f"Baixado: {caminho}")


def main():

    os.makedirs(
        PASTA_DESTINO,
        exist_ok=True
    )

    datasets = encontrar_datasets()

    print(
        f"{len(datasets)} datasets encontrados.\n"
    )

    for dataset in datasets:

        nome_dataset = dataset["nome"]

        print(
            f"Processando: {nome_dataset}"
        )

        csvs = encontrar_csv(
            dataset["url"]
        )

        if not csvs:

            print(
                "  Nenhum CSV encontrado.\n"
            )

            continue

        for i, url_csv in enumerate(csvs):

            # extrai o ano do dataset
            ano = nome_dataset.split()[-1]

            nome_arquivo = f"samu_{ano}_{i + 1}.csv"

            try:

                baixar_arquivo(
                    url_csv,
                    nome_arquivo
                )

            except Exception as erro:

                print(
                    f"  Erro ao baixar: {erro}"
                )

        print()


if __name__ == "__main__":

    main()