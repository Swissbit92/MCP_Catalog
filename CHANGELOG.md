# Changelog

All notable changes to the MCP Catalog project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure with MCP Coordinator backend and React UI frontend
- Persona-based chat interface with multiple character options
- Gacha-style character selection with card reveal animations
- Static character browsing with search functionality
- FastAPI backend with Ollama LLM integration
- Comprehensive testing setup with Jest and pytest
- **Unified startup script** (`run_react.py`) that launches both backend and frontend together
- **CORS support** in FastAPI for cross-origin requests from React UI
- **Header Component Enhancement (Phase 1)**: Modern dark theme header with rarity-based active page highlighting, responsive layout, and branding
- **Header Component Enhancement (Iteration 2.1)**: Added Framer Motion animations with entrance effects, hover interactions, and smooth transitions
- **Header Component Enhancement (Iteration 2.2)**: Implemented visible particle system, dynamic gradient theming with page-based color changes, enhanced glassmorphism, animated typography with glow effects, and prominent animated bottom border
- **Header Component Enhancement (Iteration 2.3)**: Added functional mobile hamburger menu with slide-out navigation, persona-aware theming that adapts to selected character, touch-optimized interactions, and mobile-specific UI enhancements
- **Phase 3: App-Wide Enhancements**: Completed character card visual effects with Framer Motion animations, polished chat interface with smooth scrolling and message animations, and comprehensive mobile optimization across the entire application
- **Chat UX Phase 3.1: Rich Media Support**: Added message timestamps, JSON syntax highlighting with collapsible display and copy buttons with visual feedback, code block highlighting with language detection and copy buttons with visual feedback, and RichContent component for intelligent content rendering
- **Chat UX Phase 3.2: Performance & Feedback**: Implemented latency tracking with response time display in ms/s, error recovery with retry functionality for failed messages, status indicators (sending, sent, delivered, failed) with loading spinners, message status management and retry counters, and React.memo performance optimizations
- **Copy Button Feature**: Added ChatGPT-style copy buttons for JSON responses and code blocks with visual feedback (copy icon → checkmark) and automatic reset after 2 seconds

### Changed
- **UI Flow Reorganization (2025-01-07)**: Moved pull mechanics to home page, simplified character selection to browsing-only
  - Home page (`/`) now handles all gacha pulls with card reveal animations
  - Character selection page (`/select`) now shows clean grid browsing with search
  - Removed "Ready to Pull?" interface from character selection page
  - Improved separation of concerns between pulling and browsing experiences
- **React Migration Completed**: Full migration from Streamlit to React UI with working chat functionality and comprehensive visual enhancements
- **Header Component Planning**: Documented phased approach for modern header redesign with vibrant colors and highlighting

### Technical Improvements
- Optimized React build (131KB gzipped) with enhanced animations and visual effects
- Fixed Jest configuration issues
- Updated TypeScript setup for better development experience
- Improved component architecture with better state management
- Added CORS middleware to FastAPI backend
- Enhanced error handling and user feedback in chat interface

### Fixed
- **Chat Session Creation**: Fixed double session creation when selecting new personas
- **Greeting Message Handling**: Fixed greeting messages appearing as user input instead of assistant messages
- **Persona Mixing**: Fixed greeting messages being sent to wrong sessions when switching chats during loading
- **Input Blocking**: Added proper blocking of chat input until initial greeting messages are generated
- **Loading States**: Added visual feedback during session creation and greeting generation
- **Avatar Images**: Fixed avatar images disappearing when switching between chats and ensured proper use of dedicated avatar images instead of card images

### Documentation
- Updated README with new unified startup process and React UI focus
- Enhanced GACHA_UX_ROADMAP.md with current implementation status
- Added comprehensive coding guidelines in AGENTS.md
- Updated REACT.md to reflect completed migration
- Created this changelog for tracking project evolution

## [0.1.0] - 2025-01-XX

### Added
- Basic MCP Coordinator architecture
- React UI with routing (Home, Character Selection, Chat)
- Character card components with rarity styling
- API integration between frontend and backend
- Basic testing infrastructure

### Technical
- React 19 with TypeScript
- FastAPI backend
- Ollama LLM integration
- Framer Motion animations
- Jest testing framework

---

## Types of changes
- `Added` for new features
- `Changed` for changes in existing functionality
- `Deprecated` for soon-to-be removed features
- `Removed` for now removed features
- `Fixed` for any bug fixes
- `Security` in case of vulnerabilities</content>
<parameter name="filePath">CHANGELOG.md