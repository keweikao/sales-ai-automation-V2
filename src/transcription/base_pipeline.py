from abc import ABC, abstractmethod
from typing import List, Dict, Any

class TranscriptionPipeline(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str) -> List[Dict[str, Any]]:
        pass
