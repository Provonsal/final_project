
import uuid

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import UUID, create_engine, Column, Integer, String, DateTime, Boolean, LargeBinary, ForeignKey, Text, Enum
from sqlalchemy.dialects.postgresql.types import BYTEA

from uuid import uuid4

from datetime import datetime, timezone

from app.models.RateEnum import RateEnum
from app.models.RoleEnum import RoleEnum
from app.models.TaskStatusEnum import TaskStatusEnum

from .base import Base, BaseModel


class User(BaseModel):
    """
    User model representing a user in the system.
    
    Attributes:
        email (str): The email address of the user, must be unique and not null.
        name (str): The name of the user, must not be null.
        role (RoleEnum): The role of the user, defined by the RoleEnum.
        is_active (bool): Indicates whether the user account is active. Defaults to True.
    
    Relationships:
        mtm_teams_users (list[TeamUser]): Many-to-many relationship with teams.
        tasks (list[Task]): One-to-many relationship with tasks assigned to the user.
        rates (list[TaskRate]): One-to-many relationship for user ratings.
        meetings_mtm_members (list[MeetingUser]): Many-to-many relationship with meetings.
        user_credentials (UserCredentials): One-to-one relationship with user credentials.
        meetings (list[Meeting]): One-to-many relationship with meetings created by the user.
        authored_comments (list[Comment]): One-to-many relationship with comments authored by the user.
    """
    
    __tablename__ = 'users'

    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum, name="user_role_enum", length=20, native_enum=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    mtm_teams_users: Mapped[list["TeamUser"]] = relationship(
        back_populates='user',
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    tasks: Mapped[list["Task"]] = relationship(
        back_populates='user',
        passive_deletes=True,             # ← БД заблокирует удаление юзера с задачами
    )
    rates: Mapped[list["TaskRate"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    meetings_mtm_members: Mapped[list["MeetingUser"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    user_credentials: Mapped["UserCredentials"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
        passive_deletes=True,
    )
    meetings: Mapped[list["Meeting"]] = relationship(
        back_populates="user",
        passive_deletes=True,             # ← БД заблокирует, если юзер — создатель митингов
    )
    authored_comments: Mapped[list["Comment"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class UserCredentials(BaseModel):
    """
    UserCredentials model representing the credentials of a user.
    
    Attributes:
        user_id (uuid.UUID): The unique identifier of the user.
        salt (bytes): The salt used for hashing the password.
        password_hash (bytes): The hashed password of the user.
        algorithm (str): The hashing algorithm used for the password.
    """
    
    __tablename__ = 'user_credentials'

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    salt: Mapped[bytes] = mapped_column(BYTEA(16), nullable=False)
    password_hash: Mapped[bytes] = mapped_column(BYTEA(32), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(16), default="sha256", nullable=False, index=True)

    user: Mapped["User"] = relationship(back_populates="user_credentials")


class Task(BaseModel):
    """
    Task model representing a task assigned to a user.
    
    Attributes:
        title (str): The title of the task.
        description (str): A detailed description of the task.
        assignee (uuid.UUID): The unique identifier of the user assigned to the task.
        due_date (datetime): The due date for the task completion.
        status (TaskStatusEnum): The current status of the task.
        connected_to_team (uuid.UUID): The unique identifier of the team associated with the task.
    """
    
    __tablename__ = 'tasks'

    title: Mapped[str] = mapped_column(String(70), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    assignee: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[TaskStatusEnum] = mapped_column(Enum(TaskStatusEnum, name="task_status_enum", length=20, native_enum=True))
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),   # ← добавить ondelete
        nullable=False,
    )

    team: Mapped["Team"] = relationship(back_populates="tasks")
    user: Mapped["User"] = relationship(back_populates="tasks")
    task_comments: Mapped[list["Comment"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    rate: Mapped["TaskRate"] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        uselist=False,
        passive_deletes=True,
    )


class Comment(BaseModel):
    """
    Comment model representing a comment on a task.
    
    Attributes:
        task_id (uuid.UUID): The unique identifier of the task the comment is associated with.
        created_at (datetime): The timestamp when the comment was created.
        text (str): The content of the comment.
        author (uuid.UUID): The unique identifier of the user who authored the comment.
    """
    
    __tablename__ = 'commentaries'

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),   # ← добавить
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),   # ← добавить
        nullable=False,
    )

    task: Mapped["Task"] = relationship(back_populates="task_comments")
    user: Mapped["User"] = relationship(back_populates="authored_comments")


class RefreshToken(BaseModel):
    """
    RefreshToken model representing a refresh token for user sessions.
    
    Attributes:
        user_id (uuid.UUID): The unique identifier of the user associated with the token.
        created_at (datetime): The timestamp when the token was created.
        expire_date (int): The expiration date of the token in epoch time.
        revoked (bool): Indicates whether the token has been revoked.
        token_hash (bytes): The hashed value of the token.
        family_id (uuid.UUID): The unique identifier for the family of tokens.
    """
    
    __tablename__ = 'refresh_tokens'

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    expire_date: Mapped[int] = mapped_column(Integer, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False)
    token_hash: Mapped[bytes] = mapped_column(BYTEA(32), nullable=False)
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, default=uuid4)


class Team(BaseModel):
    """
    Team model representing a group of users.
    
    Attributes:
        name (str): The name of the team.
        max_per_team (int): The maximum number of members allowed in the team.
        owner (uuid.UUID): The unique identifier of the user who owns the team.
    """
    
    __tablename__ = 'teams'

    name: Mapped[str] = mapped_column(String(40), nullable=False)
    max_per_team: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    owner: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    mtm_teams_users: Mapped[list["TeamUser"]] = relationship(
        back_populates='team',
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    invite_codes: Mapped[list["TeamInviteCode"]] = relationship(
        back_populates='team',
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="team",
        cascade="all, delete-orphan",     # ← добавить каскад
        passive_deletes=True,
    )
    meets: Mapped[list["Meeting"]] = relationship(
        back_populates="team",
        cascade="all, delete-orphan",     # ← добавить каскад
        passive_deletes=True,
    )


class TeamUser(Base):
    """
    TeamUser model representing the association between teams and users.
    
    Attributes:
        team_id (uuid.UUID): The unique identifier of the team.
        user_id (uuid.UUID): The unique identifier of the user.
    """
    
    __tablename__ = 'mtm_team_user'

    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('teams.id', ondelete="CASCADE"),   # ← добавить
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete="CASCADE"),   # ← добавить
        primary_key=True,
    )

    user: Mapped["User"] = relationship(back_populates="mtm_teams_users")
    team: Mapped["Team"] = relationship(back_populates="mtm_teams_users")


class TeamInviteCode(BaseModel):
    """
    TeamInviteCode model representing an invitation code for teams.
    
    Attributes:
        creator (uuid.UUID): The unique identifier of the user who created the invite code.
        active (bool): Indicates whether the invite code is active.
        connected_to (uuid.UUID): The unique identifier of the team associated with the invite code.
        body (str): The content of the invite code.
    """
    
    __tablename__ = 'invite_codes'

    creator: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    connected_to: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('teams.id', ondelete="CASCADE"),   # ← добавить
        nullable=False,
    )
    body: Mapped[str] = mapped_column(String(40), nullable=False)

    team: Mapped["Team"] = relationship(back_populates="invite_codes")


class TaskRate(BaseModel):
    """
    TaskRate model representing the rating given to a task by a user.
    
    Attributes:
        rate (RateEnum): The rating given to the task.
        rater (uuid.UUID): The unique identifier of the user who rated the task.
        task_id (uuid.UUID): The unique identifier of the task being rated.
    """
    
    __tablename__ = 'task_rates'

    rate: Mapped[RateEnum] = mapped_column(Enum(RateEnum, name="task_rate_readable_enum", length=20, native_enum=True), default=RateEnum.UNRATED)
    rater: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete="CASCADE"),   # ← добавить
        nullable=False,
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('tasks.id', ondelete="CASCADE"),   # ← добавить
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="rates")
    task: Mapped["Task"] = relationship(back_populates="rate")


