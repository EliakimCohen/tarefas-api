import json
from functools import wraps

from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token

from .models import Task


def endpoint(methods, authenticated=True):
    """Retorna erros JSON e exige autenticação nas operações privadas."""
    def decorate(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method not in methods:
                response = JsonResponse({"error": "Método não permitido."}, status=405)
                response["Allow"] = ", ".join(methods)
                return response
            if authenticated and not request.user.is_authenticated:
                return JsonResponse({"error": "Autenticação necessária."}, status=401)
            try:
                return view(request, *args, **kwargs)
            except ValueError as error:
                return JsonResponse({"error": str(error)}, status=400)
        return wrapped
    return decorate


def body(request):
    if request.content_type != "application/json":
        raise ValueError("Use Content-Type: application/json.")
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError) as error:
        raise ValueError("JSON inválido.") from error
    if not isinstance(data, dict):
        raise ValueError("O corpo deve ser um objeto JSON.")
    return data


def validate_task(data, partial=False):
    if set(data) - {"title", "completed"}:
        raise ValueError("Campos permitidos: title, completed.")
    if not partial and "title" not in data:
        raise ValueError("title é obrigatório.")
    if partial and not data:
        raise ValueError("Informe pelo menos um campo.")
    clean = {}
    if "title" in data:
        title = data["title"]
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 160:
            raise ValueError("title deve ter de 1 a 160 caracteres.")
        clean["title"] = title.strip()
    if "completed" in data:
        if type(data["completed"]) is not bool:
            raise ValueError("completed deve ser booleano.")
        clean["completed"] = data["completed"]
    return clean


def csrf_failure(request, reason=""):
    return JsonResponse({"error": "Token CSRF ausente ou inválido."}, status=403)


@endpoint(["GET"], authenticated=False)
def health(request):
    return JsonResponse({"status": "ok"})


@endpoint(["GET"], authenticated=False)
def csrf(request):
    return JsonResponse({"csrfToken": get_token(request)})


@endpoint(["POST"], authenticated=False)
def sign_in(request):
    data = body(request)
    if set(data) != {"username", "password"} or not all(isinstance(value, str) and value for value in data.values()):
        raise ValueError("Informe username e password como textos não vazios.")
    user = authenticate(request, username=data["username"], password=data["password"])
    if user is None:
        return JsonResponse({"error": "Credenciais inválidas."}, status=401)
    login(request, user)
    # O login troca o token CSRF. O cliente deve usar o novo valor.
    return JsonResponse({"username": user.username, "csrfToken": get_token(request)})


@endpoint(["POST"])
def sign_out(request):
    logout(request)
    return HttpResponse(status=204)


@endpoint(["GET", "POST"])
def tasks(request):
    if request.method == "POST":
        data = validate_task(body(request))
        task = Task.objects.create(owner=request.user, **data)
        response = JsonResponse(task.as_dict(), status=201)
        response["Location"] = f"/api/tasks/{task.pk}/"
        return response
    query = Task.objects.filter(owner=request.user)
    completed = request.GET.get("completed")
    if completed is not None:
        if completed not in ("true", "false"):
            raise ValueError("completed deve ser true ou false.")
        query = query.filter(completed=completed == "true")
    try:
        page = int(request.GET.get("page", "1"))
    except ValueError as error:
        raise ValueError("page deve ser um inteiro positivo.") from error
    if not 1 <= page <= 100000:
        raise ValueError("page deve estar entre 1 e 100000.")
    page_size = 20
    offset = (page - 1) * page_size
    return JsonResponse({"count": query.count(), "page": page, "page_size": page_size, "results": [task.as_dict() for task in query[offset:offset + page_size]]})


@endpoint(["GET", "PATCH", "DELETE"])
def task_detail(request, task_id):
    task = Task.objects.filter(pk=task_id, owner=request.user).first()
    if task is None:
        return JsonResponse({"error": "Tarefa não encontrada."}, status=404)
    if request.method == "DELETE":
        task.delete()
        return HttpResponse(status=204)
    if request.method == "PATCH":
        data = validate_task(body(request), partial=True)
        for key, value in data.items():
            setattr(task, key, value)
        task.save(update_fields=list(data))
    return JsonResponse(task.as_dict())
