# Faculty Research Opportunity Notifier (PI rate research)

This project is an AI-driven multi-agent system designed to connect university faculty with relevant research funding opportunities. The system proactively identifies new grants, matches them to faculty expertise, generates preliminary research ideas, and suggests potential collaborators.

## Architecture Overview

The system is built as a Python **FastAPI** application, designed for scalability and containerization with **Docker**.

It employs a multi-agent architecture where specialized agents collaborate to perform the full workflow. Agent-to-agent (A2A) communication is intended to be handled by the **Google Agent Development Kit (ADK)**, with agents exposing their capabilities via the **Model Context Protocol (MCP)** for standardized tool calling.

## Repository Structure

The project follows a standard Python application layout:

```
.
├── .dockerignore
├── .gitignore
├── Dockerfile
├── README.md
├── development_checklist.yaml
├── requirements.txt
├── data/
│   ├── raw/          # Raw, unprocessed data from scrapers
│   └── processed/    # Cleaned, structured data for agents
├── src/
│   ├── __init__.py
│   ├── main.py       # FastAPI application entry point
│   ├── agents/       # Core logic for each specialized agent
│   ├── core/         # Core components like Pydantic models, A2A config
│   └── tools/        # Reusable tools (e.g., web scrapers, API clients)
└── tests/
    ├── __init__.py
    ├── mock_data/    # Static HTML/JSON for testing scrapers/parsers
    ├── agents/
    ├── core/
    └── tools/
```

## Data Flow

The data flows through the system in a pipeline, orchestrated by the agents. Each step enriches the data for the next agent in the chain.

```
graph TD
    subgraph Ingestion Phase
        A[Funding Websites e.g., NIH, PCORI] -->|HTTP Request| B(Scraper Tools);
        C[Faculty Sources e.g., Google Scholar] -->|API/HTTP Request| D(Faculty Finder Tools);
        B --> E{Ingestion Agent};
        D --> E;
        E -->|Writes Raw JSON| F[Raw Data Storage: data/raw/];
    end

    subgraph Analysis & Generation Phase
        F --> G{Matcher Agent with Multi-Dimensional Scoring};
        G -->|Scored Matches| H{Idea Generation Agent};
        G -->|Scored Matches| I{Collaborator Suggestion Agent};
        H -->|Conservative/Innovative/Stretch Variants + Budget/Timeline| J[Enriched Data Object];
        I -->|Finds Collaborators| J;
    end

    subgraph Dashboard & Export Phase
        J --> P{Admin Dashboard};
        J --> Q{Export Tools};
        P -->|Analytics & Monitoring| R[System Metrics];
        Q -->|Formatted Proposals| S[Export Outputs];
    end

    subgraph Notification Phase
        J --> K{Notification Agent};
        K -->|Composes Email| L[Formatted Notification];
        L -->|Sends via Email Service| M((Faculty Member));
    end

    subgraph API & A2A Layer
        N[FastAPI Endpoint: /run-analysis] -->|Triggers| E;
        E -.->|A2A Message| G;
        G -.->|A2A Message| H;
        G -.->|A2A Message| I;
        H & I -.->|A2A Message| K;
    end

    style F fill:#f9f,stroke:#333,stroke-width:2px
    style J fill:#ccf,stroke:#333,stroke-width:2px
    style L fill:#cfc,stroke:#333,stroke-width:2px
```

## Setup and Usage

1. **Install Dependencies:**
  
  ```
  pip install -r requirements.txt
  ```
  
2. Run Tests:
  
  Ensure all components are working as expected.
  
  ```
  pytest
  ```
  
3. Start the Application:
  
  This will start the Uvicorn server.
  
  ```
  uvicorn src.main:app --reload
  ```
  
  The API will be available at `http://127.0.0.1:8000`.
  

## Containerization

Build and run the application using Docker:

1. **Build the image:**
  
  ```
  docker build -t research-agent-system .
  ```
  
2. **Run the container:**
  
  ```
  docker run -p 8000:8000 research-agent-system
  ```
