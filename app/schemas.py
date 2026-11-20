from typing import Optional, List, Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")

class StandardResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    error: Optional[str] = None

# Category
class CategoryDto(BaseModel):
    id: str
    slug: str
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    displayOrder: Optional[int] = 0
    moduleCount: Optional[int] = 0

# Tag
class TagDto(BaseModel):
    id: str
    slug: str
    name: str

# Category Summary in Module
class ModuleCategorySummary(BaseModel):
    id: Optional[str] = None
    slug: str
    name: str
    icon: Optional[str] = None

# File Object
class ModuleFileItem(BaseModel):
    id: Optional[str] = None
    fileName: str
    filePath: str
    content: str
    language: str = "typescript"
    isEntry: bool = False

# Version Object
class ModuleVersionItem(BaseModel):
    id: Optional[str] = None
    version: str
    changelog: Optional[str] = None
    files: Optional[List[ModuleFileItem]] = None

# Documentation Object
class ModuleDocumentation(BaseModel):
    overview: Optional[str] = None
    installation: Optional[str] = None
    apiReference: Optional[str] = None
    integrationExample: Optional[str] = None

# Module Summary for List & Featured
class ModuleSummaryItem(BaseModel):
    id: str
    slug: str
    name: str
    shortDescription: Optional[str] = None
    framework: str
    language: str
    status: str
    latestVersion: Optional[str] = "1.0.0"
    downloadCount: int = 0
    category: Optional[ModuleCategorySummary] = None
    tags: List[TagDto] = []

# Paginated Result
class ModuleListResult(BaseModel):
    total: int
    page: int
    totalPages: int
    limit: int
    items: List[ModuleSummaryItem]

# Detail Page Object
class ModuleDetailItem(BaseModel):
    id: str
    slug: str
    name: str
    shortDescription: Optional[str] = None
    description: Optional[str] = None
    framework: str
    language: str
    status: str
    downloadCount: int = 0
    category: Optional[ModuleCategorySummary] = None
    tags: List[TagDto] = []
    currentVersion: Optional[ModuleVersionItem] = None
    documentation: Optional[ModuleDocumentation] = None

# Upload Request Payload
class ModuleUploadPayload(BaseModel):
    name: str = Field(..., min_length=1)
    slug: str = Field(..., min_length=1)
    categoryId: str = Field(..., min_length=1)
    shortDescription: str = Field(..., min_length=1)
    description: Optional[str] = None
    framework: str = "React"
    language: str = "TypeScript"
    version: str = "1.0.0"
    tags: Optional[List[str]] = []
    files: List[ModuleFileItem] = Field(..., min_length=1)
    overview: Optional[str] = None
    installation: Optional[str] = None
    apiReference: Optional[str] = None
    integrationExample: Optional[str] = None

# Upload Response Data
class CreatedModuleResponse(BaseModel):
    id: str
    slug: str
    name: str

# Platform Stats
class PlatformStats(BaseModel):
    publishedModules: int
    totalDownloads: int
