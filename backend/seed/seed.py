"""Nordbank tenant seed. §13 targets 400 requests across every decision band and both
channels; this seeds a representative ~16-request slice for local dev/demo — grow toward
400 once increment 3's UI needs realistic volume/pagination testing."""

from datetime import date, datetime, timedelta, timezone

from app.ai.providers.embeddings import get_embedding_provider
from app.core.audit import record_audit_event
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.core.versioned_config import create_draft, publish
from app.knowledge.ingestion import index_version
from app.models.automation import ConfigResourceKind, WorkflowAction, WorkflowActionStatus, WorkflowRun, WorkflowRunStatus
from app.models.customer import Customer
from app.models.decision import Decision, DecisionType, Evidence, RuleEvaluation
from app.models.department import Department
from app.models.email import Mailbox, MailboxProvider, MailboxStatus
from app.models.feedback import Feedback
from app.models.knowledge import AccessLevel, KnowledgeArticle, KnowledgeGap, KnowledgeGapStatus, KnowledgeVersion, KnowledgeVersionStatus
from app.models.request import Channel, Message, MessageAuthor, Priority, Request, RequestStatus
from app.models.user import RoleName, User

DEPARTMENTS = [
    "Retail Banking",
    "Cards & Payments",
    "Mortgages",
    "Business Banking",
    "Legal & Compliance",
    "Retail Operations",
    "Open Banking",
    "Technical Support",
]

# (email, full_name, role, department_name | None)
USERS = [
    ("priya.raman@nordbank.example", "Priya Raman", RoleName.SUPPORT_AGENT, "Retail Banking"),
    ("mei.chow@nordbank.example", "Mei Lin Chow", RoleName.KNOWLEDGE_MANAGER, None),
    ("daniel.okafor@nordbank.example", "Daniel Okafor", RoleName.DEPT_MANAGER, "Cards & Payments"),
    ("tomas.berg@nordbank.example", "Tomas Berg", RoleName.ADMIN, None),
    ("alice.vandermeer@nordbank.example", "Alice Vandermeer", RoleName.EXECUTIVE, None),
    ("ken.ishida@nordbank.example", "Ken Ishida", RoleName.AUDITOR, None),
    ("super.admin@nordbank.example", "Super Admin", RoleName.SUPER_ADMIN, None),
]

DEV_PASSWORD = "arip-dev-password"

