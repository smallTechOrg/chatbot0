"""
Domains feature module.

Public surface
--------------
- ``DomainRepository``  – data access layer
- ``DomainService``     – business logic layer
- Domain-specific exceptions for use in the controller layer
"""
from domains.repository import DomainRepository
from domains.service import (
    DomainAlreadyExistsError,
    DomainService,
    InvalidWebsiteURLError,
    ParentDomainNotFoundError,
)

__all__ = [
    "DomainAlreadyExistsError",
    "DomainRepository",
    "DomainService",
    "InvalidWebsiteURLError",
    "ParentDomainNotFoundError",
]
