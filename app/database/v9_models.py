from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint

from app.database.database import Base


class ProductMatchReview(Base):
    __tablename__ = "product_match_reviews"
    __table_args__ = (
        UniqueConstraint("raw_product_id", "status", name="uq_match_review_raw_status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    raw_product_id = Column(Integer, ForeignKey("raw_products.id"), nullable=False, index=True)
    candidate_global_product_id = Column(Integer, ForeignKey("global_products.id"), nullable=True, index=True)
    proposed_identity_key = Column(String, nullable=True, index=True)
    confidence = Column(Float, nullable=False, default=0)
    reasons_json = Column(Text, nullable=True)
    conflicts_json = Column(Text, nullable=True)
    identifiers_json = Column(Text, nullable=True)
    status = Column(String, default="PENDING", nullable=False, index=True)
    decision_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