# (customer_email, customer_name, channel, department, category, intent, subject, body,
#  confidence, decision_type, status, priority, rule_hold, evidence)
REQUEST_SAMPLES = [
    ("amara.diallo@example.com", "Amara Diallo", Channel.WEB, "Cards & Payments", "Billing", "dispute_charge",
     "Card dispute — timing of refund", "My refund for a disputed transaction hasn't landed yet, can you confirm the ETA?",
     0.97, DecisionType.AUTO_REPLY, RequestStatus.ANSWERED, Priority.MEDIUM, None,
     [("KB-0412", "v4.2", "vector", 0.94, "§3.1")]),
    ("jonas.weber@example.com", "Jonas Weber", Channel.WEB, "Retail Banking", "General Inquiry", "address_change",
     "Address change request", "I moved recently and need to update my registered address.",
     0.98, DecisionType.AUTO_REPLY, RequestStatus.ANSWERED, Priority.LOW, None,
     [("KB-0500", "v2.0", "vector", 0.96, "§1")]),
    ("sofia.rossi@example.com", "Sofia Rossi", Channel.EMAIL, "Cards & Payments", "Complaint", "dispute_charge",
     "Card dispute — timing of refund follow-up", "Following up again on my card dispute — this is taking too long.",
     0.91, DecisionType.DRAFT_REPLY, RequestStatus.AWAITING_APPROVAL, Priority.HIGH, None,
     [("KB-0412", "v4.2", "vector", 0.91, "§3.1"), ("KB-0455", "v1.0", "vectorless", 0.68, "§2")]),
    ("liam.oconnor@example.com", "Liam O'Connor", Channel.WEB, "Mortgages", "General Inquiry", "restructuring",
     "Loan restructuring question", "Can I restructure my mortgage term without a penalty this year?",
     0.86, DecisionType.DRAFT_REPLY, RequestStatus.AWAITING_APPROVAL, Priority.MEDIUM, None,
     [("KB-0301", "v3.1", "vector", 0.86, "§5.2")]),
    ("mei.tanaka@example.com", "Mei Tanaka", Channel.EMAIL, "Legal & Compliance", "Legal", "account_freeze",
     "Account freeze — legal request", "My account was frozen and I was told to contact legal for details.",
     0.98, DecisionType.HOLD, RequestStatus.HELD, Priority.URGENT,
     ("BR-022", "require_human", 15),
     [("KB-0900", "v1.0", "vector", 0.95, "§1.1")]),
    ("carlos.mendes@example.com", "Carlos Mendes", Channel.WEB, "Business Banking", "Compliance", "kyc_update",
     "KYC document re-upload", "Compliance flagged my account for a KYC refresh — where do I upload documents?",
     0.93, DecisionType.HOLD, RequestStatus.HELD, Priority.HIGH,
     ("BR-014", "require_human", 8),
     [("KB-0810", "v2.3", "vector", 0.9, "§2.1")]),
    ("nina.petrova@example.com", "Nina Petrova", Channel.WEB, "Retail Banking", "Technical Support", "login_issue",
     "Can't log into mobile banking", "The app keeps saying my one-time code is invalid, even right after receiving it.",
     0.74, DecisionType.ASK_CLARIFICATION, RequestStatus.AWAITING_CUSTOMER, Priority.MEDIUM, None, []),
    ("erik.svensson@example.com", "Erik Svensson", Channel.EMAIL, "Open Banking", "Technical Support", "api_access",
     "Open Banking API access request", "We'd like sandbox access for our Open Banking integration but the docs link is broken.",
     0.68, DecisionType.ASK_CLARIFICATION, RequestStatus.AWAITING_CUSTOMER, Priority.LOW, None, []),
    ("fatima.zahra@example.com", "Fatima Zahra", Channel.WEB, "Retail Operations", "Feedback", "branch_experience",
     "Branch visit feedback", "I had a mixed experience at the downtown branch and want to give some specific feedback.",
     0.71, DecisionType.ASK_CLARIFICATION, RequestStatus.AWAITING_CUSTOMER, Priority.LOW, None, []),
    ("oliver.brandt@example.com", "Oliver Brandt", Channel.WEB, "Technical Support", "Technical Support", "outage",
     "Online banking down for me", "Online banking has been showing an error page for the last hour.",
     0.62, DecisionType.ASK_CLARIFICATION, RequestStatus.AWAITING_CUSTOMER, Priority.HIGH, None, []),
    ("grace.kim@example.com", "Grace Kim", Channel.EMAIL, None, "HR", "employment_verification",
     "Employment verification letter", "I need an employment verification letter for a visa application, not sure who handles this.",
     0.41, DecisionType.ROUTE, RequestStatus.ROUTED, Priority.MEDIUM, None, []),
    ("thabo.nkosi@example.com", "Thabo Nkosi", Channel.WEB, None, "Sales", "product_question",
     "Interested in a business credit line", "I run a small business and want to know what credit line options are available.",
     0.55, DecisionType.ROUTE, RequestStatus.ROUTED, Priority.MEDIUM, None, []),
    ("ingrid.larsen@example.com", "Ingrid Larsen", Channel.EMAIL, "Legal & Compliance", "Complaint", "regulatory",
     "Formal complaint — regulatory", "I want to file a formal regulatory complaint about how my case was handled.",
     0.38, DecisionType.ROUTE, RequestStatus.ROUTED, Priority.URGENT, None, []),
    ("bruno.fischer@example.com", "Bruno Fischer", Channel.WEB, None, "Other", "unclear",
     "Not sure who to ask", "Not really sure this is the right place but I have a question about my statements.",
     0.29, DecisionType.ROUTE, RequestStatus.ROUTED, Priority.LOW, None, []),
    ("hana.suzuki@example.com", "Hana Suzuki", Channel.WEB, "Cards & Payments", "Billing", "fee_question",
     "Unexpected fee on statement", "There's a fee on my statement I don't recognize, can you explain it?",
     None, None, RequestStatus.RECEIVED, Priority.MEDIUM, None, []),
    ("victor.almeida@example.com", "Victor Almeida", Channel.EMAIL, "Mortgages", "General Inquiry", "rate_question",
     "Current mortgage rates", "What are your current fixed mortgage rates for a 5-year term?",
     None, None, RequestStatus.RECEIVED, Priority.LOW, None, []),
]

