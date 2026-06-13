"""
Multi-Agent Orchestration API Endpoints
"""
import logging
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
import asyncio
import json

from app.core.security import get_current_user
from app.multi_agent.types import AgentType, CollaborationMode
from app.multi_agent.orchestrator.multi_agent_orchestrator import orchestrator
from app.multi_agent.services.agent_manager import agent_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/multi-agent", tags=["multi-agent"])


@router.post("/teams/create")
async def create_team(
    goal: str,
    agent_types: str,  # Comma-separated list
    collaboration_mode: str = "sequential",
    max_parallel: int = 3,
    team_name: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Create a team of agents"""
    try:
        # Parse comma-separated agent types
        agent_type_list = [at.strip() for at in agent_types.split(",")]
        agent_type_enums = [AgentType(at) for at in agent_type_list]
        collaboration = CollaborationMode(collaboration_mode)
        user_uuid = uuid.UUID(current_user["id"])
        
        result = await orchestrator.create_team(
            user_uuid=user_uuid,
            goal=goal,
            agent_types=agent_type_enums,
            collaboration_mode=collaboration,
            max_parallel=max_parallel,
            team_name=team_name,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Create team error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/teams")
async def list_teams(current_user: dict = Depends(get_current_user)):
    """List all teams for current user"""
    try:
        user_uuid = uuid.UUID(current_user["id"])
        teams = await orchestrator.list_teams(user_uuid)
        return {"teams": teams, "count": len(teams)}
    except Exception as e:
        logger.error(f"List teams error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/teams/{team_id}")
async def get_team(team_id: str, current_user: dict = Depends(get_current_user)):
    """Get team details"""
    try:
        user_uuid = uuid.UUID(current_user["id"])
        team_uuid = uuid.UUID(team_id)
        team = await orchestrator.get_team(team_uuid)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        # Get agents in team
        agents = await agent_manager.list_agents(user_uuid, team_uuid)
        
        return {"team": team, "agents": agents}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get team error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/teams/{team_id}")
async def delete_team(team_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a team"""
    try:
        from app.database.connection import get_pool
        import uuid
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Delete agents first
            await conn.execute("DELETE FROM agents WHERE team_id = $1", uuid.UUID(team_id))
            await conn.execute("DELETE FROM agent_teams WHERE id = $1", uuid.UUID(team_id))
        return {"status": "deleted", "team_id": team_id}
    except Exception as e:
        logger.error(f"Delete team error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents")
async def list_agents(
    team_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """List agents for current user"""
    try:
        user_uuid = uuid.UUID(current_user["id"])
        team_uuid = uuid.UUID(team_id) if team_id else None
        agents = await agent_manager.list_agents(user_uuid, team_uuid)
        return {"agents": agents, "count": len(agents)}
    except Exception as e:
        logger.error(f"List agents error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str, current_user: dict = Depends(get_current_user)):
    """Get agent details"""
    try:
        agent = await agent_manager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get agent error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}/messages")
async def get_agent_messages(
    agent_id: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    """Get messages for an agent"""
    try:
        messages = await agent_manager.get_messages(agent_id, limit)
        return {"messages": messages, "count": len(messages)}
    except Exception as e:
        logger.error(f"Get messages error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute")
async def execute_multi_agent(
    goal: str,
    agent_types: Optional[str] = None,  # Comma-separated list
    team_id: Optional[str] = None,
    collaboration_mode: str = "sequential",
    current_user: dict = Depends(get_current_user),
):
    """Execute a goal using multiple agents"""
    try:
        logger.info(f"Execute request - user: {current_user}, goal: {goal}, agent_types: {agent_types}")
        agent_type_enums = None
        if agent_types:
            agent_type_list = [at.strip() for at in agent_types.split(",")]
            agent_type_enums = [AgentType(at) for at in agent_type_list]
        collaboration = CollaborationMode(collaboration_mode)
        user_uuid = uuid.UUID(current_user["id"])
        logger.info(f"Executing with user_uuid: {user_uuid}")
        
        result = await orchestrator.execute_goal(
            user_uuid=user_uuid,
            goal=goal,
            agent_types=agent_type_enums,
            team_id=team_id,
            collaboration_mode=collaboration,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        logger.error(f"Execute error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute/stream")
async def execute_multi_agent_stream(
    goal: str,
    agent_types: Optional[str] = None,  # Comma-separated list
    team_id: Optional[str] = None,
    collaboration_mode: str = "sequential",
    current_user: dict = Depends(get_current_user),
):
    """Execute a goal using multiple agents with streaming response"""
    async def event_generator():
        agent_type_enums = None
        if agent_types:
            agent_type_list = [at.strip() for at in agent_types.split(",")]
            agent_type_enums = [AgentType(at) for at in agent_type_list]
        collaboration = CollaborationMode(collaboration_mode)
        user_uuid = uuid.UUID(current_user["id"])
        
        async def stream_callback(event):
            yield f"data: {json.dumps(event)}\n\n"
        
        try:
            result = await orchestrator.execute_goal(
                user_uuid=user_uuid,
                goal=goal,
                agent_types=agent_type_enums,
                team_id=team_id,
                collaboration_mode=collaboration,
                stream_callback=stream_callback,
            )
            yield f"data: {json.dumps({'type': 'done', 'result': result})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/executions")
async def list_executions(
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """List multi-agent executions"""
    try:
        user_uuid = uuid.UUID(current_user["id"])
        executions = await orchestrator.list_executions(user_uuid, limit)
        return {"executions": executions, "count": len(executions)}
    except Exception as e:
        logger.error(f"List executions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str, current_user: dict = Depends(get_current_user)):
    """Get execution details"""
    try:
        execution = await orchestrator.get_execution(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        return execution
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/executions/{execution_id}/stop")
async def stop_execution(execution_id: str, current_user: dict = Depends(get_current_user)):
    """Stop a running execution"""
    try:
        success = await orchestrator.stop_execution(execution_id)
        return {"status": "stopped" if success else "failed", "execution_id": execution_id}
    except Exception as e:
        logger.error(f"Stop execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types")
async def list_agent_types():
    """List available agent types"""
    from app.multi_agent.services.agent_registry import agent_registry
    agents = agent_registry.list_all()
    return {
        "agent_types": [
            {
                "type": a.agent_type.value,
                "name": a.name,
                "description": a.description,
                "capabilities": a.capabilities,
                "tools": a.tools,
            }
            for a in agents
        ]
    }


@router.get("/modes")
async def list_collaboration_modes():
    """List available collaboration modes"""
    return {
        "modes": [
            {"mode": "sequential", "description": "Agents work one after another"},
            {"mode": "parallel", "description": "All agents work simultaneously"},
            {"mode": "hierarchical", "description": "Supervisor coordinates workers"},
        ]
    }