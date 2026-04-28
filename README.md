# Image Upload API

API REST para captura e armazenamento de imagens via webcam.

---

## Instalação e execução

```bash
# 1. Instalar dependências (apenas na primeira vez)
uv sync

# 2. Subir o servidor
uv run uvicorn app.main:app --reload
```

Acesse em: **http://localhost:8000**  
Documentação interativa (OpenAPI): **http://localhost:8000/docs**
Documentação interativa (ReDoc): **http://localhost:8000/redoc**

> O banco de dados (`data.db`) e a pasta de imagens (`uploads/`) são criados automaticamente na primeira execução.

---

## Estrutura do projeto

```
image_upload/
├── main.py               # Ponto de entrada (uvicorn)
├── pyproject.toml        # Dependências gerenciadas pelo uv
├── data.db               # SQLite — gerado automaticamente
├── uploads/              # Imagens salvas — gerado automaticamente
└── app/
    ├── main.py           # Instância FastAPI + CORS + static files
    ├── database.py       # Inicialização do banco e pasta de uploads
    ├── models.py         # Pydantic models (request / response)
    ├── security.py       # Validação: MIME, magic bytes, tamanho
    ├── routes/
    │   ├── sessions.py   # GET /sessions/{id}
    │   └── images.py     # POST /images · GET /sessions/{id}/images · GET /images/{id}
    └── static/
        ├── index.html    # Frontend de teste (webcam + galeria)
        ├── style.css     # Estilos do frontend
        └── app.js        # Lógica do frontend
```

---

## Endpoints

### `POST /images` — Enviar imagem

Recebe uma imagem codificada em base64 via JSON.  
**Cria a sessão automaticamente** na primeira chamada e retorna o `session_id`.

**Request**

```http
POST /images
Content-Type: application/json

{
  "image": "<base64 puro, sem prefixo data URI>",
  "mime_type": "image/jpeg"
}
```

| Campo       | Tipo                           | Obrigatório | Descrição                                    |
|-------------|--------------------------------|-------------|----------------------------------------------|
| `image`     | `string` (base64)              | ✅           | Conteúdo da imagem. O prefixo `data:image/...;base64,` é removido automaticamente se presente. |
| `mime_type` | `"image/jpeg"` \| `"image/png"` | ✅           | Tipo MIME da imagem.                         |

**Response `201 Created`**

```json
{
  "message": "Imagem enviada com sucesso.",
  "session_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "image": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "session_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "filename": "3fa85f64-5717-4562-b3fc-2c963f66afa6.jpg",
    "mime_type": "image/jpeg",
    "size_bytes": 48210,
    "url": "http://localhost:8000/uploads/3fa85f64-5717-4562-b3fc-2c963f66afa6.jpg",
    "created_at": "2026-04-28T13:45:00.123456Z"
  }
}
```

O campo `session_id` está presente em **toda** resposta (sessão nova ou existente).

---

### `GET /sessions/{session_id}` — Verificar sessão

Verifica se uma sessão existe. Útil para validar o `session_id` recuperado do cookie antes de listar imagens.

**Response `200 OK`**

```json
{
  "session_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "created_at": "2026-04-28T13:40:00Z"
}
```

**Response `404 Not Found`**

```json
{ "detail": "Sessão não encontrada." }
```

---

### `GET /sessions/{session_id}/images` — Listar imagens da sessão

Retorna todas as imagens vinculadas à sessão, em ordem cronológica.

**Response `200 OK`**

```json
{
  "session_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "total": 2,
  "images": [
    {
      "id": "...",
      "session_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "filename": "....jpg",
      "mime_type": "image/jpeg",
      "size_bytes": 48210,
      "url": "http://localhost:8000/uploads/....jpg",
      "created_at": "2026-04-28T13:45:00Z"
    }
  ]
}
```

---

### `GET /images/{image_id}` — Detalhes de uma imagem

Retorna os metadados de uma imagem específica pelo seu `id`.

