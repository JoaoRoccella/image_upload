"""
Router de sessões — consulta e valida sessões de captura.

As sessões são criadas automaticamente pelo endpoint POST /images
na primeira chamada. Não é necessário criar uma sessão manualmente.
"""

from fastapi import APIRouter, HTTPException, status

from app.database import get_connection
from app.models import SessionResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Verificar sessão",
    description=(
        "Verifica se uma sessão existe e retorna seus metadados. "
        "Útil para validar um `session_id` recuperado do cookie antes de listar imagens."
    ),
)
def get_session(session_id: str) -> SessionResponse:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, created_at FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão não encontrada.",
        )

    return SessionResponse(session_id=row["id"], created_at=row["created_at"])
