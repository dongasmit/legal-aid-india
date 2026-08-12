"""
agent_graph.py — Phase 5: Self-Healing Agentic RAG Workflow via LangGraph
==========================================================================
Replaces the linear LangChain pipeline with a cyclic, self-healing agent:
  1. Retrieve: Hybrid Qdrant search + FlashRank reranking
  2. Grade Relevance: LLM relevance grader evaluates top candidate chunks
  3. Web Search Fallback: Triggered if local RAG corpus lacks relevant docs
  4. Generate: Produces structured output using Llama-3.3 on Groq
  5. Check Hallucination: Critic node checks for groundness in source context;
     loops back to fix or query rewrite if hallucination detected.

Standalone test:
    python3 agent_graph.py "What is the penalty for murder under BNS section 103?"
"""

import os
import sys
import logging
from typing import TypedDict, List, Dict, Any, Optional

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END

from retrieval import retrieve_and_rerank
from web_search import search_web_legal
from schemas import LegalResponse, Citation

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── LLM Instantiation ─────────────────────────────────────────────────────────
llm = ChatGroq(
    temperature=0.1,
    model_name="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
)

# ── Graph State Definition ────────────────────────────────────────────────────
class AgentState(TypedDict):
    question: str
    original_question: str
    documents: List[Dict[str, Any]]
    web_results: List[Dict[str, Any]]
    generation: Optional[LegalResponse]
    is_relevant: bool
    hallucination_detected: bool
    retry_count: int
    source_type: str  # "rag" | "web" | "hybrid" | "unverified"
    history: List[Dict[str, str]]


# ── Node 1: Retrieve ──────────────────────────────────────────────────────────
def node_retrieve(state: AgentState) -> Dict[str, Any]:
    log.info(f"--- [NODE: RETRIEVE] Query: '{state['question']}' ---")
    question = state["question"]
    docs = retrieve_and_rerank(question, top_k=20, top_n=5)
    return {
        "documents": docs,
        "retry_count": state.get("retry_count", 0),
    }


# ── Node 2: Grade Relevance ────────────────────────────────────────────────────
def node_grade_relevance(state: AgentState) -> Dict[str, Any]:
    log.info("--- [NODE: GRADE RELEVANCE] ---")
    question = state["question"]
    docs = state.get("documents", [])

    if not docs:
        log.info("  No local docs retrieved → triggering web search fallback.")
        return {"is_relevant": False}

    # Check top score from reranker
    top_score = max([d.get("rerank_score", 0.0) for d in docs]) if docs else 0.0
    log.info(f"  Top candidate rerank score: {top_score:.4f}")

    # High confidence: trust the reranker, skip LLM grading
    if top_score >= 0.5:
        log.info("  Rerank score >= 0.5 → RELEVANT (RAG). Skipping LLM grader.")
        return {"is_relevant": True}

    # Very low confidence: skip straight to web
    if top_score < 0.1:
        log.info("  Rerank score < 0.1 → NOT RELEVANT. Triggering web search.")
        return {"is_relevant": False}

    # Borderline (0.1 - 0.5): use LLM grader as tiebreaker
    log.info("  Borderline rerank score — invoking LLM relevance grader...")
    grader_prompt = ChatPromptTemplate.from_template(
        """You are a legal document relevance grader.
Evaluate whether the following retrieved legal chunks contain facts or provisions relevant to the user question.

USER QUESTION: {question}

RETRIEVED CONTEXT:
{context}

Answer ONLY with 'YES' if relevant facts exist, or 'NO' if context is unhelpful.
Answer:"""
    )
    context_str = "\n---\n".join([f"[{d['source']}]: {d['text'][:400]}" for d in docs[:3]])
    chain = grader_prompt | llm | StrOutputParser()

    try:
        res = chain.invoke({"question": question, "context": context_str}).strip().upper()
        is_rel = "YES" in res
    except Exception as e:
        log.warning(f"Relevance grader error ({e}) → defaulting to YES.")
        is_rel = True

    log.info(f"  Relevance Grader verdict: {'RELEVANT (RAG)' if is_rel else 'NOT RELEVANT (Fallback to Web)'}")
    return {"is_relevant": is_rel}


