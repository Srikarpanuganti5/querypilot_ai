"""Bounded document metadata, search arguments, passages and citations."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DocumentCategory = Literal[
    "refunds",
    "shipping",
    "payments",
    "cancellations",
    "products",
    "support",
    "discounts",
    "fraud",
    "inventory",
    "faq",
]


class DocumentMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)
    document_id: str = Field(pattern=r"^QP-[A-Z]{2,12}-[0-9]{3}$")
    title: str = Field(min_length=1, max_length=120)
    category: DocumentCategory


class DocumentSearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    query: str = Field(min_length=1, max_length=500, strict=True)
    top_k: int = Field(default=5, ge=1, le=10, strict=True)
    category: DocumentCategory | None = None

    @field_validator("query", mode="before")
    @classmethod
    def bound_raw_query(cls, value: object) -> object:
        if isinstance(value, str) and len(value) > 500:
            raise ValueError("Query exceeds the character limit")
        return value


class SearchHit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: str = Field(pattern=r"^QP-[A-Z]{2,12}-[0-9]{3}$")
    document_title: str = Field(min_length=1, max_length=120)
    category: DocumentCategory
    section: str = Field(min_length=1, max_length=200)
    excerpt: str = Field(min_length=1, max_length=1200)
    score: float = Field(gt=0, allow_inf_nan=False)
    source_citation: str = Field(pattern=r"^QP-[A-Z]{2,12}-[0-9]{3}#s[0-9]{3}-c[0-9]{3}$")

    @model_validator(mode="after")
    def matching_provenance(self) -> "SearchHit":
        if not self.source_citation.startswith(self.document_id + "#"):
            raise ValueError("Citation does not belong to the document")
        return self


class DocumentSearchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation: Literal["search_business_documents"] = "search_business_documents"
    matches: list[SearchHit] = Field(max_length=10)
    indexed_documents: int = Field(ge=0, le=50)
    indexed_chunks: int = Field(ge=0, le=500)
    content_trust: Literal["untrusted"] = "untrusted"

    @model_validator(mode="after")
    def unique_citations(self) -> "DocumentSearchOutput":
        citations = [hit.source_citation for hit in self.matches]
        if len(set(citations)) != len(citations):
            raise ValueError("Duplicate passage citations")
        return self