# (title, department, category, content) — content matches the citations already
# referenced by REQUEST_SAMPLES' evidence (KB-0412, KB-0500, KB-0900) so the knowledge
# library and the request evidence tell the same story.
KNOWLEDGE_ARTICLES = [
    (
        "Card dispute refund timing",
        "Cards & Payments",
        "Billing",
        "# Card disputes\nRefunds for a confirmed card dispute are processed within 5 to "
        "7 business days.\n## Escalation\nIf a refund has not arrived after 7 business "
        "days, escalate to the Cards and Payments team for manual review.",
    ),
    (
        "Updating your registered address",
        "Retail Banking",
        "General Inquiry",
        "# Address changes\nCustomers can update their registered address at any time "
        "through online banking or by visiting a branch with valid ID.\n## Processing "
        "time\nAddress changes take effect immediately online, or within 2 business days "
        "when submitted at a branch.",
    ),
    (
        "Account freeze — legal holds",
        "Legal & Compliance",
        "Legal",
        "# Legal holds\nAccounts frozen under a legal hold cannot be unfrozen by support "
        "staff.\n## Contacting legal\nCustomers must be directed to Legal & Compliance "
        "for any account frozen under a court order, regulatory request, or fraud "
        "investigation.",
    ),
]

# (cluster_key, occurrence_count, avg_confidence, sample_request_refs)
KNOWLEDGE_GAPS = [
    ("employment_verification", 34, 0.41, ["REQ-24810"]),
    ("product_question", 21, 0.55, ["REQ-24811"]),
    ("regulatory_complaint", 12, 0.38, ["REQ-24812"]),
    ("unclear_intent", 9, 0.29, ["REQ-24813"]),
]

# (name, email_address, department) — provider is always mailhog (local dev stand-in).
MAILBOXES = [
    ("Retail Banking support", "support@nordbank.example", "Retail Banking"),
    ("Cards & Payments disputes", "disputes@nordbank.example", "Cards & Payments"),
]

# (kind, key, name, config, description) — active version 1 for each. BR-022/BR-014
# match the rule_code values already referenced by REQUEST_SAMPLES' rule_hold entries.
AUTOMATION_RESOURCES = [
    (
        ConfigResourceKind.BUSINESS_RULE, "BR-022", "Legal requests always held for human review",
        {"when": {"category": "Legal"}, "then": {"outcome": "require_human", "priority": 15}},
        "Regulatory requirement — no AI auto-reply on Legal-categorized requests regardless of confidence.",
    ),
    (
        ConfigResourceKind.BUSINESS_RULE, "BR-014", "Compliance KYC requests held for human review",
        {"when": {"category": "Compliance"}, "then": {"outcome": "require_human", "priority": 8}},
        "KYC document requests must be reviewed by Compliance before any reply is sent.",
    ),
    (
        ConfigResourceKind.PROMPT_TEMPLATE, "reply_draft_prompt", "Draft reply generation prompt",
        {"model": "claude-sonnet-4.6", "text": "Answer the customer's question using only the provided citations. Be concise and cite every claim."},
        "Used for draft_reply and auto_reply decisions.",
    ),
    (
        ConfigResourceKind.ROUTING_RULE, "dispute_charge_routing", "Card disputes -> Cards & Payments",
        {"intent": "dispute_charge", "department": "Cards & Payments"},
        "Routes card dispute intents to the Cards & Payments queue.",
    ),
    (
        ConfigResourceKind.WORKFLOW, "card_dispute_escalation", "Card dispute escalation workflow",
        {"nodes": [{"id": "n1", "type": "trigger", "on": "decision.hold"}, {"id": "n2", "type": "notify", "channel": "webhook"}, {"id": "n3", "type": "create_approval_task"}], "edges": [["n1", "n2"], ["n2", "n3"]]},
        "Fires when a card-dispute decision is held for review.",
    ),
]


