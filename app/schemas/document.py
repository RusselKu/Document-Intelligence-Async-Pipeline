from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.db.models import JobStatus

class DocumentUploadResponse(BaseModel):
    job_id: str
    filename: str
    file_format: str
    file_size_bytes: int
    status: JobStatus
    status_message: str
    claim_check_url: str

class JobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    filename: str
    file_format: str
    file_size_bytes: int
    status: JobStatus
    progress_percent: int
    status_message: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_duration_sec: Optional[float] = None
    error_message: Optional[str] = None

class JobResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    filename: str
    status: JobStatus
    extracted_text: Optional[str] = None
    extracted_metadata: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class JobListResponse(BaseModel):
    total: int
    jobs: List[JobStatusResponse]

class ParserBenchmarkResult(BaseModel):
    parser_name: str
    extraction_time_sec: float
    characters_extracted: int
    words_extracted: int
    success: bool
    notes: str

class SystemBenchmarkResponse(BaseModel):
    test_file: str
    file_format: str
    results: List[ParserBenchmarkResult]
    recommended_parser: str
