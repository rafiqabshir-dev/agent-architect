"""State definition for the autonomous content generation graph."""

from __future__ import annotations
from typing import TypedDict, NotRequired


class AutonomousState(TypedDict, total=False):
    """State object for the autonomous graph pipeline.

    Tracks content through generation, compliance checking, and publishing.
    """

    # Client and session context
    client_id: str
    client_config: dict

    # Content generation
    content: str
    content_type: str
    channel: str

    # Provider targeting (outreach)
    target_provider: dict
    outreach_type: str
    subject_line: str | None
    talking_points: list[str] | None

    # Compliance
    compliance_result: dict
    revision_count: int

    # DME compliance (Feature 2)
    dme_compliance_result: dict
    dme_revision_count: int

    # Publishing
    publish_queue_id: str
    status: str

    # Error tracking
    error: str | None
