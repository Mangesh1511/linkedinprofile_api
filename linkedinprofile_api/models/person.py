"""
Pydantic data models for LinkedIn Person profile information.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class Experience(BaseModel):
    """Represents a work experience entry."""
    position_title: str = Field(..., description="Job title / position")
    institution_name: str = Field(..., description="Company / organization name")
    from_date: Optional[str] = Field(None, description="Start date (e.g. Jul 2024)")
    to_date: Optional[str] = Field(None, description="End date (e.g. Present)")
    duration: Optional[str] = Field(None, description="Duration (e.g. 1 yr 2 mos)")
    location: Optional[str] = Field(None, description="Job location")
    description: Optional[str] = Field(None, description="Description of responsibilities")


class Education(BaseModel):
    """Represents an education entry."""
    institution_name: str = Field(..., description="School / University / College name")
    degree: Optional[str] = Field(None, description="Degree or field of study")
    from_date: Optional[str] = Field(None, description="Start date")
    to_date: Optional[str] = Field(None, description="End date")
    description: Optional[str] = Field(None, description="Additional education summary or grade")


class Accomplishment(BaseModel):
    """Represents a certification, award, publication, or honor."""
    category: str = Field(..., description="Category (Certification, Award, Publication, etc.)")
    title: str = Field(..., description="Title of accomplishment")
    issuer: Optional[str] = Field(None, description="Issuing organization")


class Interest(BaseModel):
    """Represents an interest or followed entity."""
    name: str = Field(..., description="Name of interest")
    category: Optional[str] = Field("General", description="Category")


class Contact(BaseModel):
    """Represents contact info entry."""
    type: str = Field(..., description="Contact type (Email, Phone, LinkedIn, etc.)")
    value: str = Field(..., description="Contact detail value")


class Person(BaseModel):
    """Represents complete scraped LinkedIn person profile."""
    linkedin_url: str = Field(..., description="Canonical LinkedIn profile URL")
    name: str = Field(..., description="Full name of person")
    headline: Optional[str] = Field(None, description="Professional headline")
    location: Optional[str] = Field(None, description="Location")
    profile_picture_url: Optional[str] = Field(None, description="Profile picture URL")
    connections: Optional[str] = Field(None, description="Connections count")
    about: Optional[str] = Field(None, description="About summary bio")
    open_to_work: bool = Field(False, description="True if open to work banner is detected")
    experiences: List[Experience] = Field(default_factory=list)
    educations: List[Education] = Field(default_factory=list)
    interests: List[Interest] = Field(default_factory=list)
    accomplishments: List[Accomplishment] = Field(default_factory=list)
    contacts: List[Contact] = Field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert person object to serializable dictionary."""
        return self.model_dump()
