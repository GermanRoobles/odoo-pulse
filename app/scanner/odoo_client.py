import xmlrpc.client
import socket
from typing import Any
from urllib.parse import urlparse

TIMEOUT_SECONDS = 15
PRIVATE_NETWORKS = (
    "10.", "172.16.", "172.17.", "172.18.", "172.19.", "172.20.",
    "172.21.", "172.22.", "172.23.", "172.24.", "172.25.", "172.26.",
    "172.27.", "172.28.", "172.29.", "172.30.", "172.31.", "192.168.",
    "127.", "0.", "169.254.", "::1",
)
PRIVATE_HOSTNAMES = ("localhost",)


class OdooConnectionError(Exception):
    pass


class OdooPermissionError(Exception):
    pass


def _validate_url(url: str, allow_private: bool = False) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise OdooConnectionError("La URL debe comenzar con http:// o https://")
    host = parsed.hostname or ""
    if not allow_private:
        if host in PRIVATE_HOSTNAMES:
            raise OdooConnectionError(
                "No se permiten URLs de redes privadas. "
                "Usa la URL pública de tu instancia Odoo."
            )
        for prefix in PRIVATE_NETWORKS:
            if host.startswith(prefix):
                raise OdooConnectionError(
                    "No se permiten URLs de redes privadas. "
                    "Usa la URL pública de tu instancia Odoo."
                )
    return url.rstrip("/")


class OdooClient:
    def __init__(self, url: str, db: str, username: str, password: str):
        from app.config import settings
        allow_private = settings.environment == "development"
        self.url = _validate_url(url, allow_private=allow_private)
        self.db = db
        self.username = username
        self.password = password
        self.uid = None

    def _get_proxy(self, endpoint: str) -> xmlrpc.client.ServerProxy:
        socket.setdefaulttimeout(TIMEOUT_SECONDS)
        return xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/{endpoint}")

    def authenticate(self) -> int:
        try:
            common = self._get_proxy("common")
            uid = common.authenticate(self.db, self.username, self.password, {})
            if not uid:
                raise OdooPermissionError(
                    "Credenciales incorrectas o usuario sin acceso a la base de datos indicada."
                )
            self.uid = uid
            return uid
        except OdooPermissionError:
            raise
        except ConnectionRefusedError:
            raise OdooConnectionError(
                f"No se puede conectar a {self.url}. Verifica que la URL sea correcta."
            )
        except socket.timeout:
            raise OdooConnectionError(
                f"Timeout al conectar con {self.url} (>{TIMEOUT_SECONDS}s)."
            )
        except Exception as e:
            raise OdooConnectionError(f"Error de conexión: {str(e)}")

    def execute(self, model: str, method: str, *args, **kwargs) -> Any:
        if self.uid is None:
            self.authenticate()
        try:
            models = self._get_proxy("object")
            return models.execute_kw(
                self.db, self.uid, self.password, model, method, list(args), kwargs
            )
        except socket.timeout:
            raise OdooConnectionError(f"Timeout ejecutando {model}.{method}")
        except Exception as e:
            raise OdooConnectionError(f"Error en llamada XML-RPC ({model}.{method}): {str(e)}")

    def model_exists(self, model: str) -> bool:
        try:
            result = self.execute("ir.model", "search_count", [("model", "=", model)])
            return result > 0
        except Exception:
            return False

    def count(self, model: str, domain=None) -> int:
        return self.execute(model, "search_count", domain or [])

    def search_read(self, model: str, domain: list, fields: list, limit: int = 0) -> list:
        kwargs = {"fields": fields}
        if limit:
            kwargs["limit"] = limit
        return self.execute(model, "search_read", domain, **kwargs)
