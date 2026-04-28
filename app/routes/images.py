"""
Router de imagens — upload e listagem de imagens por sessão.
"""

from datetime import datetime, timezone
from uuid import uuid4

import aiofiles
from fastapi import APIRouter, Cookie, HTTPException, Request, Response, status

from app.database import UPLOADS_DIR, get_connection
from app.models import (
    ImageResponse,
    ImageUploadRequest,
    SessionImagesResponse,
    UploadResponse,
)
from app.security import decode_and_validate_image, get_extension

router = APIRouter(tags=["images"])

# Nome e configuração do cookie de sessão
COOKIE_NAME = "wc_session_id"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 dias


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _build_image_url(request: Request, filename: str) -> str:
    """Constrói a URL pública de acesso à imagem."""
    base = str(request.base_url).rstrip("/")
    return f"{base}/uploads/{filename}"


def _row_to_image_response(row, request: Request) -> ImageResponse:
    return ImageResponse(
        id=row["id"],
        session_id=row["session_id"],
        filename=row["filename"],
        mime_type=row["mime_type"],
        size_bytes=row["size_bytes"],
        url=_build_image_url(request, row["filename"]),
        created_at=row["created_at"],
    )


def _get_or_create_session(session_id: str | None) -> tuple[str, bool]:
    """
    Retorna (session_id, created) onde created=True se uma nova sessão foi criada.
    Se session_id for None ou não existir no banco, cria uma nova sessão.
    """
    if session_id:
        row = None
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
        if row:
            return session_id, False

    # Cria nova sessão
    new_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO sessions (id, created_at) VALUES (?, ?)",
            (new_id, created_at),
        )
    return new_id, True


def _assert_session_exists(session_id: str) -> None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão não encontrada.",
        )


# ---------------------------------------------------------------------------
# Upload de imagem  (POST /images)
# ---------------------------------------------------------------------------

_UPLOAD_DESCRIPTION = """\
Recebe uma imagem em base64 via JSON, valida segurança e armazena em disco.

## Gerenciamento de sessão via cookie

A sessão é **criada automaticamente** na primeira chamada — não é necessário
nenhum passo anterior. O `session_id` retornado deve ser persistido pelo
frontend como cookie `wc_session_id` para reutilização da mesma sessão
nas capturas seguintes.

### Fluxo recomendado no JavaScript

```javascript
// 1. Preparação para usar webcapture API
const canvas = document.querySelector('canvas');
const fullBase64 = canvas.toDataURL('image/jpeg');

// Removendo o prefixo "data:image/jpeg;base64,"
const base64String = fullBase64.split(',')[1];

// 2. Enviar a imagem (sem se preocupar com sessão)
fetch('/images', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ image: base64String, mime_type: 'image/jpeg' }),
})
  .then(response => response.json())
  .then(data => {
    // 3. Registrar o session_id em um cookie (válido por 30 dias)
    document.cookie = [
      `wc_session_id=${data.session_id}`,
      'path=/',
      `max-age=${30 * 24 * 3600}`,
      'SameSite=Lax',
    ].join('; ');

    console.log("Upload bem-sucedido!", data);
  })
  .catch(error => {
    console.error("Erro no upload:", error);
  });

// 4. Nas chamadas seguintes, o cookie é enviado automaticamente pelo browser
//    e a API reutilizará a mesma sessão.

// 5. Para listar as imagens da sessão:
const sessionId = getCookie('wc_session_id');
if (sessionId) {
  fetch(`/sessions/${sessionId}/images`)
    .then(response => response.json())
    .then(data => {
      console.log("Imagens da sessão:", data);
    })
    .catch(error => {
      console.error("Erro ao listar imagens:", error);
    });
}
```

### Comportamento por cenário

| Cookie `wc_session_id` | Resultado |
|------------------------|-----------|
| Ausente                | Nova sessão criada; `session_id` retornado na resposta |
| Presente e válido      | Sessão existente reutilizada |
| Presente e inválido    | Nova sessão criada; novo `session_id` retornado |

### Corpo da resposta

O campo `session_id` está presente **em toda resposta**, independente de a
sessão ser nova ou existente. O frontend deve sempre atualizar o cookie com
o valor recebido para garantir a validade do prazo de expiração.
"""


@router.post(
    "/images",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar imagem capturada",
    description=_UPLOAD_DESCRIPTION,
)
async def upload_image(
    payload: ImageUploadRequest,
    request: Request,
    response: Response,
    wc_session_id: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> UploadResponse:
    # Obtém ou cria sessão baseado no cookie recebido
    session_id, _ = _get_or_create_session(wc_session_id)

    # Define (ou renova) o cookie na resposta
    response.set_cookie(
        key=COOKIE_NAME,
        value=session_id,
        max_age=COOKIE_MAX_AGE,
        path="/",
        samesite="lax",
        httponly=False,  # Deve ser legível pelo JS para exibição na UI
    )

    # Decodifica e valida segurança da imagem
    image_bytes = decode_and_validate_image(payload.image, payload.mime_type)

    # Gera nome único no servidor (nunca usa nome enviado pelo cliente)
    ext = get_extension(payload.mime_type)
    image_id = str(uuid4())
    filename = f"{image_id}{ext}"
    filepath = UPLOADS_DIR / filename

    # Salva o arquivo em disco de forma assíncrona
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(image_bytes)

    # Persiste metadados no banco
    created_at = datetime.now(timezone.utc).isoformat()
    relative_path = f"uploads/{filename}"

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO images (id, session_id, filename, filepath, mime_type, size_bytes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                image_id,
                session_id,
                filename,
                relative_path,
                payload.mime_type,
                len(image_bytes),
                created_at,
            ),
        )

    image_resp = ImageResponse(
        id=image_id,
        session_id=session_id,
        filename=filename,
        mime_type=payload.mime_type,
        size_bytes=len(image_bytes),
        url=_build_image_url(request, filename),
        created_at=created_at,
    )
    return UploadResponse(
        message="Imagem enviada com sucesso.",
        session_id=session_id,
        image=image_resp,
    )


# ---------------------------------------------------------------------------
# Listagem de imagens da sessão  (GET /sessions/{session_id}/images)
# ---------------------------------------------------------------------------

@router.get(
    "/sessions/{session_id}/images",
    response_model=SessionImagesResponse,
    summary="Listar imagens da sessão",
    description=(
        "Retorna todas as imagens vinculadas à sessão informada, "
        "em ordem cronológica. O `session_id` pode ser recuperado do cookie "
        "`wc_session_id` ou do campo `session_id` da última resposta de upload."
    ),
)
def list_images(session_id: str, request: Request) -> SessionImagesResponse:
    _assert_session_exists(session_id)

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, session_id, filename, filepath, mime_type, size_bytes, created_at
            FROM images
            WHERE session_id = ?
            ORDER BY created_at ASC
            """,
            (session_id,),
        ).fetchall()

    images = [_row_to_image_response(row, request) for row in rows]
    return SessionImagesResponse(
        session_id=session_id,
        total=len(images),
        images=images,
    )


# ---------------------------------------------------------------------------
# Detalhes de uma imagem específica  (GET /images/{image_id})
# ---------------------------------------------------------------------------

@router.get(
    "/images/{image_id}",
    response_model=ImageResponse,
    summary="Detalhes de uma imagem",
    description="Retorna os metadados de uma imagem específica pelo seu `id`.",
)
def get_image(image_id: str, request: Request) -> ImageResponse:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, session_id, filename, filepath, mime_type, size_bytes, created_at
            FROM images WHERE id = ?
            """,
            (image_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Imagem não encontrada.",
        )

    return _row_to_image_response(row, request)
