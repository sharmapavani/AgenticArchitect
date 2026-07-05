"""CAISupportCrew — full SAD nine-agent sequential pipeline."""

from __future__ import annotations

import os

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from multiagentchat.guardrails.triage_guardrails import respond_guardrail, triage_guardrail
from multiagentchat.tools.citation_formatter import format_citations
from multiagentchat.tools.pii_scrubber import scrub_pii
from multiagentchat.tools.servicenow_stub import create_case_stub
from multiagentchat.tools.tone_validator import validate_tone
from multiagentchat.tools.vector_search import search_knowledge_base
from multiagentchat.utils.llmUtils import get_llm

KNOWLEDGE_TOOLS = [search_knowledge_base, format_citations]
RESPONSE_TOOLS = [scrub_pii, validate_tone]
TICKET_TOOLS = [create_case_stub]
COPILOT_TOOLS = [search_knowledge_base, create_case_stub]

# DEV: skip ticket/handoff/copilot LLM tasks to measure latency delta (default: on).
# Set CREW_SKIP_SUPPORT_TASKS=0 to restore the full nine-task pipeline.
def _skip_support_tasks() -> bool:
    return os.getenv("CREW_SKIP_SUPPORT_TASKS", "1").lower() in ("1", "true", "yes")


TASK_MANIFEST_CORE: list[dict[str, str]] = [
    {
        "task_id": "triage_task",
        "agent_id": "triage_agent",
        "label": "CAI Intake Enrichment Agent",
    },
    {
        "task_id": "retrieve_task",
        "agent_id": "facility_CAI_knowledge_agent",
        "label": "Facilities Portal RAG Specialist",
    },
    {
        "task_id": "insurer_validate_task",
        "agent_id": "insurer_CAI_knowledge_agent",
        "label": "Insurers Portal RAG Specialist",
    },
    {
        "task_id": "training_task",
        "agent_id": "training_guide_agent",
        "label": "Procedural Step Extractor",
    },
    {
        "task_id": "respond_task",
        "agent_id": "response_agent",
        "label": "User-Facing Answer Composer",
    },
    {
        "task_id": "sentiment_task",
        "agent_id": "sentiment_escalation_agent",
        "label": "Quality and Escalation Gate",
    },
]

TASK_MANIFEST_SUPPORT: list[dict[str, str]] = [
    {
        "task_id": "ticket_task",
        "agent_id": "ticket_agent",
        "label": "ServiceNow Case Creator",
    },
    {
        "task_id": "handoff_task",
        "agent_id": "handoff_agent",
        "label": "Human Context Packager",
    },
    {
        "task_id": "copilot_task",
        "agent_id": "copilot_agent",
        "label": "Internal Support Copilot",
    },
]


def active_task_manifest() -> list[dict[str, str]]:
    """Return active crew tasks with display metadata for progress UI."""
    if _skip_support_tasks():
        return list(TASK_MANIFEST_CORE)
    return list(TASK_MANIFEST_CORE) + list(TASK_MANIFEST_SUPPORT)


