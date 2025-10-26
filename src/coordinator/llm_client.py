# src/coordinator/llm_client.py
import requests
from typing import List, Dict, Any

class OllamaClient:
    def __init__(self, base: str = "http://localhost:11434", model: str = "llama3.1:8b"):
        self.base = base.rstrip("/")
        self.model = model

    def complete(self, system: str, user_prompt: str, temperature: float = 0.1, max_tokens: int | None = None) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": temperature},
        }
        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens

        r = requests.post(f"{self.base}/api/chat", json=payload, timeout=180)
        r.raise_for_status()
        data = r.json()
        return data["message"]["content"]

    def chat_with_tools(self, system: str, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Single-step router: ask the model to either produce a direct answer
        or emit a single tool call as strict JSON. Output protocol:
          - If answering directly:    "FINAL:\n<text>"
          - If calling a tool:        "TOOL:\n{\"name\":\"...\",\"arguments\":{...}}"
        Returns:
          {"text": "..."}  OR  {"tool": {"name": "...", "arguments": {...}}}
        """
        tool_block = (
            "Available tools (JSON Schemas):\n" +
            "\n".join([f"- {t['name']}: {t['description']}" for t in tools]) +
            "\n\n"
            "Output exactly one of the following:\n"
            "1) DIRECT ANSWER:\n"
            "   FINAL:\\n<your concise answer>\n\n"
            "2) A SINGLE TOOL CALL as strict JSON:\n"
            "   TOOL:\\n{\"name\":\"tool_name\",\"arguments\":{...}}\n\n"
            "Rules:\n"
            "- Prefer tools for factual/document/date-sensitive questions.\n"
            "- If small talk or opinion, answer directly.\n"
            "- Use only ONE tool call.\n"
            "- Do not include extra text before or after the required format.\n"
        )

        chat = [{"role": "system", "content": system}]
        chat.extend(messages)
        chat.append({"role": "user", "content": tool_block})

        r = requests.post(
            f"{self.base}/api/chat",
            json={"model": self.model, "messages": chat, "stream": False, "options": {"temperature": 0.1}},
            timeout=180,
        )
        r.raise_for_status()
        content = r.json()["message"]["content"].strip()

        if content.startswith("TOOL:"):
            import json as _json
            json_part = content[len("TOOL:"):].strip()
            tool = _json.loads(json_part)
            return {"tool": tool}
        elif content.startswith("FINAL:"):
            return {"text": content[len("FINAL:"):].strip()}
        else:
            # Fallback: treat as direct answer
            return {"text": content}
