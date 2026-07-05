"""
Shared test fixtures. Forces the JSON memory backend so the whole training loop
runs with no ChromaDB and no API key — tests are hermetic and fast.
"""

import os
import tempfile

import pytest

os.environ["GOLDFRONT_MEMORY_BACKEND"] = "json"

from brain.memory.knowledge_base import KnowledgeBase  # noqa: E402
from brain.training.service import TrainingService  # noqa: E402


@pytest.fixture
def kb():
    return KnowledgeBase(path=tempfile.mkdtemp())


@pytest.fixture
def svc(kb):
    return TrainingService(kb)
