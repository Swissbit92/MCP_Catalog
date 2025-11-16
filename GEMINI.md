# Project Overview

This project is a local, persona-driven chat interface for interacting with GraphRAG and other MCP (Modular Computation Process) servers. It is built with Python and uses React for the frontend, FastAPI for the backend, and Ollama for local LLM inference. The application allows users to select from a variety of personas and have conversations with them through an advanced gacha-style character selection system.

The project is structured as follows:

*   `run_react.py`: The main entry point for the application. It starts both the FastAPI coordinator and the React UI.
*   `src/coordinator/server.py`: The FastAPI backend that handles chat, greetings, persona CV summaries, and chat persistence using SQLite.
*   `react-ui/`: The React frontend that provides a modern, gacha-style character selection and chat interface.
*   `personas/`: A directory containing JSON files that define the different personas available in the application.
*   `requirements.txt`: A file that lists the Python dependencies for the project.

# Building and Running

To build and run the project, follow these steps:

1.  **Install the dependencies:**

    ```
    pip install -r requirements.txt
    cd react-ui && npm install && cd ..
    ```

2.  **Create a `.env` file:**

    Create a `.env` file in the root of the project with the following content:

    ```
    COORD_PORT=8000
    COORD_URL=http://127.0.0.1:8000
    OLLAMA_BASE=http://127.0.0.1:11434
    PERSONA_MODEL=llama3.1:latest
    PERSONA_DIR=personas
    ```

3.  **Run the application:**

    ```
    python run_react.py
    ```

This will start both the FastAPI coordinator (backend) and the React UI (frontend). You can then access the UI in your browser at `http://localhost:3000`.

# Development Conventions

*   The project uses a modular architecture, with the frontend and backend separated into different directories.
*   The backend uses FastAPI and the frontend uses React with TypeScript.
*   Personas are defined in JSON files in the `personas/` directory.
*   The project uses a `.env` file for configuration.
*   The `run_react.py` script is the main entry point for the application, starting both backend and frontend.
*   The React UI features a gacha-style character selection system with classic cards, audio integration, and collection management.
*   Code follows TypeScript strict mode with comprehensive testing using Jest and React Testing Library.