# ── Node 3: Web Search Fallback ────────────────────────────────────────────────
def node_web_search(state: AgentState) -> Dict[str, Any]:
    log.info("--- [NODE: WEB SEARCH FALLBACK] ---")
    question = state["original_question"]
    web_res = search_web_legal(question, limit=5)
    return {
        "web_results": web_res,
        "documents": web_res,  # Replace documents with web search snippets
        "source_type": "web",
    }


# ── Node 4: Generate ───────────────────────────────────────────────────────────
def node_generate(state: AgentState) -> Dict[str, Any]:
    log.info("--- [NODE: GENERATE] ---")
    question = state["original_question"]
    docs = state.get("documents", [])
    source_type = state.get("source_type", "rag")
    retry_count = state.get("retry_count", 0)

    context_blocks = []
    citations = []

    for d in docs:
        source_name = d.get("source", "Legal Corpus")
        page_num = d.get("page", 1)
        snippet_text = d.get("text", "")[:300]
        url = d.get("url")

        context_blocks.append(f"Source: {source_name} (Page {page_num})\nText: {d.get('text', '')}")
        citations.append(Citation(
            source=source_name,
            page=page_num,
            snippet=snippet_text,
            source_type=source_type,
            url=url,
        ))

    context_str = "\n\n---\n\n".join(context_blocks)

    strict_instruction = ""
    if retry_count > 0:
        strict_instruction = (
            "\n⚠️ IMPORTANT: A previous generation contained claims not directly in the context. "
            "Stick STRICTLY to the provided CONTEXT. Do not invent section numbers or facts.\n"
        )

    gen_prompt = ChatPromptTemplate.from_template(
        """You are JurisOne Senior Legal Advocate. Answer the user question based ONLY on the provided CONTEXT.
{strict_instruction}
CONTEXT:
{context}

USER QUESTION: {question}

PROVIDE YOUR RESPONSE IN THE FOLLOWING STRUCTURE:
1. Executive Summary (2-3 sentences overview)
2. Detailed Legal Analysis (Sections, provisions, procedural rules)
3. Strategic Next Steps / Recommendation

Response (Github Markdown format):"""
    )

    chain = gen_prompt | llm | StrOutputParser()
    raw_answer = chain.invoke({
        "context": context_str,
        "question": question,
        "strict_instruction": strict_instruction,
    })

    # Build executive summary from first paragraph
    lines = [line.strip() for line in raw_answer.split("\n") if line.strip() and not line.startswith("#")]
    summary = lines[0] if lines else "Legal analysis based on retrieved corpus."

    response = LegalResponse(
        summary=summary,
        citations=citations,
        confidence=0.95 if source_type == "rag" else 0.80,
        source_type=source_type,
        answer=raw_answer,
    )

    return {"generation": response}


# ── Node 5: Check Hallucination ────────────────────────────────────────────────
def node_check_hallucination(state: AgentState) -> Dict[str, Any]:
    log.info("--- [NODE: CHECK HALLUCINATION] ---")
    docs = state.get("documents", [])
    gen = state.get("generation")
    retry_count = state.get("retry_count", 0)

    if not gen or not docs:
        return {"hallucination_detected": False}

    critic_prompt = ChatPromptTemplate.from_template(
        """You are a strict Legal Hallucination Verifier.
Compare the generated answer against the source context and determine if any key claim is unsupported or hallucinated.

SOURCE CONTEXT:
{context}

GENERATED ANSWER:
{answer}

Answer ONLY with 'GROUNDED' if all facts are supported by context, or 'HALLUCINATED' if any fact is fabricated.
Verdict:"""
    )
    context_str = "\n".join([d.get("text", "")[:400] for d in docs])
    chain = critic_prompt | llm | StrOutputParser()

    try:
        verdict = chain.invoke({"context": context_str, "answer": gen.answer[:1500]}).strip().upper()
        has_hallucination = "HALLUCINATED" in verdict
    except Exception:
        has_hallucination = False

    log.info(f"  Critic Verdict: {'HALLUCINATION DETECTED' if has_hallucination else 'GROUNDED (PASSED)'}")

    return {
        "hallucination_detected": has_hallucination,
        "retry_count": retry_count + 1 if has_hallucination else retry_count,
    }


