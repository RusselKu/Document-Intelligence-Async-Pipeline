import os
import time
from datetime import datetime
from celery.utils.log import get_task_logger
from app.tasks.celery_app import celery_app
from app.db.session import get_db_context
from app.db.models import DocumentJob, JobStatus
from app.services.extractor import extract_text_from_file
from app.services.metadata import extract_document_metadata
from app.config import settings

logger = get_task_logger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def process_document_job(self, job_id: str):
    """
    Tarea asíncrona de procesamiento de documentos:
    - Cambia estado a PROCESSING.
    - Extrae el texto utilizando el motor de inteligencia.
    - Genera metadatos avanzados.
    - Almacena el resultado en DB y sistema de archivos.
    - Maneja errores para asegurar que ningún trabajo quede atascado.
    """
    logger.info(f"Iniciando procesamiento asíncrono para Job ID: {job_id}")
    start_time = time.time()

    with get_db_context() as db:
        job = db.query(DocumentJob).filter(DocumentJob.id == job_id).first()
        if not job:
            logger.error(f"Job ID {job_id} no encontrado en la base de datos.")
            return

        try:
            # 1. Actualizar a PROCESSING
            job.status = JobStatus.PROCESSING
            job.started_at = datetime.utcnow()
            job.progress_percent = 25
            job.status_message = "Leyendo y analizando archivo en worker..."
            db.commit()

            # Verificar existencia del archivo físico
            if not os.path.exists(job.storage_path):
                raise FileNotFoundError(f"El archivo físico no existe en la ruta {job.storage_path}")

            # 2. Extracción de texto
            job.progress_percent = 50
            job.status_message = "Ejecutando motor de parsing y OCR..."
            db.commit()

            extracted_text, parser_used = extract_text_from_file(job.storage_path, job.file_format)

            # 3. Extracción de metadatos
            job.progress_percent = 80
            job.status_message = "Calculando metadatos y verificando integridad..."
            db.commit()

            extracted_metadata = extract_document_metadata(
                file_path=job.storage_path,
                extracted_text=extracted_text,
                parser_used=parser_used,
                file_size_bytes=job.file_size_bytes
            )

            # Guardar copia del texto extraído en el almacenamiento de resultados
            extracted_dir = os.path.join(settings.STORAGE_DIR, "extracted")
            os.makedirs(extracted_dir, exist_ok=True)
            result_file_path = os.path.join(extracted_dir, f"{job_id}.txt")
            with open(result_file_path, "w", encoding="utf-8") as rf:
                rf.write(extracted_text)

            # 4. Actualizar estado a COMPLETED
            end_time = time.time()
            duration = round(end_time - start_time, 3)

            job.status = JobStatus.COMPLETED
            job.progress_percent = 100
            job.status_message = "Procesamiento finalizado con éxito."
            job.extracted_text = extracted_text
            job.extracted_metadata = extracted_metadata
            job.completed_at = datetime.utcnow()
            job.processing_duration_sec = duration
            db.commit()

            logger.info(f"Job ID {job_id} procesado exitosamente en {duration} segundos.")

        except Exception as exc:
            db.rollback()
            logger.error(f"Error procesando Job ID {job_id}: {str(exc)}", exc_info=True)

            # Reobtener objeto de la sesión limpia
            job = db.query(DocumentJob).filter(DocumentJob.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED
                job.progress_percent = 100
                job.status_message = "El procesamiento del documento ha fallado."
                job.error_message = str(exc)
                job.completed_at = datetime.utcnow()
                db.commit()
