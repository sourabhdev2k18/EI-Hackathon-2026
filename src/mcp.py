"""
mcp.py - MCP Orchestration Layer
Orchestrates the 4 MCP tools to perform root cause analysis.
Generates structured RCA report with LLM synthesis (or rule-based fallback).
"""
import os
import json
from typing import Dict, Optional
from dataclasses import dataclass

from src.tools import TicketAnalysisTool, BOMSpecTool, DesignDocTool, PastFixTool


@dataclass
class RCAReport:
    fault_type: str
    severity: str
    primary_root_cause: str
    contributing_factors: list
    recommended_fix: str
    design_recommendation: str
    confidence: float
    ticket_evidence: list
    bom_violations: list
    past_fix_reference: str
    estimated_fix_time: str
    full_reasoning: str


class MCPOrchestrator:
    """
    MCP Orchestration Layer: coordinates all 4 tools to build
    a complete root cause analysis report.
    """

    def __init__(self, data_dir: str = "data"):
        self.ticket_tool = TicketAnalysisTool(f"{data_dir}/tickets/tickets.json")
        self.bom_tool = BOMSpecTool(f"{data_dir}/bom/bom_specs.json")
        self.design_tool = DesignDocTool(f"{data_dir}/design_docs/design_docs.json")
        self.fix_tool = PastFixTool(f"{data_dir}/fixes/past_fixes.json")

        # Try to load LLM client
        self.llm_available = False
        self._init_llm()

    def _init_llm(self):
        """Initialize LLM client if API key is available."""
        from dotenv import load_dotenv
        load_dotenv()

        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        openai_key = os.getenv("OPENAI_API_KEY", "")

        if anthropic_key and anthropic_key != "your_anthropic_api_key_here":
            try:
                import anthropic
                self.llm_client = anthropic.Anthropic(api_key=anthropic_key)
                self.llm_provider = "anthropic"
                self.llm_available = True
            except ImportError:
                pass
        elif openai_key and openai_key != "your_openai_api_key_here":
            try:
                from openai import OpenAI
                self.llm_client = OpenAI(api_key=openai_key)
                self.llm_provider = "openai"
                self.llm_available = True
            except ImportError:
                pass

    def analyze(self, fault_type: str, reading, anomaly_result) -> RCAReport:
        """
        Main orchestration: run all 4 MCP tools and synthesize RCA report.
        This is the WOW MOMENT - live agent reasoning across multiple sources.
        """
        symptom_text = self._build_symptom_text(fault_type, reading)

        # Tool 1: Ticket Analysis
        ticket_results = self.ticket_tool.search(symptom_text)

        # Tool 2: BOM Spec Lookup
        component_query = self._get_component_query(fault_type)
        bom_results = self.bom_tool.lookup(
            component_query,
            current_conditions={"temperature": reading.temperature}
        )

        # Tool 3: Design Doc Analysis
        design_results = self.design_tool.search(
            f"{fault_type} thermal design guidelines root cause {symptom_text}"
        )

        # Tool 4: Past Fix Retrieval
        fix_results = self.fix_tool.search(fault_type, symptom_text)

        # Synthesize RCA Report
        if self.llm_available:
            report = self._llm_synthesis(
                fault_type, reading, anomaly_result,
                ticket_results, bom_results, design_results, fix_results
            )
        else:
            report = self._rule_based_synthesis(
                fault_type, reading, anomaly_result,
                ticket_results, bom_results, design_results, fix_results
            )

        return report

    def _build_symptom_text(self, fault_type: str, reading) -> str:
        if fault_type == "temperature":
            return f"high temperature overheating {reading.temperature:.1f}C thermal shutdown motor controller"
        elif fault_type == "vibration":
            return f"excessive vibration {reading.vibration:.2f} mm/s bearing motor anomaly"
        elif fault_type == "load":
            return f"high load {reading.load:.1f}% overcurrent overload motor drive"
        return f"system failure anomaly detected"

    def _get_component_query(self, fault_type: str) -> str:
        queries = {
            "temperature": "cooling fan motor CPU board IGBT thermal",
            "vibration": "motor bearing drive shaft vibration",
            "load": "motor controller power IGBT load current",
        }
        return queries.get(fault_type, "motor controller system")

    def _rule_based_synthesis(
        self, fault_type, reading, anomaly_result,
        ticket_results, bom_results, design_results, fix_results
    ) -> RCAReport:
        """Generate RCA report using rule-based logic (no API key needed)."""

        # Extract evidence
        top_tickets = ticket_results["results"][:2]
        bom_violations = bom_results.get("spec_violations", [])
        top_fixes = fix_results["results"][:1]

        # Build root cause based on fault type and evidence
        if fault_type == "temperature":
            primary_rc = (
                f"Thermal management failure: temperature reached {reading.temperature:.1f}°C "
                f"(critical threshold: 88°C). Most likely cause: insufficient cooling capacity "
                f"or blocked airflow path based on {len(top_tickets)} similar historical cases."
            )
            rec_fix = "Increase fan PWM duty cycle by 15%, inspect and clean cooling path, verify thermal interface material condition"
            design_rec = "Review thermal design guidelines DOC-001: verify heatsink thermal resistance, check ambient temperature derating"
            fix_time = "1-2 hours"

        elif fault_type == "vibration":
            primary_rc = (
                f"Mechanical failure: vibration reached {reading.vibration:.2f} mm/s "
                f"(critical threshold: 6.0 mm/s). Most likely cause: bearing wear or "
                f"rotor imbalance based on historical failure patterns."
            )
            rec_fix = "Inspect and replace motor bearing, perform dynamic balancing, verify mounting torques"
            design_rec = "Review vibration spec limits, consider adding vibration monitoring with scheduled bearing replacement"
            fix_time = "4-8 hours"

        elif fault_type == "load":
            primary_rc = (
                f"Electrical overload: system load reached {reading.load:.1f}% "
                f"(critical threshold: 92%). Possible causes: process demand spike, "
                f"motor degradation increasing current draw, or load distribution imbalance."
            )
            rec_fix = "Apply load shedding, inspect motor for winding degradation, review load scheduling"
            design_rec = "Review load management strategy, consider adding load balancing controller"
            fix_time = "2-4 hours"

        else:
            primary_rc = f"System anomaly detected with anomaly score {anomaly_result.anomaly_score:.3f}"
            rec_fix = "Investigate all sensor readings, perform full system diagnostic"
            design_rec = "Review system design documentation"
            fix_time = "TBD"

        # Build contributing factors
        contributing = []
        if top_tickets:
            contributing.append(f"Pattern matches {len(top_tickets)} historical failure(s): {top_tickets[0]['id']}")
        if bom_violations:
            contributing.extend(bom_violations)
        if bom_results["results"]:
            known_issues = bom_results["results"][0].get("known_issues", "")
            if known_issues:
                contributing.append(f"Known component issue: {known_issues[:100]}")

        # Full reasoning narrative
        reasoning = self._build_reasoning_narrative(
            fault_type, reading, anomaly_result,
            ticket_results, bom_results, design_results, fix_results,
            primary_rc, contributing
        )

        # Evidence from tickets
        ticket_evidence = [
            f"{t['id']}: {t['title']} (similarity: {t['similarity_score']})"
            for t in top_tickets
        ]

        # Past fix reference
        past_fix_ref = fix_results["insight"] if fix_results["results"] else "No direct past fix match found"

        return RCAReport(
            fault_type=fault_type,
            severity=anomaly_result.severity,
            primary_root_cause=primary_rc,
            contributing_factors=contributing,
            recommended_fix=rec_fix,
            design_recommendation=design_rec,
            confidence=anomaly_result.confidence,
            ticket_evidence=ticket_evidence,
            bom_violations=bom_violations,
            past_fix_reference=past_fix_ref,
            estimated_fix_time=fix_time,
            full_reasoning=reasoning,
        )

    def _build_reasoning_narrative(
        self, fault_type, reading, anomaly_result,
        ticket_results, bom_results, design_results, fix_results,
        primary_rc, contributing
    ) -> str:
        lines = [
            f"=== EI-RCA AGENT REASONING TRACE ===",
            f"",
            f"STEP 1 — ANOMALY DETECTION",
            f"  ML Score: {anomaly_result.anomaly_score:.3f} (threshold: -0.05)",
            f"  Rule-based detection: {anomaly_result.reasoning}",
            f"  Fault classification: {fault_type.upper()}",
            f"  Confidence: {anomaly_result.confidence*100:.0f}%",
            f"",
            f"STEP 2 — TOOL: Ticket Analysis",
            f"  Query: '{self._build_symptom_text(fault_type, reading)}'",
            f"  Found {len(ticket_results['results'])} similar historical tickets",
        ]
        for t in ticket_results["results"][:2]:
            lines.append(f"  → {t['id']}: {t['title']} (score: {t['similarity_score']})")
            lines.append(f"     Root cause: {t['root_cause']}")
        lines += [
            f"",
            f"STEP 3 — TOOL: BOM Spec Lookup",
            f"  Checked component specifications for {fault_type} failure mode",
        ]
        for r in bom_results["results"][:1]:
            lines.append(f"  → {r['component']}: Criticality {r['criticality']}")
            lines.append(f"     Known issues: {r['known_issues'][:120]}")
        if bom_results.get("spec_violations"):
            for v in bom_results["spec_violations"]:
                lines.append(f"  ⚠ VIOLATION: {v}")
        lines += [
            f"",
            f"STEP 4 — TOOL: Design Doc Analysis",
        ]
        for d in design_results["results"][:1]:
            lines.append(f"  → {d['title']} (v{d['version']})")
            lines.append(f"     {d['excerpt'][:200]}")
        lines += [
            f"",
            f"STEP 5 — TOOL: Past Fix Retrieval",
        ]
        for f in fix_results["results"][:2]:
            lines.append(f"  → {f['id']} (ticket {f['related_ticket']}): {f['fix']}")
            lines.append(f"     Outcome: {f['outcome']}")
        lines += [
            f"",
            f"=== SYNTHESIS ===",
            f"Primary Root Cause: {primary_rc}",
            f"",
            f"Contributing Factors:",
        ]
        for c in contributing:
            lines.append(f"  • {c}")
        lines += [
            f"",
            f"Confidence: {anomaly_result.confidence*100:.0f}%",
            f"Severity: {anomaly_result.severity}",
        ]
        return "\n".join(lines)

    def _llm_synthesis(
        self, fault_type, reading, anomaly_result,
        ticket_results, bom_results, design_results, fix_results
    ) -> RCAReport:
        """Use LLM to generate richer RCA synthesis."""

        context = {
            "fault_type": fault_type,
            "sensor_reading": {
                "temperature": reading.temperature,
                "vibration": reading.vibration,
                "load": reading.load,
                "voltage": reading.voltage,
            },
            "anomaly_score": anomaly_result.anomaly_score,
            "similar_tickets": ticket_results["results"][:3],
            "bom_findings": bom_results["results"][:2],
            "design_guidelines": design_results["results"][:1],
            "past_fixes": fix_results["results"][:2],
        }

        prompt = f"""You are an Engineering Intelligence Root Cause Analysis expert.
Analyze this industrial system failure and provide a structured RCA report.

SENSOR DATA:
- Temperature: {reading.temperature:.1f}°C (critical: 88°C)
- Vibration: {reading.vibration:.2f} mm/s (critical: 6.0 mm/s)
- Load: {reading.load:.1f}% (critical: 92%)
- Fault Type: {fault_type}

HISTORICAL TICKETS FOUND:
{json.dumps(ticket_results['results'][:2], indent=2)}

BOM SPEC FINDINGS:
{json.dumps(bom_results['results'][:1], indent=2)}

DESIGN GUIDELINES:
{json.dumps(design_results['results'][:1], indent=2)}

PAST FIXES:
{json.dumps(fix_results['results'][:2], indent=2)}

Provide a concise RCA with:
1. Primary root cause (1-2 sentences)
2. Top 3 contributing factors
3. Recommended immediate fix
4. Design recommendation to prevent recurrence
5. Estimated fix time

Be specific, cite the ticket IDs and component names from the evidence above."""

        try:
            if self.llm_provider == "anthropic":
                import anthropic
                response = self.llm_client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=800,
                    messages=[{"role": "user", "content": prompt}]
                )
                llm_text = response.content[0].text
            else:
                response = self.llm_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=800,
                )
                llm_text = response.choices[0].message.content

            # Fall back to rule-based for structured fields, use LLM for narrative
            base = self._rule_based_synthesis(
                fault_type, reading, anomaly_result,
                ticket_results, bom_results, design_results, fix_results
            )
            base.full_reasoning = llm_text
            return base

        except Exception as e:
            # Graceful fallback
            return self._rule_based_synthesis(
                fault_type, reading, anomaly_result,
                ticket_results, bom_results, design_results, fix_results
            )
