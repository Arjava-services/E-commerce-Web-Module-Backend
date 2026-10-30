-- ============================================================================
-- E-Commerce Web Module Platform - Minimal 5-Core-Table Database Schema
-- Compatible with PostgreSQL 13+ (Uses pgcrypto / gen_random_uuid())
-- ============================================================================

-- 0. Enable UUID generation extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. categories
-- Stores catalog categories for module classification and navigation
CREATE TABLE IF NOT EXISTS categories (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    icon TEXT,
    "displayOrder" INTEGER NOT NULL DEFAULT 0,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. modules
-- Core module entity containing metadata, category linkage, framework, and stats
CREATE TABLE IF NOT EXISTS modules (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    "shortDescription" TEXT,
    description TEXT,
    "categoryId" TEXT NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'PUBLISHED',
    framework TEXT NOT NULL,
    language TEXT NOT NULL,
    "downloadCount" INTEGER NOT NULL DEFAULT 0,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. module_versions
-- Release versions for each module with changelog and active/latest flag
CREATE TABLE IF NOT EXISTS module_versions (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    "moduleId" TEXT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    version TEXT NOT NULL,
    changelog TEXT,
    "isLatest" BOOLEAN NOT NULL DEFAULT true,
    status TEXT NOT NULL DEFAULT 'PUBLISHED',
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_module_version UNIQUE ("moduleId", version)
);

-- 4. module_files
-- Source code files belonging to a specific module version
CREATE TABLE IF NOT EXISTS module_files (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    "moduleVersionId" TEXT NOT NULL REFERENCES module_versions(id) ON DELETE CASCADE,
    "filePath" TEXT NOT NULL,
    "fileName" TEXT NOT NULL,
    language TEXT NOT NULL,
    content TEXT NOT NULL,
    "isEntry" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. tags & module_tags
-- Multi-tag categorization system
CREATE TABLE IF NOT EXISTS tags (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS module_tags (
    "moduleId" TEXT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    "tagId" TEXT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY ("moduleId", "tagId")
);

-- ============================================================================
-- Indexes for High Performance Querying
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_categories_slug ON categories(slug);
CREATE INDEX IF NOT EXISTS idx_categories_display_order ON categories("displayOrder");

CREATE INDEX IF NOT EXISTS idx_modules_slug ON modules(slug);
CREATE INDEX IF NOT EXISTS idx_modules_category_id ON modules("categoryId");
CREATE INDEX IF NOT EXISTS idx_modules_status ON modules(status);
CREATE INDEX IF NOT EXISTS idx_modules_framework ON modules(framework);
CREATE INDEX IF NOT EXISTS idx_modules_download_count ON modules("downloadCount" DESC);
CREATE INDEX IF NOT EXISTS idx_modules_updated_at ON modules("updatedAt" DESC);

CREATE INDEX IF NOT EXISTS idx_module_versions_module_id ON module_versions("moduleId");
CREATE INDEX IF NOT EXISTS idx_module_versions_latest ON module_versions("moduleId", "isLatest");

CREATE INDEX IF NOT EXISTS idx_module_files_version_id ON module_files("moduleVersionId");
CREATE INDEX IF NOT EXISTS idx_tags_slug ON tags(slug);
CREATE INDEX IF NOT EXISTS idx_module_tags_module_id ON module_tags("moduleId");
CREATE INDEX IF NOT EXISTS idx_module_tags_tag_id ON module_tags("tagId");

