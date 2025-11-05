from __future__ import annotations

import sys
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Dict, Iterable, List
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_ROOT = REPO_ROOT / "analysis-service" / "src"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))


@dataclass
class DummyModel:
    """Simple stub that mimics the Gemini `generate_content` method."""

    payload: str
    recorded_prompts: List[str]

    def generate_content(self, prompt: str):
        self.recorded_prompts.append(prompt)
        return SimpleNamespace(text=self.payload)


@pytest.fixture
def sample_segments() -> Iterable[Dict]:
    return [
        {"start": 0.0, "end": 4.2, "speaker": "Speaker 1", "text": "大家好，感謝今天參與。"},
        {"start": 4.2, "end": 9.8, "speaker": "Speaker 2", "text": "我們最近希望縮短點餐時間。"},
    ]


def build_dummy_factory(payload: str, recorded_prompts: List[str]):
    def _factory():
        return DummyModel(payload=payload, recorded_prompts=recorded_prompts)

    return _factory
