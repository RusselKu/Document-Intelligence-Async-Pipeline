from typing import List
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import DocumentJob, JobStatus
from app.core.claim_check import validate_and_save_upload
from app.tasks.tasks import process_document_job
from app.services.benchmark import run_parser_benchmark
from app.schemas.document import (
    DocumentUploadResponse,
    JobStatusResponse,
    JobResultResponse,
    JobListResponse,
    SystemBenchmarkResponse
)

router = APIRouter()

@router.post(
    "/documents/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Subir documento para procesamiento asíncrono (Claim-Check Pattern)"
)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Endpoint de Ingesta:
    - Aplica la arquitectura Claim-Check.
    - Valida formato y tamaño del archivo.
    - Almacena el binario en el almacenamiento distribuido.
    - Registra el trabajo en PostgreSQL con estado PENDING.
    - Encola la tarea asíncrona en Celery y retorna el `job_id` (claim check).
    """
    job_id, filename, file_format, file_size_bytes, storage_path = validate_and_save_upload(file)

    # Crear registro inicial en la base de datos
    new_job = DocumentJob(
        id=job_id,
        filename=filename,
        file_format=file_format,
        file_size_bytes=file_size_bytes,
        storage_path=storage_path,
        status=JobStatus.PENDING,
        progress_percent=0,
        status_message="Documento recibido y encolado."
    )
    db.add(new_job)
    db.commit()

    # Dispatch Celery Task
    process_document_job.delay(job_id)

    return DocumentUploadResponse(
        job_id=job_id,
        filename=filename,
        file_format=file_format,
        file_size_bytes=file_size_bytes,
        status=JobStatus.PENDING,
        status_message="Trabajo encolado exitosamente.",
        claim_check_url=f"/api/v1/jobs/{job_id}"
    )

@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="Consultar el estado y progreso de un trabajo (Job Tracking)"
)
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Endpoint de Trazabilidad:
    Retorna el estado del trabajo (PENDING, PROCESSING, COMPLETED, FAILED),
    el porcentaje de avance y detalles de ejecución.
    """
    job = db.query(DocumentJob).filter(DocumentJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trabajo con ID '{job_id}' no encontrado."
        )
    return job

@router.get(
    "/jobs/{job_id}/result",
    response_model=JobResultResponse,
    summary="Obtener el resultado final del texto extraído y metadatos"
)
def get_job_result(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Endpoint de Resultado:
    Permite obtener el texto plano extraído y el reporte de metadatos una vez completado el procesamiento.
    """
    job = db.query(DocumentJob).filter(DocumentJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trabajo con ID '{job_id}' no encontrado."
        )

    if job.status == JobStatus.PENDING or job.status == JobStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El trabajo todavía está en proceso (Estado: {job.status.value}, Avance: {job.progress_percent}%)."
        )

    return JobResultResponse(
        job_id=job.id,
        filename=job.filename,
        status=job.status,
        extracted_text=job.extracted_text,
        extracted_metadata=job.extracted_metadata,
        completed_at=job.completed_at,
        error_message=job.error_message
    )

@router.get(
    "/jobs",
    response_model=JobListResponse,
    summary="Listar el historial de trabajos procesados"
)
def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Lista todos los trabajos registrados en el sistema ordenados por fecha de creación desc.
    """
    total = db.query(DocumentJob).count()
    jobs = db.query(DocumentJob).order_by(DocumentJob.created_at.desc()).offset(skip).limit(limit).all()
    return JobListResponse(total=total, jobs=jobs)

@router.get(
    "/jobs/{job_id}/benchmark",
    response_model=SystemBenchmarkResponse,
    summary="Ejecutar benchmark comparativo de parseadores sobre el documento"
)
def run_benchmark_for_job(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Endpoint de Benchmark (Parte 3 del PDF):
    Compara empíricamente el rendimiento de PyMuPDF, pypdf y Tesseract OCR sobre el documento seleccionado.
    """
    job = db.query(DocumentJob).filter(DocumentJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trabajo con ID '{job_id}' no encontrado."
        )
    return run_parser_benchmark(job.storage_path, job.file_format)
