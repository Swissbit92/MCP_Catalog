# src/coordinator/tools_spec.py
TOOLS_SPEC = [
    {
        "name": "call_rag_qa",
        "description": "Answer a question using GraphRAG with citations.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "k": {"type": "integer", "default": 8},
                "entity_ids": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["question"]
        }
    },
    {
        "name": "call_rag_search",
        "description": "Semantic search in the RAG store.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "k": {"type": "integer", "default": 8}
            },
            "required": ["text"]
        }
    },
    {
        "name": "call_kg_sparql",
        "description": "Query the Knowledge Graph via SPARQL.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"]
        }
    },
    # Placeholder for future Brave MCP wiring
    {
        "name": "call_brave_search",
        "description": "Web search (Brave MCP). Use when up-to-date info is required.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}, "count": {"type": "integer", "default": 5}},
            "required": ["query"]
        }
    }
]
