"""
IT Incident Handling — LLM Prompt Templates.

Sprint 126: Story 126-2 — Prompt templates for incident analysis
and remediation recommendation via LLM.
"""

INCIDENT_ANALYSIS_PROMPT = """You are an expert IT operations engineer. Analyze the following
IT incident and provide a structured root cause analysis.

## Incident Details

- **Number**: {incident_number}
- **Severity**: {severity}
- **Category**: {category}
- **Description**: {short_description}
- **Full Description**: {description}
- **Affected Components**: {affected_components}
- **Business Service**: {business_service}
- **CMDB CI**: {cmdb_ci}

## Correlation Data

{correlation_summary}

## Root Cause Analysis (from rule-based system)

{rca_summary}

## Historical Similar Cases

{historical_cases}

---

Provide your analysis in the following JSON format:

{{
    "root_cause_summary": "One-sentence root cause description",
    "root_cause_confidence": 0.85,
    "contributing_factors": [
        "Factor 1 description",
        "Factor 2 description"
    ],
    "analysis_notes": "Additional observations or caveats",
    "suggested_category_correction": null
}}

Rules:
1. root_cause_confidence must be between 0.0 and 1.0
2. Be specific and actionable in your root cause summary
3. List all contributing factors that may have led to this incident
4. If the category seems incorrect, suggest a correction
5. Focus on IT infrastructure root causes (not business process issues)
"""

REMEDIATION_SUGGESTION_PROMPT = """You are an expert IT operations engineer. Based on the following
incident analysis, suggest remediation actions.

## Incident

- **Number**: {incident_number}
- **Severity**: {severity}
- **Category**: {category}
- **Description**: {short_description}

## Root Cause Analysis

{root_cause_summary}

## Contributing Factors

{contributing_factors}

## Available MCP Tools

The following automated tools are available for remediation:

| Tool | Description | Risk |
|------|-------------|------|
| shell:run_command | Execute shell commands on target server | Varies |
| ldap:ad_operations | Active Directory operations (unlock, reset) | Low |
| servicenow:update_incident | Update ServiceNow incident record | Low |

## Existing Rule-Based Suggestions

{existing_suggestions}

---

Suggest additional remediation actions in the following JSON format:

{{
    "suggestions": [
        {{
            "title": "Action title",
            "description": "Detailed description of what to do",
            "confidence": 0.8,
            "risk": "low|medium|high|critical",
            "mcp_tool": "shell:run_command",
            "mcp_params": {{"command": "systemctl restart nginx"}},
            "prerequisites": ["Verify service is not actively processing requests"],
            "rollback_steps": ["systemctl stop nginx", "Restore previous config"]
        }}
    ]
}}

Rules:
1. Only suggest actions that are safe and well-understood
2. confidence must be between 0.0 and 1.0
3. risk must be one of: auto, low, medium, high, critical
4. Always include rollback steps for medium+ risk actions
5. Do not duplicate existing rule-based suggestions
6. Prefer least-disruptive actions first
"""
