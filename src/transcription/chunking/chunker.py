"""
Audio Chunking Module

智能音檔分段模組，基於音檔長度將長音檔切分成適合處理的片段
"""

import logging
from typing import List, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class AudioChunker:
    """音檔智能分段器"""

    def __init__(
        self,
        target_chunk_duration: int = 600,  # 10分鐘
        max_chunk_duration: int = 900,     # 15分鐘
        min_chunk_duration: int = 300,     # 5分鐘
        overlap_duration: int = 2          # 2秒重疊
    ):
        """
        初始化分段器

        Args:
            target_chunk_duration: 目標片段長度（秒）
            max_chunk_duration: 最大片段長度（秒）
            min_chunk_duration: 最小片段長度（秒）
            overlap_duration: 片段重疊時間（秒），避免切斷句子
        """
        self.target_duration = target_chunk_duration
        self.max_duration = max_chunk_duration
        self.min_duration = min_chunk_duration
        self.overlap = overlap_duration

        logger.info(
            f"Audio Chunker initialized - "
            f"target: {target_chunk_duration}s, "
            f"max: {max_chunk_duration}s, "
            f"overlap: {overlap_duration}s"
        )

    def create_chunks(
        self,
        total_duration: float
    ) -> List[Dict]:
        """
        創建音檔分段

        Args:
            total_duration: 音檔總長度（秒）

        Returns:
            List[Dict]: 分段資訊列表
            [
                {
                    "chunk_id": 0,
                    "start": 0.0,
                    "end": 612.5,
                    "duration": 612.5,
                    "has_overlap_start": False,
                    "has_overlap_end": True
                },
                ...
            ]
        """
        logger.info(f"Creating chunks for audio duration: {total_duration:.1f}s ({total_duration/60:.1f} min)")

        # 如果音檔短於目標長度，不分段
        if total_duration <= self.target_duration:
            logger.info("Audio is shorter than target duration, no chunking needed")
            return [{
                "chunk_id": 0,
                "start": 0.0,
                "end": total_duration,
                "duration": total_duration,
                "has_overlap_start": False,
                "has_overlap_end": False
            }]

        chunks = []
        current_start = 0.0
        chunk_id = 0

        while current_start < total_duration:
            # 計算片段結束點
            ideal_end = current_start + self.target_duration
            chunk_end = min(ideal_end, total_duration)

            # 檢查剩餘長度
            remaining = total_duration - chunk_end

            # 如果剩餘部分太短，合併到當前片段
            if 0 < remaining < self.min_duration:
                chunk_end = total_duration

            chunk_duration = chunk_end - current_start

            # 創建片段
            chunk = {
                "chunk_id": chunk_id,
                "start": current_start,
                "end": chunk_end,
                "duration": chunk_duration,
                "has_overlap_start": chunk_id > 0,
                "has_overlap_end": chunk_end < total_duration
            }

            chunks.append(chunk)

            logger.debug(
                f"Created chunk {chunk_id}: "
                f"{current_start:.1f}s - {chunk_end:.1f}s "
                f"({chunk_duration:.1f}s)"
            )

            # 移動到下一個片段（包含重疊）
            if chunk_end >= total_duration:
                break

            current_start = chunk_end - self.overlap
            chunk_id += 1

        logger.info(f"Created {len(chunks)} chunks")
        self._print_chunk_summary(chunks)

        return chunks

    def _print_chunk_summary(self, chunks: List[Dict]) -> None:
        """打印分段摘要"""
        logger.info("Chunk Summary:")
        for chunk in chunks:
            logger.info(
                f"  Chunk {chunk['chunk_id']}: "
                f"{chunk['start']:.1f}s - {chunk['end']:.1f}s "
                f"({chunk['duration']:.1f}s, "
                f"{chunk['duration']/60:.1f} min)"
            )

    def get_extraction_info(
        self,
        audio_path: str,
        chunk: Dict
    ) -> Dict:
        """
        獲取音檔片段提取資訊（用於 ffmpeg）

        Args:
            audio_path: 原始音檔路徑
            chunk: 片段資訊

        Returns:
            Dict: 提取資訊
            {
                "input": "original.m4a",
                "output": "chunk_0.wav",
                "start": 0.0,
                "duration": 612.5,
                "ffmpeg_command": "ffmpeg -i ..."
            }
        """
        chunk_id = chunk["chunk_id"]
        start = chunk["start"]
        duration = chunk["duration"]

        # 生成輸出檔名
        input_path = Path(audio_path)
        output_filename = f"{input_path.stem}_chunk_{chunk_id:03d}.wav"

        # 構建 ffmpeg 命令
        ffmpeg_cmd = (
            f'ffmpeg -i "{audio_path}" '
            f'-ss {start} '
            f'-t {duration} '
            f'-ar 16000 '  # 重採樣至 16kHz
            f'-ac 1 '      # 轉為單聲道
            f'-c:a pcm_s16le '  # WAV 格式
            f'"{output_filename}"'
        )

        return {
            "input": str(audio_path),
            "output": output_filename,
            "start": start,
            "duration": duration,
            "chunk_id": chunk_id,
            "ffmpeg_command": ffmpeg_cmd
        }


# 使用範例
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 建立分段器
    chunker = AudioChunker(
        target_chunk_duration=600,  # 10分鐘
        overlap_duration=2
    )

    # 測試不同長度的音檔
    test_cases = [
        ("30分鐘", 1800),
        ("60分鐘", 3600),
        ("90分鐘", 5400),
        ("120分鐘", 7200)
    ]

    for name, duration in test_cases:
        print(f"\n{'='*60}")
        print(f"測試案例: {name} 音檔 ({duration}秒)")
        print(f"{'='*60}")

        chunks = chunker.create_chunks(duration)

        print(f"\n分段結果: {len(chunks)} 個片段")
        for chunk in chunks:
            print(
                f"  Chunk {chunk['chunk_id']}: "
                f"{chunk['start']/60:.1f} - {chunk['end']/60:.1f} min "
                f"({chunk['duration']/60:.1f} min)"
            )
