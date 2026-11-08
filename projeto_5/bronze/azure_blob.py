"""Autenticação Microsoft Entra e acesso ao container Azure Blob Storage."""

import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

logger = logging.getLogger(__name__)
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def conectar_azure_blob() -> Any:
    """Autentica com Service Principal, valida o container e o retorna.

    As variáveis são lidas do ambiente ou do `.env` compartilhado em `projeto_5`.
    Nenhum segredo ou detalhe de exceção do SDK é registrado.
    """
    load_dotenv(ENV_FILE)
    required = (
        "AZURE_TENANT_ID",
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
        "AZURE_STORAGE_ACCOUNT_URL",
    )
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            "Variáveis Azure ausentes: " + ", ".join(missing)
        )

    container_name = os.getenv("AZURE_STORAGE_CONTAINER", "vigia-bronze")
    try:
        from azure.core.exceptions import (
            ClientAuthenticationError,
            HttpResponseError,
            ServiceRequestError,
            ServiceResponseError,
        )
        from azure.identity import ClientSecretCredential
        from azure.storage.blob import BlobServiceClient
    except ImportError as error:
        raise RuntimeError(
            "SDKs Azure ausentes. Instale azure-identity e azure-storage-blob."
        ) from error

    credential = None
    try:
        credential = ClientSecretCredential(
            tenant_id=os.environ["AZURE_TENANT_ID"],
            client_id=os.environ["AZURE_CLIENT_ID"],
            client_secret=os.environ["AZURE_CLIENT_SECRET"],
        )
        service = BlobServiceClient(
            account_url=os.environ["AZURE_STORAGE_ACCOUNT_URL"],
            credential=credential,
        )
        container = service.get_container_client(container_name)
        container.get_container_properties()
        logger.info("Container Azure acessível: %s", container_name)
        return container
    except ClientAuthenticationError:
        logger.error("Falha de autenticação Microsoft Entra no Azure.")
        raise RuntimeError(
            "Autenticação Azure falhou. Confira Tenant ID, Client ID e Secret."
        ) from None
    except HttpResponseError as error:
        if error.status_code == 403:
            logger.error("Acesso negado ao container Azure %s.", container_name)
            message = (
                "Acesso negado ao container. Confira o escopo e a função "
                "Colaborador de Dados do Storage Blob do Service Principal."
            )
        elif error.status_code == 404:
            logger.error("Container Azure não encontrado: %s", container_name)
            message = f"Container Azure não encontrado: {container_name}."
        else:
            logger.error("Erro HTTP ao validar o container Azure (%s).", error.status_code)
            message = "Falha HTTP ao validar acesso ao container Azure."
        raise RuntimeError(message) from None
    except (ServiceRequestError, ServiceResponseError, TimeoutError, OSError):
        logger.error("Falha de conexão com Azure Blob Storage.")
        raise RuntimeError(
            "Não foi possível conectar ao Azure Blob Storage. Confira a URL e a rede."
        ) from None
    except Exception:
        logger.error("Falha inesperada ao inicializar o cliente Azure Blob.")
        raise RuntimeError("Falha inesperada ao inicializar o cliente Azure Blob.") from None


class AzureBlobStorage:
    """Adaptador de upload usado pelo pipeline Bronze já existente."""

    def __init__(self):
        self.container = conectar_azure_blob()

    def upload(self, blob_name: str, content: bytes) -> None:
        """Cria um blob sem substituir um objeto já existente."""
        try:
            self.container.get_blob_client(blob_name).upload_blob(
                content, overwrite=False
            )
            logger.info("Upload Azure concluído: %s", blob_name)
        except Exception as error:
            logger.error(
                "Falha no upload Azure para %s (tipo=%s).",
                blob_name,
                type(error).__name__,
            )
            raise
