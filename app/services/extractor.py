import os
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import docx
from typing import Tuple

def extract_text_from_file(file_path: str, file_format: str) -> Tuple[str, str]:
    """
    Motor de Extracción Inteligente de Documentos:
    Selecciona la mejor estrategia según el formato y el contenido.
    Retorna una tupla (texto_extraído, nombre_del_parser_utilizado).
    """
    ext = file_format.lower().strip(".")

    if ext == "txt":
        return _extract_from_txt(file_path)
    elif ext == "docx":
        return _extract_from_docx(file_path)
    elif ext in ["png", "jpg", "jpeg"]:
        return _extract_from_image(file_path)
    elif ext == "pdf":
        return _extract_from_pdf(file_path)
    else:
        raise ValueError(f"Formato no soportado para extracción: {file_format}")

def _extract_from_txt(file_path: str) -> Tuple[str, str]:
    encodings = ["utf-8", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                text = f.read()
                return text.strip(), "Plain Text Reader (UTF-8/Fallback)"
        except UnicodeDecodeError:
            continue
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().strip(), "Plain Text Reader (Lossy Fallback)"

def _extract_from_docx(file_path: str) -> Tuple[str, str]:
    doc = docx.Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        if para.text:
            full_text.append(para.text)
    for table in doc.tables:
        for row in table.rows:
            row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_text:
                full_text.append(" | ".join(row_text))
    return "\n".join(full_text).strip(), "python-docx Parser"

def _extract_from_image(file_path: str) -> Tuple[str, str]:
    image = Image.open(file_path)
    # Tesseract con soporte para Español e Inglés
    text = pytesseract.image_to_string(image, lang="spa+eng")
    return text.strip(), "Tesseract OCR Engine (spa+eng)"

def _extract_from_pdf(file_path: str) -> Tuple[str, str]:
    doc = fitz.open(file_path)
    text_pages = []
    total_chars = 0

    # 1. Intentar extracción directa de texto vectorial con PyMuPDF
    for page in doc:
        page_text = page.get_text()
        text_pages.append(page_text)
        total_chars += len(page_text.strip())

    # Si se extrajo una cantidad razonable de texto, es un PDF nativo
    avg_chars_per_page = total_chars / len(doc) if len(doc) > 0 else 0
    if avg_chars_per_page > 15:
        combined_text = "\n--- Página ---\n".join(text_pages).strip()
        doc.close()
        return combined_text, "PyMuPDF (fitz) Direct Parser"

    # 2. Si el texto es escaso o nulo, es un PDF escaneado -> Ejecutar OCR por página
    ocr_pages = []
    for i, page in enumerate(doc):
        # Renderizar la página a una imagen de alta resolución (300 DPI -> zoom 2.0)
        pix = page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        page_ocr_text = pytesseract.image_to_string(img, lang="spa+eng")
        ocr_pages.append(f"--- Página {i+1} (OCR) ---\n" + page_ocr_text.strip())

    doc.close()
    return "\n".join(ocr_pages).strip(), "Hybrid OCR Fallback (PyMuPDF Pixmap + Tesseract OCR spa+eng)"
