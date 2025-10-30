"""
VAD (Voice Activity Detection) Processor Module

使用 Faster-Whisper 內建的 VAD 功能進行語音活動檢測
"""

import logging
from typing import List, Dict, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class VADProcessor:
    """VAD 語音活動檢測處理器"""

    def __init__(
        self,
        threshold: float = 0.5,
        min_speech_duration_ms: int = 250,
        min_silence_duration_ms: int = 500,
        speech_pad_ms: int = 400
    ):
        """
        初始化 VAD 處理器

        Args:
            threshold: 語音檢測閾值 (0-1)，越高越嚴格
            min_speech_duration_ms: 最短語音長度（毫秒）
            min_silence_duration_ms: 最短靜音長度（毫秒）
            speech_pad_ms: 語音前後保留時間（毫秒），避免切掉句首句尾
        """
        self.vad_parameters = {
            "threshold": threshold,
            "min_speech_duration_ms": min_speech_duration_ms,
            "min_silence_duration_ms": min_silence_duration_ms,
            "speech_pad_ms": speech_pad_ms
        }

        logger.info(f"VAD Processor initialized with parameters: {self.vad_parameters}")

    def get_vad_parameters(self) -> Dict:
        """
        獲取 VAD 參數（用於 faster-whisper transcribe）

        Returns:
            Dict: VAD 參數字典
        """
        return self.vad_parameters

    def estimate_speech_ratio(
        self,
        audio_duration: float,
        estimated_silence_ratio: float = 0.35
    ) -> Tuple[float, float]:
        """
        預估語音與靜音時長

        Args:
            audio_duration: 音檔總長度（秒）
            estimated_silence_ratio: 預估靜音佔比（預設 35%）

        Returns:
            Tuple[float, float]: (語音時長, 靜音時長)
        """
        silence_duration = audio_duration * estimated_silence_ratio
        speech_duration = audio_duration - silence_duration

        logger.info(
            f"Estimated - Total: {audio_duration:.1f}s, "
            f"Speech: {speech_duration:.1f}s ({(1-estimated_silence_ratio)*100:.1f}%), "
            f"Silence: {silence_duration:.1f}s ({estimated_silence_ratio*100:.1f}%)"
        )

        return speech_duration, silence_duration

    @staticmethod
    def get_preset_parameters(preset: str = "meeting") -> Dict:
        """
        獲取預設的 VAD 參數配置

        Args:
            preset: 預設類型
                - "meeting": 會議錄音（多人對話）
                - "presentation": 演講/簡報（單人長時間）
                - "noisy": 嘈雜環境（背景噪音大）
                - "default": 預設配置

        Returns:
            Dict: VAD 參數字典
        """
        presets = {
            "meeting": {
                "threshold": 0.5,
                "min_speech_duration_ms": 250,
                "min_silence_duration_ms": 500,
                "speech_pad_ms": 400
            },
            "presentation": {
                "threshold": 0.6,
                "min_speech_duration_ms": 500,
                "min_silence_duration_ms": 1000,
                "speech_pad_ms": 300
            },
            "noisy": {
                "threshold": 0.7,
                "min_speech_duration_ms": 500,
                "min_silence_duration_ms": 800,
                "speech_pad_ms": 500
            },
            "default": {
                "threshold": 0.5,
                "min_speech_duration_ms": 250,
                "min_silence_duration_ms": 500,
                "speech_pad_ms": 400
            }
        }

        params = presets.get(preset, presets["default"])
        logger.info(f"Using VAD preset '{preset}': {params}")

        return params


# 使用範例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 建立 VAD 處理器
    vad = VADProcessor()

    # 獲取參數
    params = vad.get_vad_parameters()
    print(f"VAD Parameters: {params}")

    # 預估語音時長
    speech_time, silence_time = vad.estimate_speech_ratio(3600)  # 60分鐘
    print(f"Estimated speech: {speech_time/60:.1f} min, silence: {silence_time/60:.1f} min")