@CrewBase
class CAISupportCrew:
    """Sequential crew implementing SAD §2.1 nine-agent pipeline."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def triage_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["triage_agent"],
            llm=get_llm(),
            tools=[],
            allow_delegation=False,
            verbose=True,
        )

    @agent
    def facility_CAI_knowledge_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["facility_CAI_knowledge_agent"],
            llm=get_llm(),
            tools=KNOWLEDGE_TOOLS,
            allow_delegation=False,
            verbose=True,
        )

    @agent
    def insurer_CAI_knowledge_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["insurer_CAI_knowledge_agent"],
            llm=get_llm(),
            tools=KNOWLEDGE_TOOLS,
            allow_delegation=False,
            verbose=True,
        )

    @agent
    def training_guide_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["training_guide_agent"],
            llm=get_llm(),
            allow_delegation=False,
            verbose=True,
        )

    @agent
    def response_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["response_agent"],
            llm=get_llm(),
            tools=RESPONSE_TOOLS,
            allow_delegation=False,
            verbose=True,
        )

    @agent
    def sentiment_escalation_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["sentiment_escalation_agent"],
            llm=get_llm(),
            allow_delegation=False,
            verbose=True,
        )

    @agent
    def ticket_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["ticket_agent"],
            llm=get_llm(),
            tools=TICKET_TOOLS,
            allow_delegation=False,
            verbose=True,
        )

    @agent
    def handoff_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["handoff_agent"],
            llm=get_llm(),
            allow_delegation=False,
            verbose=True,
        )

    @agent
    def copilot_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["copilot_agent"],
            llm=get_llm(),
            tools=COPILOT_TOOLS,
            allow_delegation=False,
            verbose=True,
        )

    @task
    def triage_task(self) -> Task:
        return Task(
            config=self.tasks_config["triage_task"],
            guardrail=triage_guardrail,
            guardrail_max_retries=2,
        )

    @task
    def retrieve_task(self) -> Task:
        return Task(config=self.tasks_config["retrieve_task"])

    @task
    def insurer_validate_task(self) -> Task:
        return Task(
            description=(
                'If triage portal is "insurers", re-run vector_search with portal=insurers '
                'and merge any additional relevant chunks for query: "{message}". '
                "If portal is not insurers, output {\"validated\": true, \"skipped\": true}. "
                "Output ONLY valid JSON with validated, skipped, supplemental_chunks."
            ),
            expected_output='JSON: {"validated":true,"skipped":true|false,"supplemental_chunks":[]}',
            agent=self.insurer_CAI_knowledge_agent(),
            context=[self.triage_task(), self.retrieve_task()],
        )

    @task
    def training_task(self) -> Task:
        return Task(
            config=self.tasks_config["training_task"],
            context=[self.retrieve_task(), self.insurer_validate_task()],
        )

    @task
    def respond_task(self) -> Task:
        return Task(
            config=self.tasks_config["respond_task"],
            guardrail=respond_guardrail,
            guardrail_max_retries=2,
            context=[self.triage_task(), self.retrieve_task(), self.training_task()],
        )

    @task
    def sentiment_task(self) -> Task:
        return Task(
            config=self.tasks_config["sentiment_task"],
            context=[self.respond_task(), self.retrieve_task()],
        )

    # --- DEV TEMP: omitted from crew() when CREW_SKIP_SUPPORT_TASKS=1 (default) ---
    @task
    def ticket_task(self) -> Task:
        return Task(
            config=self.tasks_config["ticket_task"],
            context=[self.sentiment_task(), self.respond_task(), self.triage_task()],
        )

    @task
    def handoff_task(self) -> Task:
        return Task(
            config=self.tasks_config["handoff_task"],
            context=[
                self.sentiment_task(),
                self.respond_task(),
                self.ticket_task(),
                self.triage_task(),
            ],
        )

    @task
    def copilot_task(self) -> Task:
        return Task(
            config=self.tasks_config["copilot_task"],
            context=[self.handoff_task(), self.retrieve_task(), self.respond_task()],
        )

    def _active_tasks(self) -> list[Task]:
        core: list[Task] = [
            self.triage_task(),
            self.retrieve_task(),
            self.insurer_validate_task(),
            self.training_task(),
            self.respond_task(),
            self.sentiment_task(),
        ]
        if _skip_support_tasks():
            return core
        return core + [self.ticket_task(), self.handoff_task(), self.copilot_task()]

    @crew
    def crew(self) -> Crew:
        skip = _skip_support_tasks()
        if skip:
            print("[DEV] CREW_SKIP_SUPPORT_TASKS=1 — ticket/handoff/copilot tasks omitted")
        return Crew(
            agents=self.agents,
            tasks=self._active_tasks(),
            process=Process.sequential,
            memory=False,
            verbose=True,
            max_rpm=int(os.getenv("CREW_MAX_RPM", "10")),
        )
