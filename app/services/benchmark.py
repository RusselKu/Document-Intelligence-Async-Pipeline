import time
import os
import fitz  # PyMuPDF
from pypdf import PdfReader
from PIL import Image
import pytesseract
from typing import Dict, Any, List
from app.schemas.document import ParserBenchmarkResult, SystemBenchmarkResponse

def run_parser_benchmark(file_path: str, file_format: str) -> SystemBenchmarkResponse:
    """
    Ejecuta un benchmark comparativo entre parseadores sobre el archivo especificado.
    Soporta evaluación en PDFs y devuelve métricas de tiempo y volumen extraído.
    """
    ext = file_format.lower().strip(".")
    results: List[ParserBenchmarkResult] = []

    if ext != "pdf":
        # Para formatos distintos a PDF, ejecutamos el extractor único por defecto
        start_time = time.time()
        from app.services.extractor import extract_text_from_file
        text, parser_used = extract_text_from_file(file_path, file_format)
        elapsed = round(time.time() - start_time, 4)

        results.append(
            ParserBenchmarkResult(
                parser_name=parser_used,
                extraction_time_sec=elapsed,
                characters_extracted=len(text),
                words_extracted=len(text.split()),
                success=True,
                notes=f"Extractor nativo para formato .{ext}"
            )
        )
        return SystemBenchmarkResponse(
            test_file=os.path.basename(file_path),
            file_format=ext,
            results=results,
            recommended_parser=parser_used
        )

    # Benchmark específico para PDF: Comparación entre PyMuPDF, pypdf y Tesseract OCR

    # 1. Benchmark PyMuPDF (fitz)
    try:
        t0 = time.time()
        doc = fitz.open(file_path)
        fitz_text = "".join([page.get_text() for page in doc])
        doc.close()
        t1 = time.time()
        results.append(
            ParserBenchmarkResult(
                parser_name="PyMuPDF (fitz)",
                extraction_time_sec=round(t1 - t0, 4),
                characters_extracted=len(fitz_text),
                words_extracted=len(fitz_text.split()),
                success=True,
                notes="Parseador directo basado en C/C++, ultra rápido para PDFs vectoriales."
            )
        )
    except Exception as e:
        results.append(
            ParserBenchmarkResult(
                parser_name="PyMuPDF (fitz)",
                extraction_time_sec=0.0,
                characters_extracted=0,
                words_extracted=0,
                success=False,
                notes=f"Error: {str(e)}"
            )
        )

    # 2. Benchmark PyPDF
    try:
        t0 = time.time()
        reader = PdfReader(file_path)
        pypdf_text = "".join([page.extract_text() or "" for page in reader.pages])
        t1 = time.time()
        results.append(
            ParserBenchmarkResult(
                parser_name="pypdf",
                extraction_time_sec=round(t1 - t0, 4),
                characters_extracted=len(pypdf_text),
                words_extracted=len(pypdf_text.split()),
                success=True,
                notes="Parseador de código abierto en Python puro para PDFs estándar."
            )
        )
    except Exception as e:
        results.append(
            ParserBenchmarkResult(
                parser_name="pypdf",
                extraction_time_sec=0.0,
                characters_extracted=0,
                words_extracted=0,
                success=False,
                notes=f"Error: {str(e)}"
            )
        )

    # 3. Benchmark Tesseract OCR (vía PyMuPDF Pixmap)
    try:
        t0 = time.time()
        doc = fitz.open(file_path)
        ocr_text_list = []
        # Evaluar hasta las primeras 3 páginas para evitar sobrecargar la respuesta
        for i in range(min(len(doc), 3)):
            page = doc[i]
            pix = page.get_pixmap(dpi=150)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            ocr_text_list.append(pytesseract.image_to_string(img, lang="spa+eng"))
        doc.close()
        ocr_text = "".join(ocr_text_list)
        t1 = time.time()
        results.append(
            ParserBenchmarkResult(
                parser_name="Tesseract OCR (spa+eng)",
                extraction_time_sec=round(t1 - t0, 4),
                characters_extracted=len(ocr_text),
                words_extracted=len(ocr_text.split()),
                success=True,
                notes="Motor OCR sobre imágenes/páginas escaneadas."
            )
        )
    except Exception as e:
        results.append(
            ParserBenchmarkResult(
                parser_name="Tesseract OCR (spa+eng)",
                extraction_time_sec=0.0,
                characters_extracted=0,
                words_extracted=0,
                success=False,
                notes=f"Error: {str(e)}"
            )
        )

    # Determinar recomendación
    recommended = "PyMuPDF (fitz)"
    fitz_res = next((r for r in results if r.parser_name == "PyMuPDF (fitz)"), None)
    if fitz_res and fitz_res.characters_extracted < 50:
        recommended = "Tesseract OCR (spa+eng) [PDF Escaneado/Imagen]"

    return SystemBenchmarkResponse(
        test_file=os.path.basename(file_path),
        file_format=ext,
        results=results,
        recommended_parser=recommended
    )
