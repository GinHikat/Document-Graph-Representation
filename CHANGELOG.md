# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-01-06

### Added
- Comprehensive backend test suite (40 tests, 100% pass rate)
  - 13 authentication endpoint tests
  - 17 document management tests
  - 10 RAG query and retrieval tests
- Test coverage reporting (69% coverage)
- Testing documentation at `docs/testing.md`
- System architecture diagrams (C4 model, sequence diagrams, use case diagrams)
- Detailed test implementation plans and analysis reports
- Support for i18n in frontend (English/Vietnamese)

### Fixed
- Syntax error in `rag_model/model/Final_pipeline/final_doc_processor.py`
- Authentication error handling improvements
- Frontend language switcher functionality

### Changed
- Updated `README.md` with comprehensive testing instructions
- Enhanced `docs/development-guide.md` with detailed test commands
- Improved API configuration centralization
- Better error handling in auth middleware

### Documentation
- Added `docs/testing.md` - Complete testing guide
- Added `docs/architecture-diagrams.md` - System architecture documentation
- Added test implementation plans
- Added code review reports for test suite

## [0.9.0] - 2025-12-16

### Added
- React frontend with TypeScript
- FastAPI backend with comprehensive REST API
- Knowledge graph visualization
- Document management interface
- Q&A interface with RAG capabilities
- Admin dashboard
- Authentication system with JWT
- Stats router for system metrics

### Documentation
- `docs/system-architecture.md` - System architecture
- `docs/api-reference.md` - API documentation
- `docs/deployment-guide.md` - Deployment instructions
- `docs/frontend-guide.md` - Frontend development guide
- `docs/development-guide.md` - Development workflow

## [0.8.0] - 2025-12-10

### Added
- BAAI/bge-m3 embedding model for evaluation
- `embedding_as_judge` parameter to evaluation function

### Changed
- Improved evaluation metrics
- Enhanced retrieval pipeline

## Earlier Versions

See git history for earlier changes.

---

## Versioning Convention

- **Major version** (x.0.0): Breaking changes, major architectural changes
- **Minor version** (0.x.0): New features, backward-compatible changes
- **Patch version** (0.0.x): Bug fixes, documentation updates

## Categories

- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security fixes
- **Documentation**: Documentation changes
