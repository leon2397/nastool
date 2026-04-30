# -*- coding: utf-8 -*-
"""
schemas/health_weights.py - Pydantic models for health_weights.yaml validation
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class WeightEntry(BaseModel):
    """Single check weight definition"""
    weight: float = Field(default=1.0, ge=0, le=10.0, description="检查项权重")
    description: str = Field(default="", description="权重说明")


class ScoreLevel(BaseModel):
    """Score level threshold definition"""
    threshold: int = Field(ge=0, le=100, description="分数阈值")
    label: str = Field(min_length=1, description="等级标签")
    name: str = Field(default="", description="等级中文名")
    desc: str = Field(default="", description="等级描述")


class DefaultWeightConfig(BaseModel):
    """Default weight and base_score settings"""
    weight: float = Field(default=1.0, ge=0, le=10.0)
    base_score: Dict[str, int] = Field(
        default={
            "passed": 100,
            "warning": 65,
            "critical": 0,
            "info": 100,
        },
        description="各状态基础分",
    )


class HealthWeightsConfig(BaseModel):
    """Root configuration model for health_weights.yaml"""
    weights: Dict[str, float] = Field(
        default_factory=dict,
        description="检查项权重映射 {check_id: weight}",
    )
    default: DefaultWeightConfig = Field(default_factory=DefaultWeightConfig)
    score_levels: List[ScoreLevel] = Field(default_factory=list)
