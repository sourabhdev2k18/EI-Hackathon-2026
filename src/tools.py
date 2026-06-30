"""
tools.py - MCP Tools with RAG-based knowledge retrieval
Three tools: Ticket Analysis, BOM Spec Lookup, Design Doc Analysis, Past Fix Retrieval
Uses TF-IDF similarity (fallback when no API key) or sentence-transformers
"""
import json
import os
import numpy as np
from typing import List, Dict, Optional
from pathlib import Path


def _load_json(path: str) -> list:
    with open(path, "r") as f:
        return json.load(f)


def _tfidf_similarity(query: str, documents: List[str]) -> List[float]:
    """Simple TF-IDF based similarity - works without any API key."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    corpus = [query] + documents
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    try:
        tfidf_matrix = vectorizer.fit_transform(corpus)
        scores = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
        return scores.tolist()
    except Exception:
        return [0.0] * len(documents)


class TicketAnalysisTool:
    """
    MCP Tool 1: Search historical failure tickets using semantic similarity.
    Finds past tickets matching current failure symptom.
    """

    def __init__(self, data_path: str):
        self.tickets = _load_json(data_path)

    def search(self, query: str, top_k: int = 3) -> Dict:
        """Find most relevant historical tickets for a given symptom."""
        documents = [
            f"{t['title']} {t['symptom']} {t['component']} {t.get('root_cause', '')}"
            for t in self.tickets
        ]
        scores = _tfidf_similarity(query, documents)
        ranked = sorted(zip(self.tickets, scores), key=lambda x: x[1], reverse=True)
        top = ranked[:top_k]

        results = []
        for ticket, score in top:
            if score > 0.05:
                results.append({
                    "id": ticket["id"],
                    "title": ticket["title"],
                    "symptom": ticket["symptom"],
                    "component": ticket["component"],
                    "severity": ticket["severity"],
                    "root_cause": ticket.get("root_cause", "Not documented"),
                    "fix_applied": ticket.get("fix_applied", "Not documented"),
                    "similarity_score": round(score, 3),
                })

        return {
            "tool": "ticket_analysis",
            "query": query,
            "results": results,
            "insight": self._generate_insight(results),
        }

    def _generate_insight(self, results: List[Dict]) -> str:
        if not results:
            return "No similar historical tickets found."
        top = results[0]
        insight = (
            f"Most similar case: {top['id']} - '{top['title']}'. "
            f"Historical root cause: {top['root_cause']}. "
            f"Fix that worked: {top['fix_applied']}."
        )
        if len(results) > 1:
            insight += f" {len(results)-1} additional similar cases found."
        return insight


class BOMSpecTool:
    """
    MCP Tool 2: Look up component specifications from Bill of Materials.
    Validates if current operating conditions exceed component ratings.
    """

    def __init__(self, data_path: str):
        self.bom = _load_json(data_path)

    def lookup(self, component_query: str, current_conditions: Dict = None) -> Dict:
        """Find BOM spec for a component and validate against current conditions."""
        documents = [
            f"{b['component']} {b['part_number']} {b.get('known_issues', '')}"
            for b in self.bom
        ]
        scores = _tfidf_similarity(component_query, documents)
        ranked = sorted(zip(self.bom, scores), key=lambda x: x[1], reverse=True)

        results = []
        violations = []

        for bom_item, score in ranked[:2]:
            if score > 0.05:
                result = {
                    "id": bom_item["id"],
                    "component": bom_item["component"],
                    "part_number": bom_item["part_number"],
                    "criticality": bom_item["criticality"],
                    "known_issues": bom_item.get("known_issues", ""),
                    "maintenance": bom_item.get("maintenance", ""),
                    "similarity_score": round(score, 3),
                }

                # Check if current conditions violate spec
                if current_conditions:
                    spec = bom_item.get("spec", {})
                    temp = current_conditions.get("temperature", 0)

                    if "max_junction_temp" in spec:
                        max_t = float(spec["max_junction_temp"].replace("C", ""))
                        if temp > max_t * 0.85:
                            violations.append(
                                f"{bom_item['component']}: Temperature {temp:.1f}°C approaching max junction {max_t}°C"
                            )

                results.append(result)

        return {
            "tool": "bom_spec_lookup",
            "query": component_query,
            "results": results,
            "spec_violations": violations,
            "insight": self._generate_insight(results, violations),
        }

    def _generate_insight(self, results: List[Dict], violations: List[str]) -> str:
        if not results:
            return "No matching BOM specifications found."
        top = results[0]
        insight = (
            f"Component: {top['component']} (Criticality: {top['criticality']}). "
            f"Known issues: {top['known_issues'][:150]}..."
        )
        if violations:
            insight += f" WARNING: Spec violations detected: {'; '.join(violations)}"
        return insight


class DesignDocTool:
    """
    MCP Tool 3: Retrieve relevant design guidelines and documentation.
    Uses RAG to find design principles relevant to the failure.
    """

    def __init__(self, data_path: str):
        self.docs = _load_json(data_path)

    def search(self, query: str, top_k: int = 2) -> Dict:
        """Search design documentation for relevant guidelines."""
        documents = [
            f"{d['title']} {d['content'][:500]}"
            for d in self.docs
        ]
        scores = _tfidf_similarity(query, documents)
        ranked = sorted(zip(self.docs, scores), key=lambda x: x[1], reverse=True)

        results = []
        for doc, score in ranked[:top_k]:
            if score > 0.02:
                # Extract most relevant sentences
                content = doc["content"]
                results.append({
                    "id": doc["id"],
                    "title": doc["title"],
                    "version": doc["version"],
                    "excerpt": content[:400] + "...",
                    "tags": doc.get("tags", []),
                    "similarity_score": round(score, 3),
                })

        return {
            "tool": "design_doc_analysis",
            "query": query,
            "results": results,
            "insight": self._generate_insight(results),
        }

    def _generate_insight(self, results: List[Dict]) -> str:
        if not results:
            return "No relevant design documentation found."
        top = results[0]
        return (
            f"Relevant guideline: '{top['title']}' (v{top['version']}). "
            f"Key content: {top['excerpt'][:200]}..."
        )


class PastFixTool:
    """
    MCP Tool 4: Retrieve validated past fixes for similar failures.
    """

    def __init__(self, data_path: str):
        self.fixes = _load_json(data_path)

    def search(self, fault_type: str, symptom: str) -> Dict:
        """Find validated past fixes for a given fault type and symptom."""
        query = f"{fault_type} {symptom}"
        documents = [
            f"{f['symptom']} {f['root_cause']} {f['fix']}"
            for f in self.fixes
        ]
        scores = _tfidf_similarity(query, documents)
        ranked = sorted(zip(self.fixes, scores), key=lambda x: x[1], reverse=True)

        results = []
        for fix, score in ranked[:3]:
            if score > 0.05:
                results.append({
                    "id": fix["id"],
                    "related_ticket": fix["related_ticket"],
                    "symptom": fix["symptom"],
                    "root_cause": fix["root_cause"],
                    "fix": fix["fix"],
                    "outcome": fix["outcome"],
                    "time_to_fix_hours": fix["time_to_fix_hours"],
                    "validated": fix["validated"],
                    "similarity_score": round(score, 3),
                })

        return {
            "tool": "past_fix_retrieval",
            "query": query,
            "results": results,
            "insight": self._generate_insight(results),
        }

    def _generate_insight(self, results: List[Dict]) -> str:
        if not results:
            return "No validated past fixes found for this failure pattern."
        top = results[0]
        return (
            f"Best matching fix (ticket {top['related_ticket']}): {top['fix']}. "
            f"Outcome: {top['outcome']}. "
            f"Time to fix: {top['time_to_fix_hours']} hours."
        )
