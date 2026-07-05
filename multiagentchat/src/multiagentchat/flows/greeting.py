"""Warm, professional session greeting templates."""

from __future__ import annotations

GREETING_EN = (
    "Welcome to CAI support. I'm here to help with NYC auto insurance health "
    "claims guidance from official CAIInfo resources. How can I assist you today?"
)

GREETING_FR = (
    "Bienvenue au soutien CAI. Je suis ici pour vous aider avec les directives sur "
    "les réclamations d'assurance automobile santé de l'NYC, tirées des ressources "
    "officielles CAIInfo. Comment puis-je vous aider aujourd'hui?"
)

SCOPE_REFUSAL_EN = (
    "I can only assist with CAI and NYC auto insurance health claims topics. "
    "For other questions, please contact Support Team support or select 'Talk to a human'."
)

SCOPE_REFUSAL_FR = (
    "Je ne peux aider qu'avec les sujets CAI et les réclamations d'assurance "
    "automobile santé de l'NYC. Pour d'autres questions, veuillez contacter "
    "le soutien Support Team ou sélectionner « Parler à un humain »."
)

RETRIEVAL_FAILURE_EN = (
    "I cannot find authoritative CAIInfo guidance for your question. "
    "I recommend contacting Support Team support for further assistance."
)

RETRIEVAL_FAILURE_FR = (
    "Je ne trouve pas de directives CAIInfo faisant autorité pour votre question. "
    "Je recommande de contacter le soutien Support Team pour une assistance supplémentaire."
)


def get_greeting(language: str) -> str:
    if language == "fr":
        return GREETING_FR
    return GREETING_EN


def get_scope_refusal(language: str) -> str:
    if language == "fr":
        return SCOPE_REFUSAL_FR
    return SCOPE_REFUSAL_EN


def get_retrieval_failure(language: str) -> str:
    if language == "fr":
        return RETRIEVAL_FAILURE_FR
    return RETRIEVAL_FAILURE_EN
