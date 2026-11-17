-- ============================================================================
-- E-Commerce Web Module Platform - MySQL 8.0+ Database Schema
-- ============================================================================

-- If creating a new database:
-- CREATE DATABASE IF NOT EXISTS moduleforge CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE moduleforge;

-- Or if using Arjava_module:
-- USE Arjava_module;

-- 1. categories
CREATE TABLE IF NOT EXISTS categories (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    slug VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    icon VARCHAR(100),
    `displayOrder` INT NOT NULL DEFAULT 0,
    `createdAt` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updatedAt` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. modules
CREATE TABLE IF NOT EXISTS modules (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    slug VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    `shortDescription` TEXT,
    description LONGTEXT,
    `categoryId` VARCHAR(36) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PUBLISHED',
    framework VARCHAR(100) NOT NULL,
    language VARCHAR(100) NOT NULL,
    `downloadCount` INT NOT NULL DEFAULT 0,
    `createdAt` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updatedAt` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_modules_category FOREIGN KEY (`categoryId`) REFERENCES categories(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. module_versions
CREATE TABLE IF NOT EXISTS module_versions (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    `moduleId` VARCHAR(36) NOT NULL,
    version VARCHAR(50) NOT NULL,
    changelog TEXT,
    `isLatest` BOOLEAN NOT NULL DEFAULT TRUE,
    status VARCHAR(50) NOT NULL DEFAULT 'PUBLISHED',
    `createdAt` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updatedAt` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_module_version UNIQUE (`moduleId`, version),
    CONSTRAINT fk_versions_module FOREIGN KEY (`moduleId`) REFERENCES modules(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. module_files
CREATE TABLE IF NOT EXISTS module_files (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    `moduleVersionId` VARCHAR(36) NOT NULL,
    `filePath` VARCHAR(500) NOT NULL,
    `fileName` VARCHAR(255) NOT NULL,
    language VARCHAR(100) NOT NULL,
    content LONGTEXT NOT NULL,
    `isEntry` BOOLEAN NOT NULL DEFAULT FALSE,
    `createdAt` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_files_version FOREIGN KEY (`moduleVersionId`) REFERENCES module_versions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. tags
CREATE TABLE IF NOT EXISTS tags (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    slug VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    `createdAt` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. module_tags
CREATE TABLE IF NOT EXISTS module_tags (
    `moduleId` VARCHAR(36) NOT NULL,
    `tagId` VARCHAR(36) NOT NULL,
    PRIMARY KEY (`moduleId`, `tagId`),
    CONSTRAINT fk_modtags_module FOREIGN KEY (`moduleId`) REFERENCES modules(id) ON DELETE CASCADE,
    CONSTRAINT fk_modtags_tag FOREIGN KEY (`tagId`) REFERENCES tags(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Indexes for High Performance
-- ============================================================================
CREATE INDEX idx_categories_slug ON categories(slug);
CREATE INDEX idx_categories_display_order ON categories(`displayOrder`);

CREATE INDEX idx_modules_slug ON modules(slug);
CREATE INDEX idx_modules_category_id ON modules(`categoryId`);
CREATE INDEX idx_modules_status ON modules(status);
CREATE INDEX idx_modules_framework ON modules(framework);
CREATE INDEX idx_modules_download_count ON modules(`downloadCount` DESC);
CREATE INDEX idx_modules_updated_at ON modules(`updatedAt` DESC);

CREATE INDEX idx_module_versions_module_id ON module_versions(`moduleId`);
CREATE INDEX idx_module_versions_latest ON module_versions(`moduleId`, `isLatest`);

CREATE INDEX idx_module_files_version_id ON module_files(`moduleVersionId`);
CREATE INDEX idx_tags_slug ON tags(slug);
CREATE INDEX idx_module_tags_module_id ON module_tags(`moduleId`);
CREATE INDEX idx_module_tags_tag_id ON module_tags(`tagId`);
