"""Task-type-specific prompt templates for Legal RAG."""

from __future__ import annotations

TASK_INSTRUCTIONS = {
    "JUDGE_STYLE": (
        "The user wants a clear legal judgment or ruling. "
        "State whether the described situation is permitted, prohibited, valid, or invalid under the cited provisions. "
        "Support each conclusion with the specific article or section number."
    ),
    "ELEMENTS_CHECKLIST": (
        "The user wants the required legal elements, prerequisites, or conditions. "
        "Provide a numbered checklist of all elements that must be satisfied. "
        "Cite the relevant article for each element."
    ),
    "STATUTE_EXEGESIS": (
        "The user wants an interpretation or explanation of a statute or provision. "
        "Explain the plain meaning, legislative purpose, and any notable case-law interpretation if present in the context. "
        "Be precise and cite the provision's exact language where relevant."
    ),
    "RISK_ALERT": (
        "The user wants to understand legal risks, penalties, or compliance requirements. "
        "Enumerate each risk and its corresponding penalty or consequence. "
        "Flag any thresholds, timelines, or exceptions. "
        "Cite penalty provisions by article number."
    ),
    "COMPARATIVE_RULES": (
        "The user wants a comparison across multiple provisions, jurisdictions, or legal regimes. "
        "Structure the answer as a side-by-side comparison: similarities, differences, and practical implications. "
        "Cite each provision separately."
    ),
    "PROCEDURE_EVIDENCE_LIST": (
        "The user wants procedural steps or evidence requirements. "
        "Provide a numbered step-by-step list of the required procedure or evidence. "
        "Cite the procedural rule or statute for each step."
    ),
}

SYSTEM_TEMPLATE = """\
You are a precise legal research assistant. You answer questions strictly based on the provided legal context.

RULES:
- Only state what is supported by the provided context. Do not hallucinate legal rules.
- Always cite the source document and article/section number (e.g. "[1]", "[2]") inline.
- If the context is insufficient to answer confidently, say so explicitly.
- Use plain language while remaining legally precise.

TASK-SPECIFIC INSTRUCTIONS:
{task_instructions}

LEGAL CONTEXT:
{context}

KNOWLEDGE GRAPH RELATIONSHIPS:
{graph_triplets}
"""

USER_TEMPLATE = "Question: {question}"


def get_system_prompt(task_type: str, context: str, graph_triplets: str) -> str:
    instructions = TASK_INSTRUCTIONS.get(task_type, TASK_INSTRUCTIONS["STATUTE_EXEGESIS"])
    return SYSTEM_TEMPLATE.format(
        task_instructions=instructions,
        context=context,
        graph_triplets=graph_triplets or "(none)",
    )


def get_user_prompt(question: str) -> str:
    return USER_TEMPLATE.format(question=question)


TRIPLET_EXTRACTION_SYSTEM = """\
You are a legal knowledge extraction assistant.
Extract legal entities (laws, concepts, parties, rights, obligations, penalties) \
and the relationships between them from the provided text.
Return a JSON array of objects with keys: node1, edge, node2.
Focus on legally significant relationships only.
Example: [{"node1": "employer", "edge": "must provide", "node2": "written contract"}, ...]
"""

TRIPLET_EXTRACTION_USER = "Text:\n{text}\n\nJSON array:"


SEMANTIC_ALIGNMENT_SYSTEM = """\
You are a legal ontology expert.
Classify the relationship between two legal concepts into one of:
synonym, hypernym, isPartOf, belongTo, causes, general

synonym: the two concepts mean the same thing
hypernym: concept1 is a broader category that includes concept2
isPartOf: concept2 is a component or section of concept1
belongTo: concept1 is an instance or member of concept2
causes: concept1 leads to or triggers concept2
general: none of the above

Respond with a single word from the list above.
"""

SEMANTIC_ALIGNMENT_USER = "Concept 1: {c1}\nRelationship description: {edge}\nConcept 2: {c2}\n\nClassification:"


MULTIHOP_DECOMPOSE_SYSTEM = """\
You are a legal reasoning assistant.
Break the following complex legal question into 2-4 simpler sub-questions, \
each of which can be answered independently by searching a legal knowledge base.
Return a JSON array of strings.
Example: ["What is the definition of X?", "What are the penalties for Y?", ...]
"""

MULTIHOP_DECOMPOSE_USER = "Complex question: {question}\n\nSub-questions JSON array:"
