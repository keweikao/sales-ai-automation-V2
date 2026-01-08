"""
Metrics data schemas.

Defines the structure for service value metrics tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class ProcessingTimestamps:
    """Timestamps for each processing stage."""
    uploaded_at: Optional[datetime] = None
    transcription_started_at: Optional[datetime] = None
    transcription_completed_at: Optional[datetime] = None
    analysis_started_at: Optional[datetime] = None
    analysis_completed_at: Optional[datetime] = None


@dataclass
class ProcessingDurations:
    """Duration metrics in seconds."""
    transcription_seconds: Optional[float] = None
    analysis_seconds: Optional[float] = None
    total_processing_seconds: Optional[float] = None


@dataclass
class AudioMetrics:
    """Audio file metrics."""
    duration_seconds: Optional[float] = None
    file_size_bytes: Optional[int] = None


@dataclass
class AgentMetrics:
    """Per-agent execution metrics."""
    agent_id: str
    duration_seconds: float
    success: bool
    retry_count: int = 0


@dataclass
class CaseMetrics:
    """Complete metrics for a single case."""
    case_id: str
    status: str
    timestamps: ProcessingTimestamps = field(default_factory=ProcessingTimestamps)
    durations: ProcessingDurations = field(default_factory=ProcessingDurations)
    audio: AudioMetrics = field(default_factory=AudioMetrics)
    agent_metrics: Dict[str, AgentMetrics] = field(default_factory=dict)

    # Engagement metrics (from delivery)
    summary_view_count: int = 0
    summary_first_viewed_at: Optional[datetime] = None
    short_url_click_count: int = 0

    def to_firestore_dict(self) -> Dict[str, Any]:
        """Convert to Firestore-compatible dictionary."""
        return {
            "timestamps": {
                "uploadedAt": self.timestamps.uploaded_at,
                "transcriptionStartedAt": self.timestamps.transcription_started_at,
                "transcriptionCompletedAt": self.timestamps.transcription_completed_at,
                "analysisStartedAt": self.timestamps.analysis_started_at,
                "analysisCompletedAt": self.timestamps.analysis_completed_at,
            },
            "durations": {
                "transcriptionSeconds": self.durations.transcription_seconds,
                "analysisSeconds": self.durations.analysis_seconds,
                "totalProcessingSeconds": self.durations.total_processing_seconds,
            },
            "audio": {
                "durationSeconds": self.audio.duration_seconds,
                "fileSizeBytes": self.audio.file_size_bytes,
            },
            "agents": {
                agent_id: {
                    "durationSeconds": m.duration_seconds,
                    "success": m.success,
                    "retryCount": m.retry_count,
                }
                for agent_id, m in self.agent_metrics.items()
            },
        }


@dataclass
class PeriodMetrics:
    """Aggregated metrics for a time period."""
    period_start: datetime
    period_end: datetime

    # Volume
    total_cases: int = 0
    completed_cases: int = 0
    failed_cases: int = 0

    # Success rate
    success_rate: float = 0.0

    # Processing time (averages)
    avg_transcription_seconds: float = 0.0
    avg_analysis_seconds: float = 0.0
    avg_total_processing_seconds: float = 0.0

    # Audio stats
    total_audio_minutes: float = 0.0
    avg_audio_minutes: float = 0.0

    # Engagement
    total_summary_views: int = 0
    summaries_viewed_rate: float = 0.0

    # Time saved calculation
    manual_analysis_minutes_per_case: float = 45.0  # Configurable baseline
    estimated_time_saved_hours: float = 0.0

    # Cost
    estimated_cost_usd: float = 0.0
    cost_per_case_usd: float = 0.0

    def calculate_time_saved(self) -> float:
        """Calculate estimated time saved vs manual analysis."""
        if self.completed_cases == 0:
            return 0.0

        # Manual time: 45 min per case (listening + notes + feedback)
        manual_total_minutes = self.completed_cases * self.manual_analysis_minutes_per_case

        # AI time: average processing time + 5 min review
        ai_total_minutes = self.completed_cases * (self.avg_total_processing_seconds / 60 + 5)

        saved_minutes = manual_total_minutes - ai_total_minutes
        self.estimated_time_saved_hours = saved_minutes / 60

        return self.estimated_time_saved_hours
