"""Teste remoto de autenticação e upload no container privado do Azure.

Execute na pasta projeto_5 com:
    python3 -m bronze.tests.test_azure_connection
"""

import json
import logging

from bronze.azure_blob import conectar_azure_blob

logger = logging.getLogger(__name__)
BLOB_NAME = "testes/conexao_azure.json"
TEST_DOCUMENT = {
    "projeto": "VigiaClima-Recife",
    "status": "conectado",
    "camada": "bronze",
}


def validar_upload() -> bool:
    """Autentica, acessa o container e envia/verifica o JSON de teste."""
    try:
        from azure.core.exceptions import (
            ClientAuthenticationError,
            HttpResponseError,
            ResourceExistsError,
            ServiceRequestError,
            ServiceResponseError,
        )
        from azure.storage.blob import ContentSettings
    except ImportError:
        print("ERRO: instale azure-identity e azure-storage-blob.")
        return False

    try:
        container = conectar_azure_blob()
        blob = container.get_blob_client(BLOB_NAME)
        content = json.dumps(
            TEST_DOCUMENT, ensure_ascii=False, indent=2
        ).encode("utf-8")

        try:
            blob.upload_blob(
                content,
                overwrite=False,
                content_settings=ContentSettings(content_type="application/json"),
            )
            properties = blob.get_blob_properties()
            if properties.size != len(content):
                print("ERRO: o tamanho do blob não corresponde ao JSON enviado.")
                return False
            print(f"SUCESSO: JSON enviado e verificado em {BLOB_NAME}.")
            return True
        except ResourceExistsError:
            # Não sobrescreve o blob. Um re-teste só passa se o conteúdo já
            # presente for exatamente o mesmo documento de validação.
            existing = blob.download_blob().readall()
            if existing == content:
                print(f"SUCESSO: {BLOB_NAME} já existe com o conteúdo esperado.")
                return True
            print(
                f"ERRO: {BLOB_NAME} já existe com outro conteúdo; "
                "nenhum arquivo foi modificado."
            )
            return False
    except ClientAuthenticationError:
        print("ERRO: autenticação Microsoft Entra falhou; confira as credenciais.")
    except HttpResponseError as error:
        if error.status_code == 403:
            print(
                "ERRO: Azure negou o acesso; confira a função e o escopo "
                "do Service Principal."
            )
        elif error.status_code == 404:
            print("ERRO: Storage Account ou container não encontrado.")
        else:
            print(f"ERRO: resposta HTTP {error.status_code} do Azure.")
    except (ServiceRequestError, ServiceResponseError, TimeoutError, OSError):
        print("ERRO: falha de conexão com Azure Blob Storage.")
    except RuntimeError as error:
        # Mensagens próprias do módulo são higienizadas e não contêm segredos.
        print(f"ERRO: {error}")
    except Exception:
        logger.error("Falha inesperada durante o teste de upload Azure.")
        print("ERRO: falha inesperada durante o teste de upload Azure.")
    return False


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    return 0 if validar_upload() else 1


if __name__ == "__main__":
    raise SystemExit(main())
