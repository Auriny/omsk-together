# tests/test_rubert_pipeline.py

import asyncio
from dataclasses import dataclass
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from enums import LabelsEnum
from pipeline.classifier.rubert import RuBERTClassifier


@dataclass
class Item:
    district: str
    topic: str
    text: str


@dataclass
class Batch:
    items: list[Item]


@pytest.mark.asyncio
async def test_pipeline_classify_filters_not_problem_and_small():
    with patch("pipeline.classifier.rubert.RuBERT") as mock_rubert_cls:
        mock_model = MagicMock()
        mock_model.filter = AsyncMock(
            return_value=[LabelsEnum.NOT_PROBLEM, LabelsEnum.SMALL, 5]
        )
        mock_rubert_cls.get_instance.return_value = mock_model

        classifier = RuBERTClassifier()

        batch = Batch(
            items=[
                Item("district1", "topic1", "text1"),  # NOT_PROBLEM
                Item("district2", "topic2", "text2"),  # SMALL
                Item("district3", "topic3", "text3"),  # проблема
            ]
        )

        result = await classifier.classify(batch)

        assert len(result) == 1
        r0 = result[0]
        assert r0["district"] == "district3"
        assert r0["topic"] == "topic3"
        assert r0["problem"] == "text3"
        assert r0["difficult"] == 5

        mock_model.filter.assert_awaited_once_with(["text1", "text2", "text3"])


@pytest.mark.asyncio
async def test_pipeline_classify_returns_empty_when_all_filtered():
    with patch("pipeline.classifier.rubert.RuBERT") as mock_rubert_cls:
        mock_model = MagicMock()
        mock_model.filter = AsyncMock(
            return_value=[LabelsEnum.NOT_PROBLEM, LabelsEnum.SMALL]
        )
        mock_rubert_cls.get_instance.return_value = mock_model

        classifier = RuBERTClassifier()

        batch = Batch(
            items=[
                Item("d1", "t1", "text1"),
                Item("d2", "t2", "text2"),
            ]
        )

        result = await classifier.classify(batch)

        assert result == []


@pytest.mark.asyncio
async def test_pipeline_classify_maps_labels_and_items_one_to_one():
    with patch("pipeline.classifier.rubert.RuBERT") as mock_rubert_cls:
        mock_model = MagicMock()
        mock_model.filter = AsyncMock(return_value=[2, 3, 4])
        mock_rubert_cls.get_instance.return_value = mock_model

        classifier = RuBERTClassifier()

        batch = Batch(
            items=[
                Item("d1", "t1", "text1"),
                Item("d2", "t2", "text2"),
                Item("d3", "t3", "text3"),
            ]
        )

        result = await classifier.classify(batch)

        assert len(result) == 3
        assert [r["difficult"] for r in result] == [2, 3, 4]
        assert [r["problem"] for r in result] == ["text1", "text2", "text3"]

        mock_model.filter.assert_awaited_once_with(["text1", "text2", "text3"])