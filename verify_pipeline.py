import time
import requests
import json
import os

API_BASE_URL = "http://localhost:8000/api/v1"

def test_pipeline():
    print("=== Iniciando Verificación de la API y el Pipeline Asíncrono ===")
    
    # 1. Healthcheck
    try:
        res = requests.get("http://localhost:8000/health", timeout=5)
        print(f"Healthcheck status code: {res.status_code}, response: {res.json()}")
        assert res.status_code == 200
    except Exception as e:
        print(f"Error al conectar con la API: {e}")
        return False

    # 2. Ingesta (Upload) de archivo de prueba
    sample_path = os.path.join(os.path.dirname(__file__), "samples", "sample.txt")
    if not os.path.exists(sample_path):
        print("Archivo de prueba no encontrado.")
        return False

    print("\n--- Enviando POST /api/v1/documents/upload ---")
    with open(sample_path, "rb") as f:
        files = {"file": ("sample.txt", f, "text/plain")}
        res = requests.post(f"{API_BASE_URL}/documents/upload", files=files)
    
    print(f"Upload response status: {res.status_code}")
    data = res.json()
    print(f"Payload recibido (Claim-Check): {json.dumps(data, indent=2)}")
    assert res.status_code == 202
    job_id = data["job_id"]

    # 3. Polling de trazabilidad del trabajo
    print(f"\n--- Monitoreando estado del Job ID: {job_id} ---")
    max_retries = 15
    for i in range(max_retries):
        res = requests.get(f"{API_BASE_URL}/jobs/{job_id}")
        job_info = res.json()
        status_str = job_info.get("status")
        progress = job_info.get("progress_percent")
        msg = job_info.get("status_message")
        print(f"Intento {i+1}: Estado={status_str}, Avance={progress}%, Mensaje='{msg}'")

        if status_str == "COMPLETED":
            print("\n¡Trabajo completado exitosamente!")
            break
        elif status_str == "FAILED":
            print(f"\n¡El trabajo falló! Error: {job_info.get('error_message')}")
            return False
        time.sleep(1)

    # 4. Obtener resultados finales
    print("\n--- Consultando GET /api/v1/jobs/{job_id}/result ---")
    res = requests.get(f"{API_BASE_URL}/jobs/{job_id}/result")
    result_data = res.json()
    print(f"Texto Extraído:\n{result_data.get('extracted_text')}")
    print(f"Metadatos Extraídos:\n{json.dumps(result_data.get('extracted_metadata'), indent=2)}")
    assert result_data["status"] == "COMPLETED"

    # 5. Ejecutar Benchmark
    print("\n--- Consultando GET /api/v1/jobs/{job_id}/benchmark ---")
    res = requests.get(f"{API_BASE_URL}/jobs/{job_id}/benchmark")
    print(f"Resultado del Benchmark:\n{json.dumps(res.json(), indent=2)}")

    print("\n=== VERIFICACIÓN DE PIPELINE FINALIZADA CON ÉXITO ===")
    return True

if __name__ == "__main__":
    test_pipeline()
