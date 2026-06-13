"""
Multi-Agent Database Models
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, Text, JSON, Float, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.database.connection import Base


class Agent(Base):
    """Agent instance model"""
    __tablename__ = "agents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    team_id = Column(UUID(as_uuid=True), ForeignKey("agent_teams.id"), nullable=True)
    
    name = Column(String(100), nullable=False)
    agent_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    model = Column(String(100), nullable=True)
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=4096)
    capabilities = Column(JSON, default=list)
    tools = Column(JSON, default=list)
    system_prompt = Column(Text, nullable=True)
    
    status = Column(String(50), default="idle")
    current_task = Column(String(100), nullable=True)
    progress = Column(Float, default=0.0)
    results = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="agents")
    team = relationship("AgentTeam", back_populates="agents")
    messages = relationship("AgentMessage", back_populates="agent", cascade="all, delete-orphan")
    tasks = relationship("AgentTaskModel", back_populates="agent", cascade="all, delete-orphan")


class AgentTeam(Base):
    """Team of agents working together"""
    __tablename__ = "agent_teams"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    name = Column(String(100), nullable=False)
    goal = Column(Text, nullable=False)
    collaboration_mode = Column(String(50), default="sequential")
    max_agents_parallel = Column(Integer, default=3)
    shared_context = Column(JSON, default=dict)
    supervisor_id = Column(UUID(as_uuid=True), nullable=True)
    
    status = Column(String(50), default="idle")
    results = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="agent_teams")
    agents = relationship("Agent", back_populates="team", cascade="all, delete-orphan")
    tasks = relationship("TeamTask", back_populates="team", cascade="all, delete-orphan")
    messages = relationship("TeamMessage", back_populates="team", cascade="all, delete-orphan")


class AgentTaskModel(Base):
    """Task assigned to an agent"""
    __tablename__ = "agent_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    team_id = Column(UUID(as_uuid=True), ForeignKey("agent_teams.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    task_id = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    context = Column(JSON, default=dict)
    priority = Column(Integer, default=0)
    deadline = Column(DateTime, nullable=True)
    dependencies = Column(JSON, default=list)
    expected_output = Column(Text, nullable=True)
    
    status = Column(String(50), default="pending")
    progress = Column(Float, default=0.0)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    assigned_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    agent = relationship("Agent", back_populates="tasks")
    team = relationship("AgentTeam", back_populates="tasks")


class TeamTask(Base):
    """High-level task for a team"""
    __tablename__ = "team_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("agent_teams.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    task_id = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    context = Column(JSON, default=dict)
    status = Column(String(50), default="pending")
    assigned_agent_id = Column(UUID(as_uuid=True), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    team = relationship("AgentTeam", back_populates="tasks")


class AgentMessage(Base):
    """Message in agent conversation"""
    __tablename__ = "agent_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    message_id = Column(String(100), nullable=False, unique=True)
    sender_id = Column(String(100), nullable=True)
    sender_type = Column(String(50), nullable=True)
    recipient_id = Column(String(100), nullable=True)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    attachments = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    agent = relationship("Agent", back_populates="messages")


class TeamMessage(Base):
    """Message in team communication"""
    __tablename__ = "team_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("agent_teams.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    message_id = Column(String(100), nullable=False, unique=True)
    sender_id = Column(String(100), nullable=True)
    sender_type = Column(String(50), nullable=True)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    metadata = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    team = relationship("AgentTeam", back_populates="messages")


class MultiAgentExecution(Base):
    """Multi-agent execution session"""
    __tablename__ = "multi_agent_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    team_id = Column(UUID(as_uuid=True), ForeignKey("agent_teams.id"), nullable=True)
    
    execution_id = Column(String(100), nullable=False, unique=True)
    goal = Column(Text, nullable=False)
    status = Column(String(50), default="started")
    
    total_agents = Column(Integer, default=0)
    active_agents = Column(Integer, default=0)
    completed_agents = Column(Integer, default=0)
    failed_agents = Column(Integer, default=0)
    
    progress = Column(Float, default=0.0)
    results = Column(JSON, default=dict)
    artifacts = Column(JSON, default=list)
    report = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)