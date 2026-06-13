"""
Multi-Agent Orchestrator
Coordinates multiple agents to accomplish complex goals
"""
import logging
import uuid
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from app.multi_agent.types import (
    AgentType, AgentStatus, CollaborationMode, 
    AgentTask, AgentMessage, MessageRole
)
from app.multi_agent.services.agent_registry import agent_registry
from app.multi_agent.services.agent_manager import agent_manager

logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    """Orchestrates multiple agents to accomplish complex goals"""
    
    def __init__(self):
        self._active_executions: Dict[str, Dict[str, Any]] = {}
    
    async def create_team(
        self,
        user_id: str,
        goal: str,
        agent_types: List[AgentType],
        collaboration_mode: CollaborationMode = CollaborationMode.SEQUENTIAL,
        max_parallel: int = 3,
        team_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a team of agents"""
        team_id = str(uuid.uuid4())
        team_name = team_name or f"Team for: {goal[:50]}"
        
        from app.database.connection import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO agent_teams (id, user_id, name, goal, collaboration_mode, max_agents_parallel, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                uuid.UUID(team_id),
                uuid.UUID(user_id),
                team_name,
                goal,
                collaboration_mode.value,
                max_parallel,
                AgentStatus.INITIALIZING.value
            )
        
        # Create agents
        agent_ids = []
        for agent_type in agent_types:
            result = await agent_manager.create_agent(
                user_id=user_id,
                agent_type=agent_type,
                team_id=team_id,
            )
            agent_ids.append(result["agent_id"])
        
        logger.info(f"Created team {team_id} with {len(agent_ids)} agents")
        return {
            "team_id": team_id,
            "name": team_name,
            "goal": goal,
            "agent_ids": agent_ids,
            "collaboration_mode": collaboration_mode.value,
        }
    
    async def execute_goal(
        self,
        user_id: str,
        goal: str,
        agent_types: Optional[List[AgentType]] = None,
        team_id: Optional[str] = None,
        collaboration_mode: CollaborationMode = CollaborationMode.SEQUENTIAL,
        stream_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """Execute a goal using multiple agents"""
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        start_time = datetime.utcnow()
        
        # Default agent types if not specified
        if not agent_types:
            agent_types = [AgentType.GENERALIST]
        
        # Create or use existing team
        if team_id:
            team_info = await self.get_team(team_id)
            if not team_info:
                raise ValueError(f"Team {team_id} not found")
            agent_ids = [a["id"] for a in await agent_manager.list_agents(user_id, team_id)]
        else:
            team_result = await self.create_team(
                user_id=user_id,
                goal=goal,
                agent_types=agent_types,
                collaboration_mode=collaboration_mode,
            )
            team_id = team_result["team_id"]
            agent_ids = team_result["agent_ids"]
        
        # Store execution
        from app.database.connection import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO multi_agent_executions (id, user_id, team_id, execution_id, goal, status, total_agents, active_agents, started_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
                uuid.uuid4(),
                uuid.UUID(user_id),
                uuid.UUID(team_id),
                execution_id,
                goal,
                "running",
                len(agent_ids),
                len(agent_ids),
                start_time
            )
        
        self._active_executions[execution_id] = {
            "execution_id": execution_id,
            "team_id": team_id,
            "goal": goal,
            "agent_ids": agent_ids,
            "status": "running",
            "started_at": start_time,
        }
        
        # Stream status
        if stream_callback:
            await stream_callback({
                "type": "execution_started",
                "execution_id": execution_id,
                "team_id": team_id,
                "goal": goal,
                "agents": len(agent_ids),
            })
        
        try:
            # Execute based on collaboration mode
            if collaboration_mode == CollaborationMode.SEQUENTIAL:
                results = await self._execute_sequential(user_id, goal, agent_ids, stream_callback)
            elif collaboration_mode == CollaborationMode.PARALLEL:
                results = await self._execute_parallel(user_id, goal, agent_ids, stream_callback)
            elif collaboration_mode == CollaborationMode.HIERARCHICAL:
                results = await self._execute_hierarchical(user_id, goal, agent_ids, stream_callback)
            else:
                results = await self._execute_sequential(user_id, goal, agent_ids, stream_callback)
            
            # Complete execution
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            async with pool.acquire() as conn:
                await conn.execute("""
                    UPDATE multi_agent_executions 
                    SET status = $1, completed_agents = $2, progress = 1.0, results = $3, completed_at = NOW(), duration_ms = $4
                    WHERE execution_id = $5
                """, "completed", len(agent_ids), results, duration_ms, execution_id)
                
                await conn.execute(
                    "UPDATE agent_teams SET status = $1, results = $2, completed_at = NOW() WHERE id = $3",
                    AgentStatus.COMPLETED.value, results, uuid.UUID(team_id)
                )
            
            if stream_callback:
                await stream_callback({
                    "type": "execution_completed",
                    "execution_id": execution_id,
                    "results": results,
                    "duration_ms": duration_ms,
                })
            
            return {
                "execution_id": execution_id,
                "team_id": team_id,
                "status": "completed",
                "results": results,
                "duration_ms": duration_ms,
            }
            
        except Exception as e:
            logger.error(f"Execution {execution_id} failed: {e}")
            async with pool.acquire() as conn:
                await conn.execute("""
                    UPDATE multi_agent_executions SET status = $1 WHERE execution_id = $2
                """, "failed", execution_id)
            
            if stream_callback:
                await stream_callback({
                    "type": "execution_failed",
                    "execution_id": execution_id,
                    "error": str(e),
                })
            
            raise
    
    async def _execute_sequential(
        self,
        user_id: str,
        goal: str,
        agent_ids: List[str],
        stream_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """Execute tasks sequentially with each agent"""
        results = {"steps": [], "final_output": ""}
        context = {"goal": goal, "previous_results": []}
        
        for i, agent_id in enumerate(agent_ids):
            if stream_callback:
                await stream_callback({
                    "type": "agent_started",
                    "agent_id": agent_id,
                    "step": i + 1,
                    "total_steps": len(agent_ids),
                })
            
            await agent_manager.update_agent_status(agent_id, AgentStatus.WORKING, progress=0.0)
            
            # Simulate agent work (in real implementation, call LLM)
            task = AgentTask(
                task_id=f"task_{uuid.uuid4().hex[:8]}",
                description=f"Agent {i+1} working on: {goal}",
                context=context,
                expected_output=f"Result from agent {i+1}",
            )
            await agent_manager.assign_task(agent_id, task)
            
            # Generate result
            result = {
                "agent_id": agent_id,
                "step": i + 1,
                "output": f"Output from agent {i+1} for: {goal[:50]}...",
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            await agent_manager.complete_task(agent_id, task.task_id, result)
            await agent_manager.update_agent_status(agent_id, AgentStatus.COMPLETED, progress=1.0)
            
            results["steps"].append(result)
            context["previous_results"].append(result)
            
            if stream_callback:
                await stream_callback({
                    "type": "agent_completed",
                    "agent_id": agent_id,
                    "step": i + 1,
                    "result": result,
                })
        
        results["final_output"] = f"Completed with {len(agent_ids)} agents"
        return results
    
    async def _execute_parallel(
        self,
        user_id: str,
        goal: str,
        agent_ids: List[str],
        stream_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """Execute tasks in parallel with all agents"""
        async def run_agent(agent_id: str, index: int):
            await agent_manager.update_agent_status(agent_id, AgentStatus.WORKING, progress=0.0)
            
            task = AgentTask(
                task_id=f"task_{uuid.uuid4().hex[:8]}",
                description=f"Agent {index+1} working on: {goal}",
                context={"goal": goal},
                expected_output=f"Result from agent {index+1}",
            )
            await agent_manager.assign_task(agent_id, task)
            
            result = {
                "agent_id": agent_id,
                "output": f"Parallel output from agent {index+1} for: {goal[:50]}...",
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            await agent_manager.complete_task(agent_id, task.task_id, result)
            await agent_manager.update_agent_status(agent_id, AgentStatus.COMPLETED, progress=1.0)
            
            if stream_callback:
                await stream_callback({
                    "type": "agent_completed",
                    "agent_id": agent_id,
                    "result": result,
                })
            
            return result
        
        # Run all agents in parallel
        tasks = [run_agent(agent_id, i) for i, agent_id in enumerate(agent_ids)]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        results = {
            "parallel_results": [r if not isinstance(r, Exception) else {"error": str(r)} for r in results_list],
            "final_output": f"Parallel execution with {len(agent_ids)} agents completed",
        }
        
        if stream_callback:
            await stream_callback({
                "type": "all_agents_completed",
                "results": results_list,
            })
        
        return results
    
    async def _execute_hierarchical(
        self,
        user_id: str,
        goal: str,
        agent_ids: List[str],
        stream_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """Execute with supervisor/worker hierarchy"""
        if len(agent_ids) < 2:
            return await self._execute_sequential(user_id, goal, agent_ids, stream_callback)
        
        supervisor_id = agent_ids[0]
        worker_ids = agent_ids[1:]
        
        if stream_callback:
            await stream_callback({
                "type": "supervisor_started",
                "supervisor_id": supervisor_id,
                "worker_count": len(worker_ids),
            })
        
        # Supervisor creates plan
        await agent_manager.update_agent_status(supervisor_id, AgentStatus.WORKING)
        
        task = AgentTask(
            task_id=f"task_{uuid.uuid4().hex[:8]}",
            description=f"Supervisor planning for: {goal}",
            context={"goal": goal, "workers": worker_ids},
            expected_output="Task assignments for workers",
        )
        await agent_manager.assign_task(supervisor_id, task)
        
        supervisor_result = {
            "agent_id": supervisor_id,
            "output": f"Supervisor planned tasks for {len(worker_ids)} workers",
            "task_assignments": [{"worker_id": wid, "task": f"Task for {wid}"} for wid in worker_ids],
        }
        
        await agent_manager.complete_task(supervisor_id, task.task_id, supervisor_result)
        await agent_manager.update_agent_status(supervisor_id, AgentStatus.COMPLETED)
        
        # Workers execute in parallel
        worker_results = await self._execute_parallel(user_id, goal, worker_ids, stream_callback)
        
        return {
            "supervisor_result": supervisor_result,
            "worker_results": worker_results,
            "final_output": f"Hierarchical execution with supervisor and {len(worker_ids)} workers completed",
        }
    
    async def get_team(self, team_id: str) -> Optional[Dict[str, Any]]:
        """Get team details"""
        from app.database.connection import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM agent_teams WHERE id = $1", uuid.UUID(team_id))
            if row:
                return dict(row)
            return None
    
    async def list_teams(self, user_id: str) -> List[Dict[str, Any]]:
        """List teams for a user"""
        from app.database.connection import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM agent_teams WHERE user_id = $1 ORDER BY created_at DESC",
                uuid.UUID(user_id)
            )
            return [dict(row) for row in rows]
    
    async def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution details"""
        from app.database.connection import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM multi_agent_executions WHERE execution_id = $1",
                execution_id
            )
            if row:
                return dict(row)
            return None
    
    async def list_executions(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """List executions for a user"""
        from app.database.connection import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM multi_agent_executions WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
                uuid.UUID(user_id), limit
            )
            return [dict(row) for row in rows]
    
    async def stop_execution(self, execution_id: str) -> bool:
        """Stop a running execution"""
        from app.database.connection import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE multi_agent_executions SET status = $1 WHERE execution_id = $2",
                "stopped", execution_id
            )
        
        if execution_id in self._active_executions:
            self._active_executions[execution_id]["status"] = "stopped"
        
        return True


# Global orchestrator instance
orchestrator = MultiAgentOrchestrator()