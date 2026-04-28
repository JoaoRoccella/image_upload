"""
Pydantic models para request e response da API.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

class ImageUploadRequest(BaseModel):
    """Payload enviado pelo frontend ao fazer upload de uma imagem."""

    # Dado da imagem codificado em base64 (sem prefixo data URI)
    image: str = Field(
        ...,
        description="Conteúdo da imagem codificado em base64 puro (sem prefixo data:image/...).",
        min_length=4,
    )
    mime_type: Literal["image/jpeg", "image/png"] = Field(
        ...,
        description="Tipo MIME da imagem. Apenas image/jpeg e image/png são aceitos.",
    )

    @field_validator("image")
    @classmethod
    def strip_data_uri_prefix(cls, v: str) -> str:
        """Remove prefixo 'data:image/...;base64,' se o frontend enviá-lo."""
        if "," in v and v.startswith("data:"):
            v = v.split(",", 1)[1]
        return v.strip()


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

class SessionResponse(BaseModel):
    session_id: str
    created_at: datetime


class ImageResponse(BaseModel):
    id: str
    session_id: str
    filename: str
    mime_type: str
    size_bytes: int
    url: str                # URL para acesso direto à imagem
    created_at: datetime


class UploadResponse(BaseModel):
    message: str
    session_id: str = Field(
        ...,
        description=(
            "UUID da sessão à qual a imagem foi vinculada. "
            "Na primeira chamada (sem cookie), uma sessão nova é criada automaticamente. "
            "O frontend deve persistir este valor como cookie `wc_session_id` "
            "para reutilizar a mesma sessão em capturas subsequentes."
        ),
    )
    image: ImageResponse


class SessionImagesResponse(BaseModel):
    session_id: str
    total: int
    images: list[ImageResponse]
