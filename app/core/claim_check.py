import os
import uuid
import shutil
from typing import Tuple
from fastapi import UploadFile, HTTPException, status
from app.config import settings

def validate_and_save_upload(file: UploadFile) -> Tuple[str, str, str, int, str]:
    """
    Implementación del patrón Claim-Check:
    1. Valida extensión y tamaño del archivo recibido en el endpoint.
    2. Guarda el archivo binario pesado en el disco/volumen compartido.
    3. Retorna la referencia ligera (job_id, filename, format, size_bytes, storage_path).
    """
    filename = file.filename or "unnamed_document"
    ext = filename.split(".")[-1].lower() if "." in filename else ""

    if not ext or ext not in settings.ALLOWED_EXTENSIONS:
        allowed_str = ", ".join(sorted(settings.ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato de archivo '{ext}' no soportado. Formatos permitidos: {allowed_str}"
        )

    # Generar Job ID único
    job_id = str(uuid.uuid4())
    upload_dir = os.path.join(settings.STORAGE_DIR, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, f"{job_id}.{ext}")

    # Guardar archivo binario y calcular tamaño
    file_size_bytes = 0
    with open(file_path, "wb") as buffer:
        while chunk := file.file.read(8192):
            file_size_bytes += len(chunk)
            # Validar límite de tamaño
            if file_size_bytes > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                # Limpiar archivo parcial
                buffer.close()
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"El archivo excede el límite máximo permitido de {settings.MAX_UPLOAD_SIZE_MB} MB."
                )
            buffer.write(chunk)

    return job_id, filename, ext, file_size_bytes, file_path
