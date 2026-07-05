# MultiAgentChat Agents

CrewAI Flow + nine-agent sequential crew for CAIInfo user queries.

| Agent ID | Role |
|----------|------|
| `triage_agent` | Intake & portal classifier |
| `facility_CAI_knowledge_agent` | Facilities portal RAG |
| `insurer_CAI_knowledge_agent` | Insurers portal RAG validation |
| `training_guide_agent` | Step extractor |
| `response_agent` | Answer composer + guardrails |
| `sentiment_escalation_agent` | Quality gate |
| `ticket_agent` | ServiceNow Case (stub) |
| `handoff_agent` | Context packager |
| `copilot_agent` | Internal copilot (stub) |

See `project-context/2.build/backend-funcional-spec.md`.
