import requests
import time
import json
import os
import io

API_BASE = "http://localhost:8000/api/v1"

def run_tests():
    print("==================================================================")
    print("   PRUEBA COMPLETA DE PIPELINE Y INTELIGENCIA DE DOCUMENTOS")
    print("==================================================================")

    # 1. Healthcheck
    res = requests.get("http://localhost:8000/health")
    print(f"\n[1] Healthcheck API: Status {res.status_code} -> {res.json()}")
    assert res.status_code == 200

    # 2. Prueba Formato No Soportado (Debe rechazar con HTTP 400)
    print("\n[2] Probando rechazo de formato no permitido (.bin)...")
    res = requests.post(
        f"{API_BASE}/documents/upload",
        files={"file": ("malicious.bin", b"\x00\x01\x02\x03", "application/octet-stream")}
    )
    print(f"Respuesta HTTP {res.status_code}: {res.json().get('detail')}")
    assert res.status_code == 400

    # 3. Ingesta y Extracción de Documento TXT
    print("\n[3] Ingestando documento TXT...")
    txt_content = "Document Intelligence Async Pipeline.\nEste es un documento TXT de prueba para validar el patron Claim-Check y la extraccion asincrona en Celery y PostgreSQL."
    res = requests.post(
        f"{API_BASE}/documents/upload",
        files={"file": ("prueba.txt", txt_content.encode("utf-8"), "text/plain")}
    )
    assert res.status_code == 202
    txt_job_id = res.json()["job_id"]
    print(f"Claim-Check retornado: Job ID {txt_job_id}")

    # Polling TXT
    for _ in range(15):
        job = requests.get(f"{API_BASE}/jobs/{txt_job_id}").json()
        if job["status"] == "COMPLETED":
            break
        time.sleep(1)

    txt_res = requests.get(f"{API_BASE}/jobs/{txt_job_id}/result").json()
    print(f"-> Estado: {txt_res['status']}")
    print(f"-> Texto Extraído:\n{txt_res['extracted_text']}")
    print(f"-> Metadatos:\n{json.dumps(txt_res['extracted_metadata'], indent=2)}")
    assert txt_res["status"] == "COMPLETED"

    # 4. Ingesta de PDF Vectorial (de la guía U1T02.pdf en la raíz)
    print("\n[4] Ingestando PDF vectorial de la materia (U1T02.pdf)...")
    pdf_path = os.path.join(os.path.dirname(__file__), "U1T02.pdf")
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            res = requests.post(
                f"{API_BASE}/documents/upload",
                files={"file": ("U1T02.pdf", f, "application/pdf")}
            )
        assert res.status_code == 202
        pdf_job_id = res.json()["job_id"]
        print(f"Claim-Check retornado: Job ID {pdf_job_id}")

        for _ in range(20):
            job = requests.get(f"{API_BASE}/jobs/{pdf_job_id}").json()
            if job["status"] in ["COMPLETED", "FAILED"]:
                break
            time.sleep(1)

        pdf_res = requests.get(f"{API_BASE}/jobs/{pdf_job_id}/result").json()
        print(f"-> Estado: {pdf_res['status']}")
        print(f"-> Extracto (primeros 300 caracteres):\n{pdf_res['extracted_text'][:300]}...")
        print(f"-> Metadatos:\n{json.dumps(pdf_res['extracted_metadata'], indent=2)}")
        assert pdf_res["status"] == "COMPLETED"

        # 5. Ejecutar Benchmark en PDF
        print("\n[5] Ejecutando Benchmark comparativo de Parseadores en PDF...")
        bench_res = requests.get(f"{API_BASE}/jobs/{pdf_job_id}/benchmark").json()
        print(json.dumps(bench_res, indent=2))

    # 6. Listado de Historial
    print("\n[6] Consultando GET /api/v1/jobs (Historial)...")
    jobs_list = requests.get(f"{API_BASE}/jobs?limit=5").json()
    print(f"Total de trabajos en historial: {jobs_list['total']}")
    for j in jobs_list["jobs"]:
        print(f" - [{j['status']}] ID: {j['job_id'][:8]}... | Archivo: {j['filename']} | Duración: {j['processing_duration_sec']}s")

    print("\n==================================================================")
    print("   TODAS LAS PRUEBAS DEL PIPELINE HAN PASADO CON EXITO!")
    print("==================================================================")

if __name__ == "__main__":
    run_tests()