---

### `GET /uploads/{filename}` — Arquivo de imagem

Serve o arquivo de imagem diretamente. A URL já vem pronta no campo `url` de cada `ImageResponse`.

---

## Gerenciamento de sessão via cookie

A sessão **não precisa ser criada previamente**. Ela é gerada automaticamente no primeiro `POST /images`.

### Comportamento por cenário

| Cookie `wc_session_id` enviado | Resultado |
|-------------------------------|-----------|
| Ausente                        | Nova sessão criada; `session_id` retornado na resposta |
| Presente e válido              | Sessão existente reutilizada |
| Presente e inválido/expirado   | Nova sessão criada; novo `session_id` retornado |

### Implementação recomendada em JavaScript

```javascript
// 1. Enviar a imagem (sem se preocupar com sessão)
fetch('/images', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    image: base64String,   // sem prefixo "data:image/...;base64,"
    mime_type: 'image/jpeg',
  }),
})
  .then(response => response.json())
  .then(data => {
    // data.session_id sempre estará presente na resposta

    // 2. Persistir o session_id no cookie (renovar a cada upload)
    document.cookie = [
      `wc_session_id=${data.session_id}`,
      'path=/',
      `max-age=${30 * 24 * 3600}`,   // 30 dias
      'SameSite=Lax',
    ].join('; ');
    
    console.log("Upload bem-sucedido!", data);
  })
  .catch(error => {
    console.error("Erro no upload:", error);
  });

// 3. Nas chamadas seguintes, o browser envia o cookie automaticamente.
//    A API o lê e reutiliza a sessão correspondente.

// 4. Para listar as imagens da sessão:
const sessionId = getCookie('wc_session_id');
if (sessionId) {
  fetch(`/sessions/${sessionId}/images`)
    .then(response => response.json())
    .then(list => console.log("Imagens:", list))
    .catch(error => console.error("Erro ao listar:", error));
}

// Helper para ler cookie
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}
```

> **Nota:** O cookie não é `HttpOnly` para que o JavaScript possa lê-lo e exibir o `session_id` na interface. Se a exibição não for necessária e a segurança for prioridade, configure-o como `HttpOnly` no backend (`app/routes/images.py`, linha `httponly=False`).

---

## Segurança

---

## Automação de Versão e Tags

Este projeto utiliza o **Conventional Commits** e **python-semantic-release** para automatizar a criação de tags e o versionamento.

### Como realizar Commits

Para que a automação funcione, utilize os prefixos padrão:

- `fix:` — Incrementa a versão **patch** (ex: 0.2.2 -> 0.2.3).
- `feat:` — Incrementa a versão **minor** (ex: 0.2.2 -> 0.3.0).
- `feat!:` ou `BREAKING CHANGE:` — Incrementa a versão **major** (ex: 0.2.2 -> 1.0.0).
- `docs:`, `style:`, `refactor:`, `test:`, `chore:` — Não incrementam a versão.

### Como gerar uma nova versão

Para calcular a próxima versão e criar a tag Git automaticamente:

```bash
# 1. Verifique qual será a próxima versão (Dry Run)
uv run semantic-release version --print

# 2. Gere a versão, crie a tag e atualize o histórico (Local)
uv run semantic-release version --no-push
```

Para realizar o release completo (incluindo push para o origin):
```bash
uv run semantic-release version
```

> **Nota:** O `hatch-vcs` garantirá que a versão no `pyproject.toml` e no metadata da API seja atualizada automaticamente a partir da nova tag criada.

---

## Erros comuns

| Código | Situação |
|--------|----------|
| `400`  | Base64 inválido ou magic bytes não correspondem ao `mime_type` declarado |
| `404`  | `session_id` ou `image_id` não encontrado |
| `413`  | Imagem maior que 10 MB |
| `415`  | `mime_type` não suportado (use `image/jpeg` ou `image/png`) |
| `422`  | Body JSON inválido ou campos ausentes |
