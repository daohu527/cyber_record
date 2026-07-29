#!/usr/bin/env python

"""Canonical data models for format conversion."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SchemaDef:
    """Schema descriptor in canonical model."""
    name: str
    encoding: str
    data: bytes


@dataclass
class ChannelDef:
    """Channel descriptor in canonical model."""
    topic: str
    message_type: str
    schema: Optional[SchemaDef] = None


@dataclass
class MessageEnvelope:
    """Message payload in canonical model."""
    topic: str
    log_time: int
    publish_time: int
    data: bytes


@dataclass
class FileStats:
    """File-level summary in canonical model."""
    message_count: int
    channel_count: int
    begin_time: int
    end_time: int