def seed() -> None:
    db = SessionLocal()
    try:
        dept_by_name = {}
        for name in DEPARTMENTS:
            dept = Department(name=name, slug=name.lower().replace(" & ", "-").replace(" ", "-"))
            db.add(dept)
            db.flush()
            dept_by_name[name] = dept

        user_by_email = {}
        for email, full_name, role, dept_name in USERS:
            user = User(
                email=email,
                full_name=full_name,
                role=role,
                hashed_password=hash_password(DEV_PASSWORD),
                department_id=dept_by_name[dept_name].id if dept_name else None,
            )
            db.add(user)
            db.flush()
            user_by_email[email] = user
            record_audit_event(db, event_type="user.created", actor="seed_script", object_ref=f"user:{user.id}", payload={"email": email, "role": role.value})

        base_time = datetime.now(timezone.utc) - timedelta(days=3)
        for i, (
            cust_email, cust_name, channel, dept_name, category, intent, subject, body,
            confidence, decision_type, status, priority, rule_hold, evidence,
        ) in enumerate(REQUEST_SAMPLES):
            customer = Customer(email=cust_email, full_name=cust_name)
            db.add(customer)
            db.flush()

            req = Request(
                reference=f"REQ-{24800 + i}",
                customer_id=customer.id,
                channel=channel,
                language="en",
                intent=intent,
                category=category,
                status=status,
                priority=priority,
                department_id=dept_by_name[dept_name].id if dept_name else None,
                assignee_id=user_by_email["priya.raman@nordbank.example"].id if dept_name == "Retail Banking" else None,
                sla_first_response_due=base_time + timedelta(hours=4),
                created_at=base_time + timedelta(minutes=i * 37),
            )
            db.add(req)
            db.flush()

            db.add(Message(request_id=req.id, author=MessageAuthor.CUSTOMER, body=body))

            if confidence is not None:
                retrieval_ms = 400 + len(evidence) * 260
                decision = Decision(
                    request_id=req.id,
                    type=decision_type,
                    confidence=confidence,
                    threshold=0.95,
                    signals={
                        "intent_certainty": round(min(confidence + 0.03, 0.99), 2),
                        "retrieval_agreement": round(max(confidence - 0.05, 0.1), 2),
                        "question_coverage": round(min(confidence + 0.01, 0.99), 2),
                        "source_recency": 0.97,
                    },
                    stages=[
                        {"key": "intake", "ms": 180 + i * 3, "meta": {"channel": channel.value, "language": "en"}},
                        {
                            "key": "retrieval",
                            "ms": retrieval_ms,
                            "meta": {
                                "vector_hits": len([e for e in evidence if e[2] == "vector"]),
                                "vectorless_nodes": len([e for e in evidence if e[2] == "vectorless"]),
                            },
                        },
                        {"key": "decision", "ms": 90 + i * 2, "meta": {"rule_overridden": rule_hold is not None}},
                    ],
                    model="claude-sonnet-4.6",
                    latency_ms=850 + i * 13,
                    rule_overridden=rule_hold is not None,
                )
                db.add(decision)
                db.flush()

                if decision_type in (DecisionType.AUTO_REPLY, DecisionType.DRAFT_REPLY):
                    db.add(Message(request_id=req.id, author=MessageAuthor.AI, body=f"Thanks for reaching out — here's what I found regarding: {subject.lower()}."))

                for article_ref, version_ref, mode, score, locator in evidence:
                    db.add(Evidence(decision_id=decision.id, chunk_id=None, retrieval_mode=mode, score=score, locator=locator, article_ref=article_ref, version_ref=version_ref))

                if rule_hold is not None:
                    code, outcome, rule_priority = rule_hold
                    db.add(RuleEvaluation(decision_id=decision.id, rule_code=code, outcome=outcome, priority=rule_priority))

                record_audit_event(
                    db,
                    event_type="decision.recorded",
                    actor="ai_service",
                    object_ref=f"decision:{decision.id}",
                    payload={"request_id": str(req.id), "type": decision_type.value, "confidence": confidence},
                )

            record_audit_event(db, event_type="request.created", actor="seed_script", object_ref=f"request:{req.id}", payload={"reference": req.reference})

            if status == RequestStatus.ANSWERED:
                rating = 5 if decision_type == DecisionType.AUTO_REPLY else 4
                db.add(Feedback(request_id=req.id, rating=rating, comment="Quick and clear answer." if rating == 5 else "Helpful, took a bit of editing."))

        embedding_provider = get_embedding_provider()
        for title, dept_name, category, content in KNOWLEDGE_ARTICLES:
            article = KnowledgeArticle(title=title, department_id=dept_by_name[dept_name].id, category=category, tags=[])
            db.add(article)
            db.flush()
            kv = KnowledgeVersion(
                article_id=article.id,
                version="v1.0",
                status=KnowledgeVersionStatus.APPROVED,
                effective_from=date.today() - timedelta(days=30),
                access_level=AccessLevel.INTERNAL,
                content=content,
                reviewer_id=user_by_email["mei.chow@nordbank.example"].id,
            )
            db.add(kv)
            db.flush()
            index_version(db, kv, embedding_provider)
            kv.status = KnowledgeVersionStatus.INDEXED
            record_audit_event(db, event_type="knowledge.approved", actor="seed_script", object_ref=f"knowledge_version:{kv.id}", payload={"version": "v1.0"})

        for cluster_key, occurrence_count, avg_confidence, sample_refs in KNOWLEDGE_GAPS:
            db.add(KnowledgeGap(cluster_key=cluster_key, occurrence_count=occurrence_count, avg_confidence=avg_confidence, status=KnowledgeGapStatus.OPEN, sample_request_refs=sample_refs))

        for name, email_address, dept_name in MAILBOXES:
            db.add(Mailbox(name=name, email_address=email_address, provider=MailboxProvider.MAILHOG, department_id=dept_by_name[dept_name].id, status=MailboxStatus.CONNECTED))

        admin_user = user_by_email["tomas.berg@nordbank.example"]
        for kind, key, name, config, description in AUTOMATION_RESOURCES:
            resource = create_draft(db, kind=kind, key=key, name=name, config=config, description=description, user=admin_user)
            publish(db, resource)
            record_audit_event(db, event_type="config.published", actor=admin_user.email, object_ref=f"config_resource:{resource.id}", payload={"kind": kind.value, "key": key, "version": 1})

        run_time = datetime.now(timezone.utc) - timedelta(hours=6)
        succeeded_run = WorkflowRun(workflow_key="card_dispute_escalation", status=WorkflowRunStatus.SUCCEEDED, started_at=run_time, finished_at=run_time + timedelta(seconds=3))
        db.add(succeeded_run)
        db.flush()
        db.add(WorkflowAction(run_id=succeeded_run.id, action_type="notify_webhook", status=WorkflowActionStatus.SUCCEEDED, executed_at=run_time + timedelta(seconds=1)))
        db.add(WorkflowAction(run_id=succeeded_run.id, action_type="create_approval_task", status=WorkflowActionStatus.SUCCEEDED, executed_at=run_time + timedelta(seconds=2)))

        failed_run = WorkflowRun(workflow_key="card_dispute_escalation", status=WorkflowRunStatus.FAILED, started_at=run_time + timedelta(hours=1), finished_at=run_time + timedelta(hours=1, seconds=2))
        db.add(failed_run)
        db.flush()
        db.add(WorkflowAction(run_id=failed_run.id, action_type="notify_webhook", status=WorkflowActionStatus.FAILED, error_message="Webhook endpoint returned 503", executed_at=run_time + timedelta(hours=1, seconds=1)))

        db.commit()
        print(f"Seeded {len(DEPARTMENTS)} departments, {len(USERS)} users, {len(REQUEST_SAMPLES)} requests.")
        print(f"Seeded {len(KNOWLEDGE_ARTICLES)} knowledge articles, {len(KNOWLEDGE_GAPS)} knowledge gaps, {len(MAILBOXES)} mailboxes.")
        print(f"Seeded {len(AUTOMATION_RESOURCES)} automation resources, 2 workflow runs.")
        print(f"Dev password for all seeded users: {DEV_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
