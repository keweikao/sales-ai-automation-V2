"""
Results Merging Module

合併多個音檔片段的轉錄結果
"""

import logging
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class TranscriptionMerger:
    """轉錄結果合併器"""

    def __init__(
        self,
        overlap_duration: float = 2.0,
        similarity_threshold: float = 0.8
    ):
        """
        初始化合併器

        Args:
            overlap_duration: 片段重疊時間（秒）
            similarity_threshold: 文字相似度閾值（用於去重）
        """
        self.overlap_duration = overlap_duration
        self.similarity_threshold = similarity_threshold

        logger.info(
            f"Transcription Merger initialized - "
            f"overlap: {overlap_duration}s, "
            f"similarity threshold: {similarity_threshold}"
        )

    def merge_chunks(
        self,
        chunk_results: List[Dict]
    ) -> Dict:
        """
        合併所有片段的轉錄結果

        Args:
            chunk_results: 片段轉錄結果列表
                [
                    {
                        "chunk_id": 0,
                        "chunk": {"start": 0.0, "end": 612.5, ...},
                        "segments": [...],
                        "success": True,
                        ...
                    },
                    ...
                ]

        Returns:
            Dict: 合併後的完整轉錄結果
        """
        logger.info(f"Merging {len(chunk_results)} chunk results...")

        # 驗證所有片段都成功
        failed_chunks = [r for r in chunk_results if not r.get("success", False)]
        if failed_chunks:
            logger.warning(f"Found {len(failed_chunks)} failed chunks")
            for failed in failed_chunks:
                logger.warning(f"  Chunk {failed['chunk_id']}: {failed.get('error', 'Unknown error')}")

        # 過濾出成功的片段
        successful_chunks = [r for r in chunk_results if r.get("success", False)]

        if not successful_chunks:
            logger.error("No successful chunks to merge")
            return {
                "success": False,
                "error": "All chunks failed",
                "segments": [],
                "full_text": "",
                "statistics": {
                    "total_chunks": len(chunk_results),
                    "successful_chunks": 0,
                    "failed_chunks": len(failed_chunks)
                }
            }

        # 按 chunk_id 排序
        successful_chunks.sort(key=lambda x: x["chunk_id"])

        # 合併所有 segments
        merged_segments = []
        previous_chunk = None

        for chunk_result in successful_chunks:
            chunk = chunk_result["chunk"]
            chunk_start_offset = chunk["start"]
            segments = chunk_result.get("segments", [])

            logger.debug(
                f"Processing chunk {chunk_result['chunk_id']}: "
                f"{len(segments)} segments, offset: {chunk_start_offset:.1f}s"
            )

            for segment in segments:
                # 調整 segment 時間戳（加上片段在原始音檔中的起始位置）
                adjusted_segment = {
                    "start": segment["start"] + chunk_start_offset,
                    "end": segment["end"] + chunk_start_offset,
                    "text": segment["text"],
                    "words": []
                }

                # 調整 word 時間戳
                if segment.get("words"):
                    for word in segment["words"]:
                        adjusted_segment["words"].append({
                            "word": word["word"],
                            "start": word["start"] + chunk_start_offset,
                            "end": word["end"] + chunk_start_offset,
                            "probability": word.get("probability", 1.0)
                        })

                # 檢查是否在重疊區域（需要去重）
                is_in_overlap = False
                if previous_chunk and chunk.get("has_overlap_start", False):
                    overlap_start = chunk_start_offset
                    overlap_end = chunk_start_offset + self.overlap_duration

                    # 如果 segment 在重疊區域
                    if overlap_start <= adjusted_segment["start"] < overlap_end:
                        is_in_overlap = True
                        # 檢查是否與前一個片段的最後幾個 segments 重複
                        if self._is_duplicate_segment(adjusted_segment, merged_segments):
                            logger.debug(f"Skipping duplicate segment in overlap: {adjusted_segment['text'][:50]}...")
                            continue

                merged_segments.append(adjusted_segment)

            previous_chunk = chunk

        # 生成完整文字
        full_text = " ".join(seg["text"].strip() for seg in merged_segments)

        # 統計資訊
        total_duration = max(seg["end"] for seg in merged_segments) if merged_segments else 0
        total_processing_time = sum(r.get("processing_time", 0) for r in successful_chunks)

        statistics = {
            "total_chunks": len(chunk_results),
            "successful_chunks": len(successful_chunks),
            "failed_chunks": len(failed_chunks),
            "total_segments": len(merged_segments),
            "total_duration": total_duration,
            "total_processing_time": total_processing_time,
            "speed_ratio": total_processing_time / total_duration if total_duration > 0 else 0,
            "vad_enabled": successful_chunks[0].get("vad_enabled", False) if successful_chunks else False
        }

        result = {
            "success": True,
            "segments": merged_segments,
            "full_text": full_text,
            "statistics": statistics,
            "chunk_details": [
                {
                    "chunk_id": r["chunk_id"],
                    "success": r["success"],
                    "segments_count": len(r.get("segments", [])),
                    "processing_time": r.get("processing_time", 0)
                }
                for r in chunk_results
            ]
        }

        logger.info("="*60)
        logger.info("Merge Summary:")
        logger.info(f"  Total segments: {statistics['total_segments']}")
        logger.info(f"  Total duration: {statistics['total_duration']:.1f}s ({statistics['total_duration']/60:.1f} min)")
        logger.info(f"  Processing time: {statistics['total_processing_time']:.1f}s ({statistics['total_processing_time']/60:.1f} min)")
        logger.info(f"  Speed ratio: {statistics['speed_ratio']:.2f}x")
        logger.info(f"  Text length: {len(full_text)} characters")
        logger.info("="*60)

        return result

    def _is_duplicate_segment(
        self,
        segment: Dict,
        existing_segments: List[Dict],
        lookback: int = 3
    ) -> bool:
        """
        檢查 segment 是否與已存在的 segments 重複

        Args:
            segment: 要檢查的 segment
            existing_segments: 已存在的 segments 列表
            lookback: 檢查最後幾個 segments

        Returns:
            bool: 是否重複
        """
        if not existing_segments:
            return False

        # 只檢查最後幾個 segments
        recent_segments = existing_segments[-lookback:]

        segment_text = segment["text"].strip().lower()

        for existing_seg in recent_segments:
            existing_text = existing_seg["text"].strip().lower()

            # 完全相同
            if segment_text == existing_text:
                return True

            # 高度相似（簡單字串包含檢查）
            if len(segment_text) > 10 and len(existing_text) > 10:
                if segment_text in existing_text or existing_text in segment_text:
                    return True

        return False

    def save_to_file(
        self,
        merged_result: Dict,
        output_path: str,
        format: str = "txt"
    ) -> None:
        """
        將合併結果儲存為檔案

        Args:
            merged_result: 合併結果
            output_path: 輸出路徑
            format: 輸出格式 (txt, srt, vtt, json)
        """
        output_file = Path(output_path)

        if format == "txt":
            self._save_as_txt(merged_result, output_file)
        elif format == "srt":
            self._save_as_srt(merged_result, output_file)
        elif format == "vtt":
            self._save_as_vtt(merged_result, output_file)
        elif format == "json":
            self._save_as_json(merged_result, output_file)
        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info(f"Saved transcription to: {output_file}")

    def _save_as_txt(self, result: Dict, output_file: Path) -> None:
        """儲存為純文字格式"""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result["full_text"])

    def _save_as_srt(self, result: Dict, output_file: Path) -> None:
        """儲存為 SRT 字幕格式"""
        with open(output_file, "w", encoding="utf-8") as f:
            for i, segment in enumerate(result["segments"], start=1):
                start_time = self._format_timestamp_srt(segment["start"])
                end_time = self._format_timestamp_srt(segment["end"])

                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{segment['text'].strip()}\n")
                f.write("\n")

    def _save_as_vtt(self, result: Dict, output_file: Path) -> None:
        """儲存為 VTT 字幕格式"""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n")

            for segment in result["segments"]:
                start_time = self._format_timestamp_vtt(segment["start"])
                end_time = self._format_timestamp_vtt(segment["end"])

                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{segment['text'].strip()}\n")
                f.write("\n")

    def _save_as_json(self, result: Dict, output_file: Path) -> None:
        """儲存為 JSON 格式"""
        import json

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _format_timestamp_srt(seconds: float) -> str:
        """格式化時間戳為 SRT 格式 (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    @staticmethod
    def _format_timestamp_vtt(seconds: float) -> str:
        """格式化時間戳為 VTT 格式 (HH:MM:SS.mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


# 使用範例
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 模擬測試資料
    mock_chunk_results = [
        {
            "chunk_id": 0,
            "chunk": {"start": 0.0, "end": 600.0, "has_overlap_end": True},
            "success": True,
            "segments": [
                {"start": 0.0, "end": 3.5, "text": "這是第一個片段", "words": []},
                {"start": 3.5, "end": 7.0, "text": "包含一些測試內容", "words": []}
            ],
            "processing_time": 45.2,
            "vad_enabled": True
        },
        {
            "chunk_id": 1,
            "chunk": {"start": 598.0, "end": 1200.0, "has_overlap_start": True},
            "success": True,
            "segments": [
                {"start": 0.0, "end": 3.5, "text": "包含一些測試內容", "words": []},  # 重複
                {"start": 3.5, "end": 7.0, "text": "這是第二個片段", "words": []}
            ],
            "processing_time": 42.8,
            "vad_enabled": True
        }
    ]

    # 建立合併器
    merger = TranscriptionMerger(overlap_duration=2.0)

    # 合併結果
    result = merger.merge_chunks(mock_chunk_results)

    print(f"\nMerged text: {result['full_text']}")
    print(f"Total segments: {len(result['segments'])}")
    print(f"Statistics: {result['statistics']}")

    # 儲存為不同格式
    # merger.save_to_file(result, "output.txt", format="txt")
    # merger.save_to_file(result, "output.srt", format="srt")
    # merger.save_to_file(result, "output.json", format="json")

    print("\nMerger initialized successfully")
