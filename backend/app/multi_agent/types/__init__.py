"""
Multi-Agent Type Definitions
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AgentType(str, Enum):
    """Types of specialized agents"""
    PLANNER = "planner"
    RESEARCHER = "researcher"
    CODER = "coder"
    REVIEWER = "reviewer"
    EXECUTOR = "executor"
    SYNTHESIZER = "synthesizer"
    COORDINATOR = "coordinator"
    GENERALIST = "generalist"


class AgentStatus(str, Enum):
    """Agent lifecycle status"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    WORKING = "working"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


class TaskStatus(str, Enum):
    """Task assignment status"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CollaborationMode(str, Enum):
    """How agents collaborate"""
    SEQUENTIAL = "sequential"  # One agent after another
    PARALLEL = "parallel"      # Multiple agents at once
    HIERARCHICAL = "hierarchical"  # Supervisor + workers
    DEBATE = "debate"          # Agents discuss and vote


class MessageRole(str, Enum):
    """Role in agent communication"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    AGENT = "agent"
    TOOL = "tool"


class AgentConfig(BaseModel):
    """Configuration for an agent instance"""
    agent_type: AgentType
    name: str
    description: str
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    capabilities: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    system_prompt: Optional[str] = None


class AgentTask(BaseModel):
    """Task assigned to an agent"""
    task_id: str
    description: str
    context: Dict[str, Any] = Field(default_factory=dict)
    priority: int = 0
    deadline: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    expected_output: Optional[str] = None


class AgentMessage(BaseModel):
    """Message between agents"""
    message_id: str
    sender_id: Optional[str] = None
    sender_type: Optional[AgentType] = None
    recipient_id: Optional[str] = None
    role: MessageRole
    content: str
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentState(BaseModel):
    """Current state of an agent"""
    agent_id: str
    agent_type: AgentType
    name: str
    status: AgentStatus
    current_task: Optional[str] = None
    progress: float = 0.0
    messages: List[AgentMessage] = Field(default_factory=list)
    results: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class TeamConfig(BaseModel):
    """Configuration for a team of agents"""
    team_id: str
    name: str
    goal: str
    agents: List[AgentConfig]
    collaboration_mode: CollaborationMode = CollaborationMode.SEQUENTIAL
    max_agents_parallel: int = 3
    shared_context: Dict[str, Any] = Field(default_factory=dict)
    supervisor_id: Optional[str] = None


class TeamState(BaseModel):
    """Current state of an agent team"""
    team_id: str
    name: str
    goal: str
    status: AgentStatus
    agents: Dict[str, AgentState] = Field(default_factory=dict)
    tasks: Dict[str, AgentTask] = Field(default_factory=dict)
    messages: List[AgentMessage] = Field(default_factory=list)
    shared_context: Dict[str, Any] = Field(default_factory=dict)
    results: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None