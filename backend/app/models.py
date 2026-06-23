from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class OrgUnit(Base):
    __tablename__ = "org_units"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("org_units.id"))
    path: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    department_code: Mapped[str | None] = mapped_column(String(80))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    parent: Mapped["OrgUnit | None"] = relationship(remote_side=[id], back_populates="children")
    children: Mapped[list["OrgUnit"]] = relationship(back_populates="parent")
    staffing_lines: Mapped[list["StaffingLine"]] = relationship(back_populates="org_unit")


class StaffingLine(Base):
    __tablename__ = "staffing_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_unit_id: Mapped[int] = mapped_column(ForeignKey("org_units.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    position_code: Mapped[str | None] = mapped_column(String(80))
    approved_fte: Mapped[float] = mapped_column(Float, nullable=False)
    reported_occupied_fte: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    org_unit: Mapped[OrgUnit] = relationship(back_populates="staffing_lines")
    assignments: Mapped[list["Assignment"]] = relationship(back_populates="staffing_line")


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_employee_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    username: Mapped[str | None] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    first_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    system_role: Mapped[str] = mapped_column(String(32), nullable=False)
    is_hr: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    assignments: Mapped[list["Assignment"]] = relationship(back_populates="employee")
    created_campaigns: Mapped[list["Campaign"]] = relationship(
        back_populates="creator",
        foreign_keys="Campaign.created_by_id",
    )
    auth_login_tokens: Mapped[list["AuthLoginToken"]] = relationship(back_populates="employee")
    auth_sessions: Mapped[list["AuthSession"]] = relationship(back_populates="employee")
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="recipient",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class AuthLoginToken(Base):
    __tablename__ = "auth_login_tokens"
    __table_args__ = (
        Index("ix_auth_login_tokens_employee_expires", "employee_id", "expires_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    employee: Mapped[Employee] = relationship(back_populates="auth_login_tokens")


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        Index("ix_auth_sessions_employee_expires", "employee_id", "expires_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime)

    employee: Mapped[Employee] = relationship(back_populates="auth_sessions")


class AiConfiguration(Base):
    __tablename__ = "ai_configurations"

    id: Mapped[int] = mapped_column(primary_key=True)
    mode: Mapped[str] = mapped_column(String(32), default="default", nullable=False)
    provider: Mapped[str] = mapped_column(String(64), default="off", nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(500))
    model_name: Mapped[str | None] = mapped_column(String(255))
    api_token: Mapped[str | None] = mapped_column(String(1000))
    clarity_threshold: Mapped[int] = mapped_column(default=70, nullable=False)
    followup_strictness: Mapped[str] = mapped_column(String(32), default="balanced", nullable=False)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    updated_by: Mapped[Employee | None] = relationship()


class QuestionnaireQuestionSetting(Base):
    __tablename__ = "questionnaire_question_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    ai_check_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    good_example: Mapped[str | None] = mapped_column(Text)
    bad_example: Mapped[str | None] = mapped_column(Text)
    requirements: Mapped[str | None] = mapped_column(Text)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    updated_by: Mapped[Employee | None] = relationship()


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_assignment_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    staffing_line_id: Mapped[int] = mapped_column(ForeignKey("staffing_lines.id"), nullable=False)
    manager_assignment_id: Mapped[int | None] = mapped_column(ForeignKey("assignments.id"))
    fte: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    assignment_role: Mapped[str] = mapped_column(String(32), default="primary", nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    employee: Mapped[Employee] = relationship(back_populates="assignments")
    staffing_line: Mapped[StaffingLine] = relationship(back_populates="assignments")
    manager: Mapped["Assignment | None"] = relationship(remote_side=[id], back_populates="reports")
    reports: Mapped[list["Assignment"]] = relationship(back_populates="manager")
    campaign_participations: Mapped[list["CampaignParticipant"]] = relationship(
        back_populates="assignment"
    )


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        Index("ix_campaigns_demo_status_id", "is_demo", "status", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    due_at: Mapped[date | None] = mapped_column(Date)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    creator: Mapped[Employee] = relationship(
        back_populates="created_campaigns",
        foreign_keys=[created_by_id],
    )
    participants: Mapped[list["CampaignParticipant"]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
    )
    waves: Mapped[list["CampaignWave"]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
        order_by="CampaignWave.id",
    )


class CampaignWave(Base):
    __tablename__ = "campaign_waves"
    __table_args__ = (
        Index("ix_campaign_waves_campaign_status", "campaign_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    due_at: Mapped[date | None] = mapped_column(Date)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    campaign: Mapped[Campaign] = relationship(back_populates="waves")
    creator: Mapped[Employee] = relationship()
    participants: Mapped[list["CampaignParticipant"]] = relationship(back_populates="wave")
    unit_selections: Mapped[list["CampaignWaveUnitSelection"]] = relationship(
        back_populates="wave",
        cascade="all, delete-orphan",
    )


class CampaignWaveUnitSelection(Base):
    __tablename__ = "campaign_wave_unit_selections"
    __table_args__ = (
        UniqueConstraint("campaign_wave_id", "org_unit_id", name="uq_campaign_wave_org_unit"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_wave_id: Mapped[int] = mapped_column(ForeignKey("campaign_waves.id"), nullable=False)
    org_unit_id: Mapped[int] = mapped_column(ForeignKey("org_units.id"), nullable=False)
    inclusion_status: Mapped[str] = mapped_column(String(32), default="included", nullable=False)
    selected_by_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    wave: Mapped[CampaignWave] = relationship(back_populates="unit_selections")
    org_unit: Mapped[OrgUnit] = relationship()
    selected_by: Mapped[Employee] = relationship()


class CampaignParticipant(Base):
    __tablename__ = "campaign_participants"
    __table_args__ = (
        UniqueConstraint("campaign_id", "assignment_id", name="uq_campaign_assignment"),
        Index(
            "ix_campaign_participants_campaign_status",
            "campaign_id",
            "participation_status",
            "expected_to_submit",
        ),
        Index(
            "ix_campaign_participants_assignment_status",
            "assignment_id",
            "participation_status",
            "expected_to_submit",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    campaign_wave_id: Mapped[int | None] = mapped_column(ForeignKey("campaign_waves.id"))
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id"), nullable=False)
    participation_status: Mapped[str] = mapped_column(String(32), default="included", nullable=False)
    expected_to_submit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    included_by_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    included_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    campaign: Mapped[Campaign] = relationship(back_populates="participants")
    wave: Mapped[CampaignWave | None] = relationship(back_populates="participants")
    assignment: Mapped[Assignment] = relationship(back_populates="campaign_participations")
    profile: Mapped["EmployeeProfile | None"] = relationship(
        back_populates="participant",
        cascade="all, delete-orphan",
        uselist=False,
    )


class EmployeeProfile(Base):
    __tablename__ = "employee_profiles"
    __table_args__ = (
        Index("ix_employee_profiles_workflow_status", "workflow_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_participant_id: Mapped[int] = mapped_column(
        ForeignKey("campaign_participants.id"),
        nullable=False,
        unique=True,
    )
    workflow_status: Mapped[str] = mapped_column(String(32), default="not_started", nullable=False)
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    participant: Mapped[CampaignParticipant] = relationship(back_populates="profile")
    draft: Mapped["ProfileDraft | None"] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        uselist=False,
    )
    revisions: Mapped[list["ProfileRevision"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="ProfileRevision.revision_no",
    )
    review_events: Mapped[list["ProfileReviewEvent"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="ProfileReviewEvent.id",
    )


class ProfileDraft(Base):
    __tablename__ = "profile_drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_profile_id: Mapped[int] = mapped_column(
        ForeignKey("employee_profiles.id"),
        nullable=False,
        unique=True,
    )
    answers_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    ai_usage_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    profile: Mapped[EmployeeProfile] = relationship(back_populates="draft")


class ProfileRevision(Base):
    __tablename__ = "profile_revisions"
    __table_args__ = (
        UniqueConstraint("employee_profile_id", "revision_no", name="uq_profile_revision_no"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_profile_id: Mapped[int] = mapped_column(
        ForeignKey("employee_profiles.id"),
        nullable=False,
    )
    revision_no: Mapped[int] = mapped_column(nullable=False)
    based_on_revision_id: Mapped[int | None] = mapped_column(ForeignKey("profile_revisions.id"))
    answers_json: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    assistant_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    assistance_level: Mapped[str] = mapped_column(String(32), nullable=False)
    assisted_sections_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    ai_check_status: Mapped[str] = mapped_column(String(32), nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime)

    profile: Mapped[EmployeeProfile] = relationship(back_populates="revisions")
    review_events: Mapped[list["ProfileReviewEvent"]] = relationship(back_populates="revision")


class ProfileReviewEvent(Base):
    __tablename__ = "profile_review_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_profile_id: Mapped[int] = mapped_column(
        ForeignKey("employee_profiles.id"),
        nullable=False,
    )
    revision_id: Mapped[int] = mapped_column(ForeignKey("profile_revisions.id"), nullable=False)
    actor_employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    profile: Mapped[EmployeeProfile] = relationship(back_populates="review_events")
    revision: Mapped[ProfileRevision] = relationship(back_populates="review_events")
    actor: Mapped[Employee] = relationship()


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_demo_type_code", "is_demo", "document_type", "document_code"),
        Index("ix_documents_demo_checksum", "is_demo", "checksum"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    document_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(80), default="1.0", nullable=False)
    document_status: Mapped[str] = mapped_column(String(32), default="confirmed", nullable=False)
    source_file_path: Mapped[str | None] = mapped_column(String(1000))
    extracted_text_path: Mapped[str | None] = mapped_column(String(1000))
    content_text: Mapped[str | None] = mapped_column(Text)
    ocr_quality_status: Mapped[str] = mapped_column(String(32), default="manual_demo", nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(128))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    links: Mapped[list["DocumentLink"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentLink(Base):
    __tablename__ = "document_links"
    __table_args__ = (
        UniqueConstraint("document_id", "target_type", "target_id", name="uq_document_target"),
        Index("ix_document_links_target_demo", "target_type", "target_id", "is_demo"),
        Index("ix_document_links_document_status", "document_id", "link_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_id: Mapped[int] = mapped_column(nullable=False)
    link_status: Mapped[str] = mapped_column(String(32), default="confirmed", nullable=False)
    confirmed_by_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    document: Mapped[Document] = relationship(back_populates="links")
    confirmed_by: Mapped[Employee | None] = relationship()


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_recipient_read_created", "recipient_employee_id", "read_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    notification_type: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(80))
    target_section: Mapped[str | None] = mapped_column(String(80))
    dedupe_key: Mapped[str | None] = mapped_column(String(255), unique=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    recipient: Mapped[Employee] = relationship(back_populates="notifications")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(80), nullable=False)
    details_json: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
