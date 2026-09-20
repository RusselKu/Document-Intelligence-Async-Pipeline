import hashlib
import math
from typing import Dict, Any
from langdetect import detect, LangDetectException

def calculate_sha256(file_path: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def extract_document_metadata(
    file_path: str,
    extracted_text: str,
    parser_used: str,
    file_size_bytes: int
) -> Dict[str, Any]:
    """
    Calcula y estructura metadatos enriquecidos del documento e información del proceso.
    """
    words = extracted_text.split()
    word_count = len(words)
    char_count = len(extracted_text)
    line_count = len(extracted_text.splitlines()) if extracted_text else 0

    # Detección de Idioma
    language = "unknown"
    if word_count >= 5:
        try:
            language = detect(extracted_text[:2000])
        except LangDetectException:
            language = "unknown"

    # Tiempo estimado de lectura (promedio 200 palabras por minuto)
    reading_time_min = math.ceil(word_count / 200) if word_count > 0 else 0

    # Hash SHA-256 para integridad
    file_hash = calculate_sha256(file_path)

    return {
        "sha256": file_hash,
        "word_count": word_count,
        "character_count": char_count,
        "line_count": line_count,
        "detected_language": language,
        "estimated_reading_time_min": reading_time_min,
        "parser_used": parser_used,
        "file_size_bytes": file_size_bytes
    }
