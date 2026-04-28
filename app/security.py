"""
Módulo de segurança — validação de imagens antes do armazenamento.
"""

import base64
import binascii

from fastapi import HTTPException, status

# Limite de tamanho do arquivo decodificado (10 MB)
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

# MIME types permitidos mapeados para seus magic bytes
ALLOWED_MIME_TYPES: dict[str, list[bytes]] = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
}

# Extensões correspondentes aos MIME types
MIME_EXTENSIONS: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


def decode_and_validate_image(image_b64: str, mime_type: str) -> bytes:
    """
    Decodifica o base64, valida o tamanho e verifica os magic bytes.

    Raises:
        HTTPException 400 — se o base64 for inválido, o arquivo for grande
                            demais ou os magic bytes não corresponderem.
        HTTPException 415 — se o mime_type não for suportado.
    """
    # 1. MIME type permitido
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Tipo MIME '{mime_type}' não suportado. Use image/jpeg ou image/png.",
        )

    # 2. Decodificar base64
    try:
        image_bytes = base64.b64decode(image_b64, validate=True)
    except binascii.Error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conteúdo base64 inválido.",
        )

    # 3. Verificar tamanho
    if len(image_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Imagem excede o limite de {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.",
        )

    # 4. Verificar magic bytes (previne disfarce de tipo)
    magic_list = ALLOWED_MIME_TYPES[mime_type]
    if not any(image_bytes.startswith(magic) for magic in magic_list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conteúdo do arquivo não corresponde ao tipo MIME declarado.",
        )

    return image_bytes


def get_extension(mime_type: str) -> str:
    """Retorna a extensão de arquivo para o MIME type dado."""
    return MIME_EXTENSIONS.get(mime_type, ".bin")
