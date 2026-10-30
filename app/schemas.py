from typing import Optional, List, Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")

class StandardResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    error: Optional[str] = None

class CategoryDto(BaseModel):
    id: str
    slug: str
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    displayOrder: Optional[int] = 0
    moduleCount: Optional[int] = 0

class ModuleCategorySummary(BaseModel):
    id: Optional[str] = None
    name: str
    slug: str
    icon: Optional[str] = None

class ModuleSummaryItem(BaseModel):
    id: str
    slug: str
    name: str
    shortDescription: Optional[str] = None
    framework: str
    language: str
    status: str
    downloadCount: int = 0
    latestVersion: Optional[str] = "1.0.0"
    category: Optional[ModuleCategorySummary] = None
    createdAt: Optional[Any] = None
    updatedAt: Optional[Any] = None

class ModuleListResult(BaseModel):
    items: List[ModuleSummaryItem]
    total: int
    page: int
    totalPages: int

class ModuleFileItem(BaseModel):
    id: Optional[str] = None
    fileName: str
    filePath: str
    content: str
    language: str = "typescript"
    isEntry: bool = False

class ModuleUploadPayload(BaseModel):
    name: str = Field(..., min_length=1)
    slug: Optional[str] = None
    categoryId: str = Field(..., min_length=1)
    shortDescription: Optional[str] = None
    description: Optional[str] = None
    framework: str = "React"
    language: str = "TypeScript"
    version: str = "1.0.0"
    tags: Optional[List[str]] = []
    files: List[ModuleFileItem] = Field(..., min_length=1)

class PlatformStats(BaseModel):
    publishedModules: int
    totalDownloads: int

class CreatedModuleResponse(BaseModel):
    id: str
    slug: str