class Meeting(BaseModel):
    """
    Meeting model representing a scheduled meeting.
    
    Attributes:
        starts_at (datetime): The start time of the meeting.
        ends_at (datetime): The end time of the meeting.
        max_members (int): The maximum number of members allowed in the meeting.
        related_team (uuid.UUID): The unique identifier of the team associated with the meeting.
        creator (uuid.UUID): The unique identifier of the user who created the meeting.
    """
    
    __tablename__ = 'meets'

    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_members: Mapped[int] = mapped_column(Integer, default=10)
    related_team: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),   # ← добавить
        nullable=False,
    )
    creator: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),                       # ← RESTRICT (по умолчанию)
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="meetings")
    members: Mapped[list["MeetingUser"]] = relationship(
        back_populates='meet',
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    team: Mapped["Team"] = relationship(back_populates="meets")


class MeetingUser(Base):
    """
    MeetingUser model representing the association between meetings and users.
    
    Attributes:
        meeting_id (uuid.UUID): The unique identifier of the meeting.
        user_id (uuid.UUID): The unique identifier of the user.
    """
    
    __tablename__ = 'mtm_meeting_user'

    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meets.id", ondelete="CASCADE"),   # ← добавить
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),   # ← добавить
        primary_key=True,
    )

    meet: Mapped["Meeting"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="meetings_mtm_members")
