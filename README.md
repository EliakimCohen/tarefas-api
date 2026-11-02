# Tarefas API

API JSON para gerenciar tarefas pessoais com Django e SQLite. Cada usuário pode criar, listar, consultar, concluir e remover as próprias tarefas.

**Python 3.12+ · Django 5.2 · SQLite · autenticação por sessão · proteção CSRF · testes de integração**

## Execute localmente

Dentro desta pasta:

```bash
python -m venv .venv
```

Ative o ambiente: `source .venv/bin/activate` no Linux/macOS ou `.venv\Scripts\activate` no terminal do Windows.

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

O comando `createsuperuser` permite criar uma conta para a demonstração sem implementar cadastro público. A API não tem painel administrativo. Abra `http://127.0.0.1:8000/api/health/` para verificar o servidor.

Em outro terminal, com o ambiente ativado:

```bash
python examples/demo.py
```

Informe o usuário e a senha criados. O cliente usa apenas a biblioteca padrão: obtém um token CSRF, faz login, cria uma tarefa, conclui, lista, remove a tarefa de demonstração e encerra a sessão.

## Endpoints

| Método | Rota | Resultado |
| --- | --- | --- |
| GET | `/api/health/` | Estado do serviço, público |
| GET | `/api/csrf/` | Token CSRF e cookie, público |
| POST | `/api/login/` | Login com `username` e `password` |
| POST | `/api/logout/` | Encerra sessão |
| GET | `/api/tasks/` | Lista paginada de tarefas do usuário |
| POST | `/api/tasks/` | Cria uma tarefa |
| GET | `/api/tasks/1/` | Consulta uma tarefa |
| PATCH | `/api/tasks/1/` | Atualiza título e/ou conclusão |
| DELETE | `/api/tasks/1/` | Remove uma tarefa |

Corpo de criação: `{"title": "Estudar Python", "completed": false}`. O título tem de 1 a 160 caracteres. `completed` aceita booleanos JSON, sem conversão de strings. Campos desconhecidos são rejeitados. Use `Content-Type: application/json`.

Filtros: `/api/tasks/?completed=true&page=1`. Cada página contém até 20 itens, ordenados pelos IDs mais recentes. A lista retorna `count`, `page`, `page_size` e `results`.

Clientes devem preservar os cookies e enviar `X-CSRFToken` nas operações de escrita, incluindo login. O login retorna um **novo** `csrfToken`, que substitui o anterior.

Respostas: 201 ao criar, 204 ao remover ou sair, 400 para dados inválidos, 401 para acesso sem sessão ou credenciais incorretas, 403 para falha de CSRF, 404 para tarefa ausente ou de outro usuário e 405 para método não permitido.

## Testes

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Cobrem CRUD, isolamento entre usuários, paginação, filtros, campos inválidos e um fluxo de autenticação com verificação real de CSRF. O banco de testes é separado do banco local.

## Organização e decisões

- `config/`: configurações e rotas.
- `tasks/models.py`: entidade persistida e serialização explícita.
- `tasks/views.py`: validação, autenticação e respostas HTTP.
- `tasks/migrations/`: histórico do esquema do banco.
- `tasks/tests.py`: testes de integração.
- `examples/demo.py`: cliente executável com cookies e CSRF.

O projeto usa recursos do próprio Django para exercitar fundamentos HTTP antes de adicionar Django REST Framework. A consulta sempre filtra pelo proprietário autenticado e nunca aceita `owner` no corpo da requisição. Senhas são tratadas pelo sistema de autenticação do Django.

## Limites e próximos passos

Configuração de **desenvolvimento local**, com DEBUG ligado e chave pública apenas para estudo. Antes de publicar um serviço, configure segredo via ambiente (`DJANGO_SECRET_KEY`), desative DEBUG (`DJANGO_DEBUG=0`), configure hosts, HTTPS, servidor WSGI/ASGI, política de senhas e proteção contra tentativas repetidas de login. Não há recuperação de senha, cadastro público, rate limiting ou interface gráfica.

Para evoluir: adicionar prazos, busca, documentação OpenAPI ou um front-end React. Atualize as dependências de forma periódica e execute os testes.

## Para explicar numa entrevista

1. Por que filtrar tarefas pelo usuário em todas as operações?
2. Qual é a diferença entre 401, 403 e 404?
3. Por que autenticação por cookie precisa de CSRF?
4. Por que validar todos os campos antes de gravar um PATCH?

Referências: [Django](https://docs.djangoproject.com/en/5.2/), [autenticação](https://docs.djangoproject.com/en/5.2/topics/auth/default/) e [CSRF](https://docs.djangoproject.com/en/5.2/howto/csrf/).

Projeto de estudo preparado com apoio de IA para evolução prática.
