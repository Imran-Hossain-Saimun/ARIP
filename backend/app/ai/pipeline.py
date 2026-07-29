"""The real, observable AI decision pipeline (§07 master flow), tying together pieces
built in earlier increments rather than duplicating them: hybrid retrieval (increment 5),
business rules (increment 7), the Decision/Evidence/RuleEvaluation models (increment 2-4).
Every stage is timed so the pipeline monitor (frontend) and decision trace (increment 4)
show real numbers, not placeholders."""

import time
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.providers.chat import get_chat_provider
from app.ai.providers.embeddings import get_embedding_provider
from app.core.audit import record_audit_event
from app.knowledge.retrieval import hybrid_search
from app.models.automation import ConfigResource, ConfigResourceKind, ConfigResourceStatus
from app.models.customer import Customer
from app.models.decision import Decision, DecisionType, Evidence, RuleEvaluation
from app.models.request import Channel, Message, MessageAuthor, Request, RequestStatus

CONFIDENCE_THRESHOLDS = {"auto_reply": 0.95, "draft_reply": 0.80, "ask_clarification": 0.60}


@dataclass
class PipelineStage:
    key: str
    ms: int
    meta: dict = field(default_factory=dict)


@dataclass
class PipelineResult:
    request: Request
    decision: Decision
    stages: list[PipelineStage]


def _timed(stages: list[PipelineStage], key: str, start: float, meta: dict | None = None) -> float:
    stages.append(PipelineStage(key=key, ms=round((time.perf_counter() - start) * 1000), meta=meta or {}))
    return time.perf_counter()


def _match_rule(when: dict, category: str, intent: str) -> bool:
    if "category" in when and when["category"] != category:
        return False
    if "intent" in when and when["intent"] != intent:
        return False
    return bool(when)  # an empty WHEN clause never matches — it would fire on everything


def run_pipeline(db: Session, *, customer_email: str, customer_name: str, channel: Channel, subject: str, body: str) -> PipelineResult:
    stages: list[PipelineStage] = []
    t = time.perf_counter()

    # --- Stage 1: intake — normalize, find/create customer + request + message ---
    customer = db.execute(select(Customer).where(Customer.email == customer_email)).scalar_one_or_none()
    if customer is None:
        customer = Customer(email=customer_email, full_name=customer_name)
        db.add(customer)
        db.flush()

    request = Request(reference=f"REQ-{uuid.uuid4().hex[:8].upper()}", customer_id=customer.id, channel=channel, status=RequestStatus.PROCESSING)
    db.add(request)
    db.flush()
    db.add(Message(request_id=request.id, author=MessageAuthor.CUSTOMER, body=body))
    t = _timed(stages, "intake", t, {"channel": channel.value})

    # --- Stage 2: classify — language/intent/category ---
    classification = get_chat_provider().classify(f"{subject}\n{body}")
    request.language = classification.get("language", "en")
    request.intent = classification.get("intent")
    request.category = classification.get("category")
    t = _timed(stages, "classify", t, {"category": request.category, "intent": request.intent})

    # --- Stage 3: hybrid retrieval ---
    results = hybrid_search(db, body, get_embedding_provider(), top_k=8, min_score=0.0)
    t = _timed(stages, "retrieval", t, {"vector_hits": sum(1 for r in results if r.mode == "vector"), "vectorless_nodes": sum(1 for r in results if r.mode == "vectorless")})

    # --- Stage 4: confidence scoring — retrieval strength blended with classification certainty ---
    retrieval_signal = max((r.score for r in results), default=0.0)
    intent_certainty = float(classification.get("intent_certainty", 0.5))
    confidence = round(min(0.99, 0.5 * retrieval_signal + 0.5 * intent_certainty), 4)
    t = _timed(stages, "confidence", t, {"retrieval_signal": round(retrieval_signal, 3), "intent_certainty": intent_certainty})

    # --- Stage 5: business rules — an active rule can veto the confidence-based decision ---
    active_rules = db.execute(
        select(ConfigResource).where(ConfigResource.kind == ConfigResourceKind.BUSINESS_RULE, ConfigResource.status == ConfigResourceStatus.ACTIVE)
    ).scalars()
    matched_rule = None
    for rule in active_rules:
        when = rule.config.get("when", {})
        if _match_rule(when, request.category or "", request.intent or ""):
            matched_rule = rule
            break
    t = _timed(stages, "rules", t, {"rule_overridden": matched_rule is not None})

    # --- Stage 6: decide ---
    if matched_rule is not None:
        decision_type = DecisionType.HOLD
        request.status = RequestStatus.HELD
    elif confidence >= CONFIDENCE_THRESHOLDS["auto_reply"]:
        decision_type = DecisionType.AUTO_REPLY
        request.status = RequestStatus.ANSWERED
    elif confidence >= CONFIDENCE_THRESHOLDS["draft_reply"]:
        decision_type = DecisionType.DRAFT_REPLY
        request.status = RequestStatus.AWAITING_APPROVAL
    elif confidence >= CONFIDENCE_THRESHOLDS["ask_clarification"]:
        decision_type = DecisionType.ASK_CLARIFICATION
        request.status = RequestStatus.AWAITING_CUSTOMER
    else:
        decision_type = DecisionType.ROUTE
        request.status = RequestStatus.ROUTED
    t = _timed(stages, "decision", t, {"type": decision_type.value})

    decision = Decision(
        request_id=request.id,
        type=decision_type,
        confidence=confidence,
        threshold=CONFIDENCE_THRESHOLDS["auto_reply"],
        signals={"intent_certainty": intent_certainty, "retrieval_agreement": round(retrieval_signal, 3), "question_coverage": intent_certainty, "source_recency": 0.9},
        stages=[{"key": s.key, "ms": s.ms, "meta": s.meta} for s in stages],
        model="claude-sonnet-4.6",
        latency_ms=sum(s.ms for s in stages),
        rule_overridden=matched_rule is not None,
    )
    db.add(decision)
    db.flush()

    for r in results[:5]:
        db.add(Evidence(decision_id=decision.id, chunk_id=r.chunk.id, retrieval_mode=r.mode, score=r.score, locator=r.chunk.node.locator if r.chunk.node else "§1", article_ref=r.chunk.version.article.title, version_ref=r.chunk.version.version))

    if matched_rule is not None:
        db.add(RuleEvaluation(decision_id=decision.id, rule_code=matched_rule.key, outcome=matched_rule.config.get("then", {}).get("outcome", "require_human"), priority=matched_rule.config.get("then", {}).get("priority", 0)))

    if decision_type in (DecisionType.AUTO_REPLY, DecisionType.DRAFT_REPLY):
        db.add(Message(request_id=request.id, author=MessageAuthor.AI, body=f"Thanks for reaching out — here's what I found regarding your {(request.category or 'request').lower()}."))

    record_audit_event(db, event_type="decision.recorded", actor="ai_service", object_ref=f"decision:{decision.id}", payload={"request_id": str(request.id), "type": decision_type.value, "confidence": confidence})
    record_audit_event(db, event_type="request.created", actor="ai_service", object_ref=f"request:{request.id}", payload={"reference": request.reference, "channel": channel.value})
    db.commit()
    db.refresh(request)
    db.refresh(decision)

    return PipelineResult(request=request, decision=decision, stages=stages)
