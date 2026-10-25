"""Strict request base and common reason contract."""

from pydantic import BaseModel, Field, ConfigDict


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Reason(Strict):
    reason: str = Field(min_length=10, max_length=1000)
