"""Autenticação Microsoft Entra e acesso ao container Azure Blob Storage.

Por que Azure Blob Storage como camada alternativa de armazenamento bronze?
- SQL Server tem custo por storage e por operação de escrita.
- Azure Blob Storage é mais barato para armazenar snapshots brutos (JSON/CSV)
  que não precisam de queries SQL — apenas de recuperação por chave.
- Este módulo é usado como complemento ao bronze SQL Server: pode armazenar
  os JSONs brutos das APIs enquanto o SQL Server recebe apenas os campos
  estruturados necessários para transformação.

Autenticação via Service Principal (Microsoft Entra ID / Azure AD):
- Mais seguro que chave de storage (não expõe acesso a toda conta).
- Funciona em CI/CD sem interação humana.
- Requer: AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET.
"""

import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Path para o .env na raiz do projeto.
# parents[1]: azure_blob.py → bronze/ → projeto_5/ → .env
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def conectar_azure_blob() -> Any:
    """Autentica com Service Principal, valida o container e o retorna.

    As variáveis são lidas do ambiente ou do `.env` compartilhado em `projeto_5`.
    Nenhum segredo ou detalhe de exceção do SDK é registrado em log.

    Estratégia de verificação de conectividade:
    get_container_properties() faz uma requisição HTTP ao Azure antes de
    retornar o container client. Isso garante que falhas de rede, permissão
    ou container inexistente sejam detectadas aqui, não na primeira operação.

    Returns:
        azure.storage.blob.ContainerClient: cliente autenticado e validado.

    Raises:
        RuntimeError: Variáveis ausentes, falha de autenticação, container não
            encontrado, permissão negada ou falha de rede — sem expor segredos.
    """
    # load_dotenv: carrega variáveis sem sobrescrever as do ambiente (CI tem prioridade).
    load_dotenv(ENV_FILE)

    # Verifica todas as variáveis obrigatórias antes de tentar conectar.
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

    # Nome do container: padrão "vigia-bronze" se não configurado.
    # Containers Azure devem ter nomes em lowercase com hífens.
    container_name = os.getenv("AZURE_STORAGE_CONTAINER", "vigia-bronze")

    # Importação local: se o SDK Azure não estiver instalado, o erro é claro.
    # requirements.txt do bronze inclui azure-identity e azure-storage-blob.
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
        # ClientSecretCredential: autentica com client_id + client_secret do Service Principal.
        # O token OAuth2 é obtido do endpoint da Microsoft e renovado automaticamente.
        credential = ClientSecretCredential(
            tenant_id=os.environ["AZURE_TENANT_ID"],
            client_id=os.environ["AZURE_CLIENT_ID"],
            client_secret=os.environ["AZURE_CLIENT_SECRET"],
        )
        # BlobServiceClient: cliente da conta de storage (nível de conta, não de container).
        service = BlobServiceClient(
            account_url=os.environ["AZURE_STORAGE_ACCOUNT_URL"],
            credential=credential,
        )
        # get_container_client: referência ao container específico.
        container = service.get_container_client(container_name)
        # get_container_properties: chamada HTTP de validação — confirma que o container
        # existe e que o Service Principal tem permissão de leitura.
        container.get_container_properties()
        logger.info("Container Azure acessível: %s", container_name)
        return container

    except ClientAuthenticationError:
        # Token inválido ou Service Principal sem permissão no tenant.
        logger.error("Falha de autenticação Microsoft Entra no Azure.")
        raise RuntimeError(
            "Autenticação Azure falhou. Confira Tenant ID, Client ID e Secret."
        ) from None

    except HttpResponseError as error:
        # Categoriza erros HTTP comuns: 403 (permissão) e 404 (container não existe).
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
        # Erros de rede: DNS, TLS, timeout, conexão recusada.
        logger.error("Falha de conexão com Azure Blob Storage.")
        raise RuntimeError(
            "Não foi possível conectar ao Azure Blob Storage. Confira a URL e a rede."
        ) from None

    except Exception:
        # Captura exceções inesperadas do SDK sem expor stack trace com segredos.
        logger.error("Falha inesperada ao inicializar o cliente Azure Blob.")
        raise RuntimeError("Falha inesperada ao inicializar o cliente Azure Blob.") from None


class AzureBlobStorage:
    """Adaptador de upload usado pelo pipeline Bronze já existente.

    Encapsula o container client em uma interface simples de upload.
    O construtor conecta imediatamente — falhas de autenticação aparecem
    na criação do objeto, não no primeiro upload.
    """

    def __init__(self):
        # conectar_azure_blob: valida autenticação e acesso ao container.
        self.container = conectar_azure_blob()

    def upload(self, blob_name: str, content: bytes) -> None:
        """Cria um blob sem substituir um objeto já existente.

        Por que overwrite=False?
        O bronze é imutável: um snapshot já armazenado não deve ser sobrescrito.
        Se o blob já existe, o SDK lança BlobAlreadyExistsError — tratado
        pelo chamador se necessário.

        Args:
            blob_name: Caminho no container (ex: "openmeteo/2026-11-15T12.json").
            content: Bytes do conteúdo a armazenar.

        Raises:
            Exception: Qualquer falha de rede ou permissão do SDK Azure.
        """
        try:
            self.container.get_blob_client(blob_name).upload_blob(
                content, overwrite=False  # imutabilidade: não sobrescreve snapshots existentes
            )
            logger.info("Upload Azure concluído: %s", blob_name)
        except Exception as error:
            logger.error(
                "Falha no upload Azure para %s (tipo=%s).",
                blob_name,
                type(error).__name__,
            )
            raise