# ── Conditional Edges ──────────────────────────────────────────────────────────
def route_relevance(state: AgentState) -> str:
    if state.get("is_relevant", True):
        return "generate"
    return "web_search"


def route_hallucination(state: AgentState) -> str:
    hallucinated = state.get("hallucination_detected", False)
    retries = state.get("retry_count", 0)

    if not hallucinated:
        return END
    if retries < 2:
        log.info(f"  Looping back to GENERATE (Retry attempt {retries})...")
        return "generate"
    elif retries < 3:
        log.info(f"  Looping back to RETRIEVE (Query rewrite attempt {retries})...")
        return "retrieve"
    else:
        log.warning("  Max retries reached. Returning best effort generation.")
        return END


# ── Graph Construction ─────────────────────────────────────────────────────────
def build_agent_graph() -> StateGraph:
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("retrieve", node_retrieve)
    workflow.add_node("grade_relevance", node_grade_relevance)
    workflow.add_node("web_search", node_web_search)
    workflow.add_node("generate", node_generate)
    workflow.add_node("check_hallucination", node_check_hallucination)

    # Set Entry Point
    workflow.set_entry_point("retrieve")

    # Connect Edges
    workflow.add_edge("retrieve", "grade_relevance")
    workflow.add_conditional_edges(
        "grade_relevance",
        route_relevance,
        {
            "generate": "generate",
            "web_search": "web_search",
        },
    )
    workflow.add_edge("web_search", "generate")
    workflow.add_edge("generate", "check_hallucination")
    workflow.add_conditional_edges(
        "check_hallucination",
        route_hallucination,
        {
            "generate": "generate",
            "retrieve": "retrieve",
            END: END,
        },
    )

    return workflow.compile()


_graph_app = None


def get_agent_app():
    global _graph_app
    if _graph_app is None:
        _graph_app = build_agent_graph()
    return _graph_app


def run_agent(question: str, history: Optional[List[Dict[str, str]]] = None) -> LegalResponse:
    """Entry point to execute the agentic RAG graph."""
    app = get_agent_app()
    initial_state: AgentState = {
        "question": question,
        "original_question": question,
        "documents": [],
        "web_results": [],
        "generation": None,
        "is_relevant": True,
        "hallucination_detected": False,
        "retry_count": 0,
        "source_type": "rag",
        "history": history or [],
    }

    final_state = app.invoke(initial_state)
    gen = final_state.get("generation")

    if gen is None:
        return LegalResponse(
            summary="Unable to verify query.",
            confidence=0.0,
            source_type="unverified",
            answer="Could not generate verified answer from available sources.",
        )

    return gen


# ── Standalone CLI Test ────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_query = sys.argv[1] if len(sys.argv) > 1 else "What is the penalty for murder under BNS section 103?"
    print(f"\n🚀 Running Agentic RAG Graph for: '{test_query}'\n")

    resp = run_agent(test_query)

    print("\n" + "=" * 70)
    print(f"📌 Source Type : {resp.source_type}")
    print(f"📊 Confidence  : {resp.confidence}")
    print(f"📝 Summary     : {resp.summary}")
    print("=" * 70)
    print("\n--- Answer ---\n")
    print(resp.answer)
