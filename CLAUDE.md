# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the Faculty Research Opportunity Notifier (PI rate research) - an AI-driven multi-agent system that connects university faculty with relevant research funding opportunities. The system uses a FastAPI backend with a multi-agent architecture where specialized agents collaborate through Google Agent Development Kit (ADK) and Model Context Protocol (MCP).

## Development Commands

### Environment Setup
```bash
pip install -r requirements.txt
```

### Running the Application
```bash
uvicorn src.main:app --reload
```
The API will be available at `http://127.0.0.1:8000`.

### Testing
```bash
pytest
```

### Docker Commands
```bash
# Build the image
docker build -t research-agent-system .

# Run the container
docker run -p 8000:8000 research-agent-system
```

## Architecture Overview

The system follows a multi-agent pipeline architecture:

1. **Ingestion Agent** - Scrapes funding opportunities (NIH, PCORI) and faculty data (Google Scholar)
2. **Matcher Agent** - Multi-dimensional scoring system (deadline urgency, career stage, methodology alignment)
3. **Idea Generation Agent** - Generates 3 proposal variants (conservative/innovative/stretch) with budget/timeline estimates
4. **Collaborator Suggestion Agent** - Identifies potential collaborators
5. **Notification Agent** - Formats and prepares email notifications
6. **Admin Dashboard** - System monitoring, analytics, and configuration management
7. **Export Tools** - Formatted proposal outlines and collaboration introductions

Data flows from `data/raw/` through multi-dimensional analysis to dashboard analytics and notifications.

## Project Structure

- `src/main.py` - FastAPI application entry point
- `src/agents/` - Core agent implementations
- `src/core/` - Pydantic models, scoring systems, analytics, and configuration management
- `src/tools/` - Reusable tools (scrapers, API clients, exporters)
- `src/dashboard/` - Admin dashboard and monitoring interfaces
- `data/raw/` - Raw scraped data storage
- `data/processed/` - Cleaned, structured data
- `config/` - Institution-specific configuration templates
- `tests/` - Test files with comprehensive mock data in `tests/mock_data/`
- `development_checklist.yaml` - Comprehensive development task tracking (7 phases)

## Development Notes

The project uses a detailed development checklist (`development_checklist.yaml`) that tracks all tasks with status, prerequisites, and testing requirements. This serves as the single source of truth for development progress.

### Testing Requirements
**CRITICAL**: Every new component must have comprehensive pytest tests with mock data. When implementing any task from the checklist:
1. Create the corresponding test file as specified in the task's testing section
2. Generate mock input data files in `tests/mock_data/` as detailed in each task
3. Mock all external API calls (LLM APIs, web scrapers, etc.)
4. Test both positive and negative cases for data validation
5. Ensure tests can run in isolation without external dependencies

### Agent Communication Architecture
The system is designed for future Agent-to-Agent (A2A) communication using Google ADK and MCP protocol (Phase 5). Current MVP uses direct function calls, but the architecture supports:
- `src/core/a2a_config.py` - A2A communication setup
- MCP protocol integration for standardized tool calling
- Plugin architecture for research automation modules

Key technologies: FastAPI, Pydantic, BeautifulSoup4, pytest, Google Generative AI, with planned integration of Google ADK and MCP protocol for agent communication.