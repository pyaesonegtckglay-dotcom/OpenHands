"""
Agent Manager Service
Handles agent lifecycle, task assignment, and state management
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from app.database.connection import get_pool
from app.multi_agent.types import AgentType, AgentStatus, AgentTask, AgentMessage, AgentState, MessageRole
from app.multi_agent.services.agent_registry import agent_registry

logger = logging.getLogger(__name__)


class AgentManager:
    """Manages agent lifecycle and operations"""
    
    def __init__(self):
        self._active_agents: Dict[str, AgentState] = {}
    
    async def create_agent(
        self,
        user_id: str,
        agent_type: AgentType,
        name: Optional[str] = None,
        team_id: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """Create a new agent instance"""
        agent_id = str(uuid.uuid4())
        config = agent_registry.get(agent_type)
        
        if not config:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        agent_name = name or config.name
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO agents (id, user_id, team_id, name, agent_type, description, model, temperature, max_tokens, capabilities, tools, system_prompt, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """, 
                uuid.UUID(agent_id),
                uuid.UUID(user_id),
                uuid.UUID(team_id) if team_id else None,
                agent_name,
                agent_type.value,
                config.description,
                model or config.model,
                temperature,
                max_tokens,
                config.capabilities,
                config.tools,
                config.system_prompt,
                AgentStatus.IDLE.value
            )
        
        # Track in memory
        self._active_agents[agent_id] = AgentState(
            agent_id=agent_id,
            agent_type=agent_type,
            name=agent_name,
            status=AgentStatus.IDLE,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )
        
        logger.info(f"Created agent {agent_id} of type {agent_type.value}")
        return {"agent_id": agent_id, "name": agent_name, "type": agent_type.value}
    
    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent details"""
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM agents WHERE id = $1", uuid.UUID(agent_id))
            if row:
                return dict(row)
            return None
    
    async def list_agents(self, user_id: str, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List agents for a user"""
        pool = await get_pool()
        async with pool.acquire() as conn:
            if team_id:
                rows = await conn.fetch(
                    "SELECT * FROM agents WHERE user_id = $1 AND team_id = $2 ORDER BY created_at DESC",
                    uuid.UUID(user_id),
                    uuid.UUID(team_id)
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM agents WHERE user_id = $1 ORDER BY created_at DESC",
                    uuid.UUID(user_id)
                )
            return [dict(row) for row in rows]
    
    async def update_agent_status(self, agent_id: str, status: AgentStatus, progress: float = None) -> bool:
        """Update agent status"""
        pool = await get_pool()
        async with pool.acquire() as conn:
            if progress is not None:
                await conn.execute(
                    "UPDATE agents SET status = $1, progress = $2, updated_at = NOW() WHERE id = $3",
                    status.value, progress, uuid.UUID(agent_id)
                )
            else:
                await conn.execute(
                    "UPDATE agents SET status = $1, updated_at = NOW() WHERE id = $2",
                    status.value, uuid.UUID(agent_id)
                )
        
        # Update memory
        if agent_id in self._active_agents:
            self._active_agents[agent_id].status = status
            if progress is not None:
                self._active_agents[agent_id].progress = progress
            self._active_agents[agent_id].updated_at = datetime.utcnow().isoformat()
        
        return True
    
    async def assign_task(self, agent_id: str, task: AgentTask) -> bool:
        """Assign a task to an agent"""
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO agent_tasks (id, agent_id, user_id, task_id, description, context, priority, dependencies, expected_output, status)
                VALUES ($1, $2, (SELECT user_id FROM agents WHERE id = $2), $3, $4, $5, $6, $7, $8, $9)
            """,
                uuid.uuid4(),
                uuid.UUID(agent_id),
                task.task_id,
                task.description,
                task.context,
                task.priority,
                task.dependencies,
                task.expected_output,
                "assigned"
            )
            
            await conn.execute(
                "UPDATE agents SET current_task = $1, status = $2, updated_at = NOW() WHERE id = $3",
                task.task_id, AgentStatus.WORKING.value, uuid.UUID(agent_id)
            )
        
        # Update memory
        if agent_id in self._active_agents:
            self._active_agents[agent_id].current_task = task.task_id
            self._active_agents[agent_id].status = AgentStatus.WORKING
        
        return True
    
    async def complete_task(self, agent_id: str, task_id: str, result: Dict[str, Any]) -> bool:
        """Mark task as completed"""
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """UPDATE agent_tasks SET status = $1, result = $2, completed_at = NOW() 
                   WHERE task_id = $3 AND agent_id = $4""",
                "completed", result, task_id, uuid.UUID(agent_id)
            )
            await conn.execute(
                "UPDATE agents SET current_task = NULL, status = $1, results = $2, updated_at = NOW() WHERE id = $3",
                AgentStatus.IDLE.value, result, uuid.UUID(agent_id)
            )
        
        # Update memory
        if agent_id in self._active_agents:
            self._active_agents[agent_id].current_task = None
            self._active_agents[agent_id].status = AgentStatus.IDLE
            self._active_agents[agent_id].results[task_id] = result
        
        return True
    
    async def send_message(self, agent_id: str, message: AgentMessage) -> bool:
        """Send a message to/from an agent"""
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO agent_messages (id, agent_id, user_id, message_id, sender_id, sender_type, recipient_id, role, content, attachments, metadata)
                VALUES ($1, $2, (SELECT user_id FROM agents WHERE id = $2), $3, $4, $5, $6, $7, $8, $9, $10)
            """,
                uuid.uuid4(),
                uuid.UUID(agent_id),
                message.message_id,
                message.sender_id,
                message.sender_type.value if message.sender_type else None,
                message.recipient_id,
                message.role.value,
                message.content,
                message.attachments,
                message.metadata
            )
        
        # Update memory
        if agent_id in self._active_agents:
            self._active_agents[agent_id].messages.append(message)
        
        return True
    
    async def get_messages(self, agent_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get messages for an agent"""
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM agent_messages WHERE agent_id = $1 ORDER BY created_at DESC LIMIT $2",
                uuid.UUID(agent_id), limit
            )
            return [dict(row) for row in rows]
    
    async def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent"""
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM agents WHERE id = $1", uuid.UUID(agent_id))
        
        # Remove from memory
        if agent_id in self._active_agents:
            del self._active_agents[agent_id]
        
        return True
    
    def get_active_agents(self) -> Dict[str, AgentState]:
        """Get all active agents from memory"""
        return self._active_agents


# Global agent manager
agent_manager = AgentManager()