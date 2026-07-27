"""LLM-powered intent detection provider for the Orchestrator subsystem."""

import json
import logging
from typing import Any
from uuid import uuid4

from app.core.exceptions import InternalServerError, ValidationError
from app.llm.models import LLMRequest
from app.orchestrator.base import (
    BaseIntentDetector,
    IntentDetectionError,
    OrchestratorInitializationError,
)
from app.orchestrator.models import DetectedIntent, IntentType, UserRequest
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)

INTENT_CLASSIFICATION_PROMPT = """You are a highly accurate intent classification engine.
Analyze the user's input and classify it into exactly one of the following intent types:
- CHAT (casual conversation, greetings, small talk)
- INFORMATION_QUERY (asking for facts, definitions, or general knowledge)
- NAVIGATION_TASK (requests to navigate, go to, or open a specific page/screen)
- BOOKING_TASK (requests to book, reserve, or schedule a service or appointment)
- SPIRITUAL_SERVICE (requests related to religious, spiritual, or astrological services, e.g. booking a pandit, horoscope reading)
- UNKNOWN (if the intent is unclear, ambiguous, or doesn't match any above)

Return a strictly valid JSON object with the following schema:
{
  "intent_type": "one of the intent types exactly as written above",
  "confidence": <float between 0.0 and 1.0 representing your confidence>,
  "entities": {
    <extract any relevant named entities, parameters, or target screens as key-value string pairs>
  }
}
Output ONLY the JSON object. Do not wrap in markdown tags like ```json. Do not include any explanations.
"""


class LLMIntentDetector(BaseIntentDetector):
    """LLM-powered implementation of BaseIntentDetector.

    Uses AIService to invoke an LLM for structured JSON intent classification.
    """

    def __init__(self, ai_service: AIService) -> None:
        """Initialize the LLM intent detector.

        Args:
            ai_service: Initialized AIService instance to communicate with LLM providers.

        Raises:
            OrchestratorInitializationError: If ai_service is None.
        """
        if ai_service is None:
            raise OrchestratorInitializationError("AIService dependency cannot be None.")
        self._ai = ai_service
        logger.info("LLMIntentDetector initialized")

    async def detect(self, request: UserRequest) -> DetectedIntent:
        """Analyze a UserRequest and classify the detected user intent using an LLM.

        Args:
            request: Incoming UserRequest model to classify.

        Returns:
            DetectedIntent: Classified intent model.

        Raises:
            IntentDetectionError: If intent classification fails or LLM output is malformed.
        """
        if not request.user_input.strip():
            logger.warning("Empty user input provided for intent detection.")
            return DetectedIntent(
                intent_id=uuid4(),
                intent_type=IntentType.UNKNOWN,
                confidence=1.0,
                entities={},
            )

        llm_req = LLMRequest(
            system_prompt=INTENT_CLASSIFICATION_PROMPT,
            prompt=f"User Input: {request.user_input}",
            temperature=0.1,  # Low temperature for deterministic classification
        )

        try:
            logger.debug("Calling AIService for intent detection [request_id=%s]", request.request_id)
            response = await self._ai.generate(request=llm_req)
        except (InternalServerError, ValidationError) as exc:
            logger.error("LLM provider error during intent detection: %s", exc)
            raise IntentDetectionError("Failed to communicate with LLM provider.") from exc
        except Exception as exc:
            logger.exception("Unexpected error during LLM generation.")
            raise IntentDetectionError("Unexpected error occurred during intent detection.") from exc

        raw_content = response.content.strip()
        
        # Clean up markdown tags if the model ignores the prompt instruction
        if raw_content.startswith("```json"):
            raw_content = raw_content[7:]
        elif raw_content.startswith("```"):
            raw_content = raw_content[3:]
        
        if raw_content.endswith("```"):
            raw_content = raw_content[:-3]
            
        raw_content = raw_content.strip()

        try:
            parsed_data: dict[str, Any] = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse LLM response as JSON. Content: %s", raw_content)
            raise IntentDetectionError("LLM returned malformed JSON output.") from exc

        intent_type_str = parsed_data.get("intent_type", "").strip().upper()
        
        try:
            confidence = float(parsed_data.get("confidence", 0.0))
        except (ValueError, TypeError):
            confidence = 0.0
            
        entities = parsed_data.get("entities", {})

        if not isinstance(entities, dict):
            entities = {}

        try:
            intent_type = IntentType(intent_type_str.lower())
        except ValueError:
            logger.warning("LLM returned invalid intent type: %s. Defaulting to UNKNOWN.", intent_type_str)
            intent_type = IntentType.UNKNOWN

        logger.info(
            "Intent detected [type=%s, confidence=%.2f, request_id=%s]",
            intent_type.value,
            confidence,
            request.request_id,
        )

        return DetectedIntent(
            intent_id=uuid4(),
            intent_type=intent_type,
            confidence=confidence,
            entities=entities,
        )
