import enum
from datetime import datetime
from sqlalchemy import Column, String, Integer, BigInteger, Float, Text, JSON, DateTime, Enum as SQLEnum
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class DocumentJob(Base):
    __tablename__ = "document_jobs"

    id = Column(String(36), primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_format = Column(String(20), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    storage_path = Column(String(512), nullable=False)

    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True)
    progress_percent = Column(Integer, default=0, nullable=False)
    status_message = Column(String(255), default="Encolado para procesamiento", nullable=False)

    extracted_text = Column(Text, nullable=True)
    extracted_metadata = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    retry_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    processing_duration_sec = Column(Float, nullable=True)

    @property
    def job_id(self) -> str:
        return self.id

