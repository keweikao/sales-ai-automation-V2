"""
檔案驗證工具

提供音檔上傳的驗證功能，包含：
- 檔案大小限制
- MIME type 驗證
- 音檔時長檢查
"""

import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)

# 檔案大小限制（bytes）
MAX_FILE_SIZE_MB = 100
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024  # 100 MB

# 音檔時長限制（秒）
MAX_AUDIO_DURATION_SECONDS = 3600  # 1 hour
MIN_AUDIO_DURATION_SECONDS = 5  # 5 seconds

# 支援的音檔格式
SUPPORTED_AUDIO_FORMATS = {
    "m4a": ["audio/mp4", "audio/x-m4a"],
    "mp3": ["audio/mpeg", "audio/mp3"],
    "wav": ["audio/wav", "audio/x-wav", "audio/wave"],
    "flac": ["audio/flac", "audio/x-flac"],
    "ogg": ["audio/ogg", "audio/x-ogg"],
    "aac": ["audio/aac", "audio/x-aac"],
    # iPhone Core Audio Format (語音備忘錄直接分享)
    "caf": ["audio/x-caf", "audio/caf"],
}

# 所有支援的 MIME types
ALL_SUPPORTED_MIME_TYPES = []
for mime_types in SUPPORTED_AUDIO_FORMATS.values():
    ALL_SUPPORTED_MIME_TYPES.extend(mime_types)


class FileValidationError(Exception):
    """檔案驗證錯誤"""
    def __init__(self, message: str, user_friendly_message: str):
        self.message = message
        self.user_friendly_message = user_friendly_message
        super().__init__(message)


def validate_audio_file(file_info: Dict) -> Tuple[bool, Optional[str]]:
    """
    驗證音檔檔案

    Args:
        file_info: Slack file_info API 回傳的檔案資訊

    Returns:
        Tuple[bool, Optional[str]]: (是否通過驗證, 錯誤訊息)

    Raises:
        FileValidationError: 驗證失敗時拋出，包含使用者友善的錯誤訊息
    """
    try:
        file_id = file_info.get("id", "unknown")
        file_name = file_info.get("name", "unknown")
        file_type = file_info.get("filetype", "").lower()
        file_size = file_info.get("size", 0)
        mime_type = file_info.get("mimetype", "").lower()

        # iPhone 直接分享時，Slack API 可能不回傳 filetype
        # 需要從檔名副檔名推斷格式
        if not file_type and file_name:
            if "." in file_name:
                file_type = file_name.rsplit(".", 1)[-1].lower()
                logger.info(f"Inferred file type from filename: {file_type}")

        logger.info(
            f"Validating file: {file_id} ({file_name}), "
            f"type={file_type}, size={file_size}, mime={mime_type}"
        )

        # 1. 檢查檔案類型（副檔名）
        if file_type not in SUPPORTED_AUDIO_FORMATS:
            supported_formats = ", ".join(SUPPORTED_AUDIO_FORMATS.keys())
            raise FileValidationError(
                f"Unsupported file type: {file_type}",
                f"⚠️ 檔案類型不支援：`{file_type}`\n\n"
                f"支援的格式：{supported_formats.upper()}"
            )

        # 2. 檢查檔案大小
        if file_size == 0:
            raise FileValidationError(
                f"File size is 0: {file_id}",
                "⚠️ 檔案大小為 0，可能是空檔案或上傳失敗。\n\n請重新上傳。"
            )

        if file_size > MAX_FILE_SIZE_BYTES:
            file_size_mb = file_size / (1024 * 1024)
            raise FileValidationError(
                f"File too large: {file_size} bytes ({file_size_mb:.1f} MB)",
                f"⚠️ 檔案過大：{file_size_mb:.1f} MB\n\n"
                f"檔案大小上限為 {MAX_FILE_SIZE_MB} MB。\n"
                f"建議：\n"
                f"• 使用音檔壓縮工具降低檔案大小\n"
                f"• 或將長錄音分段上傳"
            )

        # 3. 檢查 MIME type（實際格式）
        if mime_type:
            expected_mime_types = SUPPORTED_AUDIO_FORMATS.get(file_type, [])
            if mime_type not in expected_mime_types and mime_type not in ALL_SUPPORTED_MIME_TYPES:
                logger.warning(
                    f"MIME type mismatch for {file_id}: "
                    f"extension={file_type}, mime={mime_type}, "
                    f"expected={expected_mime_types}"
                )
                raise FileValidationError(
                    f"MIME type mismatch: extension={file_type}, mime={mime_type}",
                    f"⚠️ 檔案格式異常\n\n"
                    f"檔案副檔名為 `.{file_type}`，但實際格式為 `{mime_type}`。\n"
                    f"請確認檔案是否正確。"
                )

        # 4. 檢查是否為私人分享（DM）
        shares = file_info.get("shares", {})
        if not shares.get("private"):
            raise FileValidationError(
                f"File not shared in DM: {file_id}",
                "⚠️ 請在私訊（DM）中上傳音檔。\n\n不支援在頻道中處理音檔。"
            )

        # 所有檢查通過
        logger.info(f"File validation passed for {file_id}")
        return True, None

    except FileValidationError:
        # 重新拋出已知的驗證錯誤
        raise
    except Exception as e:
        # 捕捉未預期的錯誤
        logger.error(f"Unexpected error during file validation: {e}", exc_info=True)
        raise FileValidationError(
            f"Validation error: {str(e)}",
            "⚠️ 檔案驗證時發生錯誤，請稍後再試或聯絡技術支援。"
        )


def get_file_size_display(size_bytes: int) -> str:
    """
    將檔案大小轉換為人類可讀的格式

    Args:
        size_bytes: 檔案大小（bytes）

    Returns:
        str: 格式化的檔案大小（例如：「1.5 MB」）
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def validate_audio_duration(duration_seconds: float) -> Tuple[bool, Optional[str]]:
    """
    驗證音檔時長

    Args:
        duration_seconds: 音檔時長（秒）

    Returns:
        Tuple[bool, Optional[str]]: (是否通過驗證, 錯誤訊息)
    """
    if duration_seconds < MIN_AUDIO_DURATION_SECONDS:
        return False, (
            f"⚠️ 音檔時長過短：{duration_seconds:.1f} 秒\n\n"
            f"最短時長要求：{MIN_AUDIO_DURATION_SECONDS} 秒"
        )

    if duration_seconds > MAX_AUDIO_DURATION_SECONDS:
        duration_minutes = duration_seconds / 60
        max_minutes = MAX_AUDIO_DURATION_SECONDS / 60
        return False, (
            f"⚠️ 音檔時長過長：{duration_minutes:.1f} 分鐘\n\n"
            f"最長時長限制：{max_minutes:.0f} 分鐘\n"
            f"建議將長錄音分段上傳。"
        )

    return True, None
