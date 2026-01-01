# Golden Q&A Examples for RAGAS Evaluation

This directory contains golden question-answer pairs for evaluating persona response quality using the RAGAS (RAG Assessment) framework.

## Purpose

Golden Q&A examples serve as ground truth for measuring:
- **Faithfulness**: Is the persona's answer grounded in their context/lore?
- **Answer Relevancy**: Does the answer address the question?
- **Context Precision**: Is retrieved context relevant?
- **Context Recall**: Is all relevant context retrieved?

## File Format

Each persona has a `{persona_key}_golden_qa.json` file with the following structure:

```json
{
  "persona_key": "eeva",
  "persona_display_name": "Eeva",
  "version": "1.0",
  "created": "2026-01-01",
  "questions": [
    {
      "id": "eeva_q1",
      "category": "background",
      "question": "What is your background?",
      "ground_truth": "I'm Eeva, a senior solutions architect specializing in enterprise Kubernetes and cloud-native infrastructure.",
      "expected_topics": ["kubernetes", "cloud-native", "solutions architect"],
      "difficulty": "easy"
    }
  ]
}
```

## Field Descriptions

### Top-Level Fields
- **persona_key**: Matches persona JSON filename (e.g., "eeva" for `eeva.json`)
- **persona_display_name**: Human-readable name (e.g., "Eeva")
- **version**: Dataset version (semantic versioning: "1.0", "1.1", etc.)
- **created**: ISO 8601 date (YYYY-MM-DD)

### Question Fields
- **id**: Unique identifier (format: `{persona}_q{number}`)
- **category**: Question type (see categories below)
- **question**: The question text (what user would ask)
- **ground_truth**: Expected answer (reference for RAGAS evaluation)
- **expected_topics**: Keywords/topics that should appear in answer (list of strings)
- **difficulty**: Complexity level (`easy`, `medium`, `hard`)

## Question Categories

### 1. Background
Questions about persona identity, role, expertise.
- Example: "What is your background?"
- Example: "What do you specialize in?"

### 2. Technical
Domain-specific technical questions.
- Example: "How would you design a Kubernetes cluster for high availability?"
- Example: "Explain the strangler fig pattern."

### 3. Personality
Questions about behavior, preferences, communication style.
- Example: "How do you approach difficult problems?"
- Example: "What's your communication style?"

### 4. Lore
Questions about persona's fictional backstory/world.
- Example: "Tell me about your journey as an elf."
- Example: "What was your role in the Hero's Party?"

### 5. Scenario
Complex multi-step reasoning scenarios.
- Example: "A client's production cluster is down. Walk me through your troubleshooting process."
- Example: "How would you migrate a monolith to microservices?"

## Difficulty Levels

### Easy (3+ questions per persona)
- **Purpose**: Baseline quality check
- **Characteristics**:
  - Simple, direct questions
  - 1-2 sentence answers
  - Well-defined in persona JSON
- **Example**: "What is your name?" → "I'm Eeva."

### Medium (4+ questions per persona)
- **Purpose**: Standard persona interaction
- **Characteristics**:
  - Requires domain knowledge
  - 2-3 sentence answers
  - May require connecting multiple facts
- **Example**: "What's your expertise?" → "I specialize in enterprise Kubernetes, GitOps workflows, and service mesh architectures."

### Hard (3+ questions per persona)
- **Purpose**: Test persona limits
- **Characteristics**:
  - Complex scenarios
  - Multi-paragraph answers
  - Requires reasoning and synthesis
- **Example**: "How would you architect a multi-region Kubernetes platform?" → [Detailed architectural answer]

## Guidelines for Writing Golden Examples

### 1. Diversity
- **DO**: Cover all 5 categories (background, technical, personality, lore, scenario)
- **DO**: Include mix of easy/medium/hard questions (3/4/3 distribution)
- **DON'T**: Focus only on technical questions
- **DON'T**: Use only simple yes/no questions

### 2. Specificity
- **DO**: Write detailed ground truth answers
- **DO**: Use persona's voice and terminology
- **DON'T**: Write vague or generic answers
- **DON'T**: Copy verbatim from persona JSON (synthesize)

### 3. Realism
- **DO**: Write questions users would actually ask
- **DO**: Match conversation context (casual, not interview-style)
- **DON'T**: Write overly formal or academic questions
- **DON'T**: Ask meta questions ("Are you an AI?")

### 4. Quality
- **DO**: Proofread for spelling/grammar
- **DO**: Ensure ground_truth is factually correct per persona JSON
- **DON'T**: Include placeholder text like "TBD" or "TODO"
- **DON'T**: Use ambiguous language

## Example: Good vs. Bad Questions

### ❌ BAD: Too vague
```json
{
  "question": "Tell me about yourself",
  "ground_truth": "I'm a persona.",
  "difficulty": "easy"
}
```

### ✅ GOOD: Specific and testable
```json
{
  "question": "What is your background and area of expertise?",
  "ground_truth": "I'm Eeva, a senior solutions architect specializing in enterprise Kubernetes and cloud-native infrastructure. I have extensive experience with GitOps workflows, service mesh architectures, and platform engineering.",
  "expected_topics": ["solutions architect", "kubernetes", "cloud-native"],
  "difficulty": "easy"
}
```

### ❌ BAD: Yes/no question
```json
{
  "question": "Do you know Kubernetes?",
  "ground_truth": "Yes.",
  "difficulty": "easy"
}
```

### ✅ GOOD: Open-ended with substance
```json
{
  "question": "How would you approach migrating a monolithic application to microservices on Kubernetes?",
  "ground_truth": "I'd start with a strangler fig pattern, incrementally extracting services while maintaining the monolith. Key steps: identify bounded contexts, implement API gateways, set up service mesh for observability, use GitOps for deployments, and establish proper monitoring before cutting over traffic.",
  "expected_topics": ["strangler pattern", "microservices", "gitops", "monitoring"],
  "difficulty": "hard"
}
```

## Validation

After creating golden Q&A, validate using:

```python
from src.coordinator.evaluation import GoldenExamplesManager

manager = GoldenExamplesManager()
dataset = manager.load_dataset("eeva")
validation = manager.validate_dataset(dataset)

print(f"Valid: {validation['is_valid']}")
print(f"Warnings: {validation['warnings']}")
```

**Expected output:**
```
Valid: True
Warnings: []
```

## Baseline Metrics

After creating golden Q&A, run evaluation to establish baseline:

```bash
pytest tests/evaluation/test_persona_quality.py --persona=eeva -v
```

**Target scores** (based on venv_Projektarbeit benchmarks):
- Faithfulness: ≥0.85
- Answer Relevancy: ≥0.90
- Context Precision: ≥0.80
- Context Recall: ≥0.80
- F1 Score: ≥0.82

## File Checklist

- [ ] `eeva_golden_qa.json` (10 questions: 3 easy, 4 medium, 3 hard)
- [ ] `frieren_golden_qa.json` (10 questions: 3 easy, 4 medium, 3 hard)
- [ ] `gojo_golden_qa.json` (10 questions: 3 easy, 4 medium, 3 hard)

## Maintenance

**When to Update:**
- Persona JSON changes (lore, expertise, voice)
- New categories of questions emerge
- Baseline metrics drop (add more examples)
- Version bump: increment dataset version (e.g., 1.0 → 1.1)

**Version History:**
- v1.0 (2026-01-01): Initial dataset for RAGAS implementation
