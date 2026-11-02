"""Cliente de demonstração: python examples/demo.py (servidor local já iniciado)."""
import getpass
import json
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener


def main():
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    base = "http://127.0.0.1:8000"

    def call(path, method="GET", data=None, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-CSRFToken"] = token
        request = Request(base + path, data=json.dumps(data).encode() if data is not None else None, headers=headers, method=method)
        with opener.open(request, timeout=10) as response:
            raw = response.read()
            return json.loads(raw) if raw else None

    try:
        token = call("/api/csrf/")["csrfToken"]
        credentials = {"username": input("Usuário: "), "password": getpass.getpass("Senha: ")}
        token = call("/api/login/", "POST", credentials, token)["csrfToken"]
        task = call("/api/tasks/", "POST", {"title": "Estudar testes Django"}, token)
        print("Criada:", task)
        print("Concluída:", call(f"/api/tasks/{task['id']}/", "PATCH", {"completed": True}, token))
        print("Lista:", call("/api/tasks/?completed=true"))
        call(f"/api/tasks/{task['id']}/", "DELETE", token=token)
        call("/api/logout/", "POST", token=token)
        print("Demonstração concluída; a tarefa de exemplo foi removida.")
    except HTTPError as error:
        print(f"Erro HTTP {error.code}: {error.read().decode()}")
        return 1
    except URLError as error:
        print(f"Não foi possível acessar o servidor: {error.reason}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
