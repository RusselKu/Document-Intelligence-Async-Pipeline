import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
import os
import requests
import time
import json

API_BASE_URL = "http://localhost:8000/api/v1"

def create_sample_pdf(filepath: str):
    doc = fitz.open()
    page = doc.new_page()
    text = "PDF Vectorial de Prueba - Document Intelligence Async Pipeline.\nEste documento evalua la extraccion directa mediante PyMuPDF fitz sin necesidad de OCR."
    page.insert_text((50, 50), text, fontsize=14)
    doc.save(filepath)
    doc.close()

def create_sample_image(filepath: str):
    img = Image.new('RGB', (800, 200), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    # Escribir texto claro para OCR
    d.text((30, 80), "PRUEBA DE OCR CON TESSERACT EN IMAGEN PNG", fill=(0, 0, 0))
    img.save(filepath)

def test_pdf_and_image():
    print("=== Probando Extracción de PDF Vectorial y OCR en Imagen PNG ===")
    
    samples_dir = os.path.dirname(__file__)
    pdf_path = os.path.join(samples_dir, "test_doc.pdf")
    img_path = os.path.join(samples_dir, "test_img.png")

    create_sample_pdf(pdf_path)
    create_sample_image(img_path)

    # 1. Probar PDF
    print("\n--- Subiendo PDF (test_doc.pdf) ---")
    with open(pdf_path, "rb") as f:
        res = requests.post(f"{API_BASE_URL}/documents/upload", files={"file": ("test_doc.pdf", f, "application/pdf")})
    assert res.status_code == 202
    pdf_job_id = res.json()["job_id"]

    for _ in range(15):
        job = requests.get(f"{API_BASE_URL}/jobs/{pdf_job_id}").json()
        if job["status"] == "COMPLETED":
            break
        time.sleep(1)

    pdf_result = requests.get(f"{API_BASE_URL}/jobs/{pdf_job_id}/result").json()
    print(f"PDF Extraído:\n{pdf_result.get('extracted_text')}")
    print(f"Parser usado: {pdf_result.get('extracted_metadata', {}).get('parser_used')}")
    assert "PyMuPDF" in pdf_result.get('extracted_metadata', {}).get('parser_used')

    # 2. Probar Imagen PNG (OCR)
    print("\n--- Subiendo Imagen PNG (test_img.png) ---")
    with open(img_path, "rb") as f:
        res = requests.post(f"{API_BASE_URL}/documents/upload", files={"file": ("test_img.png", f, "image/png")})
    assert res.status_code == 202
    img_job_id = res.json()["job_id"]

    for _ in range(15):
        job = requests.get(f"{API_BASE_URL}/jobs/{img_job_id}").json()
        if job["status"] == "COMPLETED":
            break
        time.sleep(1)

    img_result = requests.get(f"{API_BASE_URL}/jobs/{img_job_id}/result").json()
    print(f"Imagen OCR Extraído:\n{img_result.get('extracted_text')}")
    print(f"Parser usado: {img_result.get('extracted_metadata', {}).get('parser_used')}")
    assert "Tesseract" in img_result.get('extracted_metadata', {}).get('parser_used')

    # 3. Probar Benchmark en PDF
    print("\n--- Benchmark en PDF ---")
    bench_res = requests.get(f"{API_BASE_URL}/jobs/{pdf_job_id}/benchmark").json()
    print(json.dumps(bench_res, indent=2))

    print("\n=== PRUEBAS DE PDF Y OCR EXITOSAS ===")

if __name__ == "__main__":
    test_pdf_and_image()
