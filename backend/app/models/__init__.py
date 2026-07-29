"""Import every model module so Base.metadata is fully populated for Alembic autogenerate."""

from app.models.audit import AuditEvent
from app.models.automation import (
    ConfigResource,
    ConfigResourceKind,
    ConfigResourceStatus,
    WorkflowAction,
    WorkflowActionStatus,
    WorkflowRun,
    WorkflowRunStatus,
)
from app.models.customer import Customer
from app.models.decision import Decision, DecisionType, Evidence, RuleEvaluation
from app.models.department import Department
from app.models.email import Mailbox, MailboxProvider, MailboxStatus, ParseFailure
from app.models.feedback import Feedback
from app.models.knowledge import (
    AccessLevel,
    KnowledgeArticle,
    KnowledgeChunk,
    KnowledgeGap,
    KnowledgeGapStatus,
    KnowledgeNode,
    KnowledgeVersion,
    KnowledgeVersionStatus,
)
from app.models.settings import AppSetting
from app.models.request import (
    Attachment,
    Channel,
    Message,
    MessageAuthor,
    Priority,
    Request,
    RequestStatus,
)
from app.models.user import RoleName, User

__all__ = [
    "AuditEvent",
    "ConfigResource",
    "ConfigResourceKind",
    "ConfigResourceStatus",
    "WorkflowAction",
    "WorkflowActionStatus",
    "WorkflowRun",
    "WorkflowRunStatus",
    "AppSetting",
    "Customer",
    "Decision",
    "DecisionType",
    "Evidence",
    "RuleEvaluation",
    "Department",
    "Mailbox",
    "MailboxProvider",
    "MailboxStatus",
    "ParseFailure",
    "Feedback",
    "AccessLevel",
    "KnowledgeArticle",
    "KnowledgeChunk",
    "KnowledgeGap",
    "KnowledgeGapStatus",
    "KnowledgeNode",
    "KnowledgeVersion",
    "KnowledgeVersionStatus",
    "Attachment",
    "Channel",
    "Message",
    "MessageAuthor",
    "Priority",
    "Request",
    "RequestStatus",
    "RoleName",
    "User",
]
