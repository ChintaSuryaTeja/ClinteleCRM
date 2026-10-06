"""Shapes of request and response bodies. Pydantic validates incoming JSON against these."""

from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field

from app.models import Role

# Emails are compared case-insensitively, so store them lowercased.
Email = Annotated[EmailStr, AfterValidator(str.lower)]
Password = Annotated[str, Field(min_length=8, max_length=128)]


class SignupIn(BaseModel):
    organization_name: str = Field(min_length=1, max_length=200)
    email: Email
    password: Password


class LoginIn(BaseModel):
    email: Email
    password: str


class UserCreateIn(BaseModel):
    email: Email
    password: Password
    role: Role


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: Role
    created_at: datetime


class MeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: Role
    organization: OrganizationOut
