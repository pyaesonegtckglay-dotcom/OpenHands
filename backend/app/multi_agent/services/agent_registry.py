"""
Agent Registry Service
Manages available agent types and their configurations
"""
import logging
from typing import Dict, List, Optional
from app.multi_agent.types import AgentType, AgentConfig

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry of available agent types and their default configurations"""
    
    def __init__(self):
        self._agents: Dict[AgentType, AgentConfig] = {}
        self._register_default_agents()
    
    def _register_default_agents(self):
        """Register default agent types"""
        default_agents = [
            AgentConfig(
                agent_type=AgentType.PLANNER,
                name="Planner Agent",
                description="Breaks down complex goals into actionable steps",
                capabilities=["planning", "goal_decomposition", "task_prioritization"],
                tools=["reasoning"],
                system_prompt="You are a Planner Agent. Your role is to break down complex goals into clear, actionable steps. Think systematically about dependencies and priorities."
            ),
            AgentConfig(
                agent_type=AgentType.RESEARCHER,
                name="Researcher Agent",
                description="Gathers and synthesizes information from various sources",
                capabilities=["web_search", "data_analysis", "information_synthesis"],
                tools=["web_search", "http_request"],
                system_prompt="You are a Researcher Agent. Your role is to gather accurate, comprehensive information. Always cite sources and verify facts."
            ),
            AgentConfig(
                agent_type=AgentType.CODER,
                name="Coder Agent",
                description="Writes, reviews, and refactors code",
                capabilities=["coding", "debugging", "code_review", "refactoring"],
                tools=["python_executor", "file_writer"],
                system_prompt="You are a Coder Agent. Write clean, efficient, well-documented code. Follow best practices and consider edge cases."
            ),
            AgentConfig(
                agent_type=AgentType.REVIEWER,
                name="Reviewer Agent",
                description="Reviews and provides feedback on work products",
                capabilities=["code_review", "quality_assurance", "feedback"],
                tools=["reasoning"],
                system_prompt="You are a Reviewer Agent. Provide constructive, detailed feedback. Be thorough but fair. Focus on improvement opportunities."
            ),
            AgentConfig(
                agent_type=AgentType.EXECUTOR,
                name="Executor Agent",
                description="Executes tasks and coordinates with tools",
                capabilities=["task_execution", "tool_use", "coordination"],
                tools=["python_executor", "file_writer", "calculator"],
                system_prompt="You are an Executor Agent. Execute tasks efficiently and report progress clearly. Use appropriate tools for each task."
            ),
            AgentConfig(
                agent_type=AgentType.SYNTHESIZER,
                name="Synthesizer Agent",
                description="Combines outputs from multiple agents into cohesive results",
                capabilities=["synthesis", "integration", "summarization"],
                tools=["reasoning"],
                system_prompt="You are a Synthesizer Agent. Combine information from multiple sources into clear, coherent outputs. Identify key insights and patterns."
            ),
            AgentConfig(
                agent_type=AgentType.COORDINATOR,
                name="Coordinator Agent",
                description="Orchestrates multiple agents to work together",
                capabilities=["coordination", "delegation", "monitoring", "communication"],
                tools=["reasoning"],
                system_prompt="You are a Coordinator Agent. Orchestrate multiple agents to achieve complex goals. Delegate tasks appropriately and monitor progress."
            ),
            AgentConfig(
                agent_type=AgentType.GENERALIST,
                name="Generalist Agent",
                description="Handles diverse tasks with broad capabilities",
                capabilities=["general_purpose", "adaptability", "problem_solving"],
                tools=["reasoning", "web_search", "python_executor"],
                system_prompt="You are a Generalist Agent. Handle diverse tasks flexibly. Adapt your approach based on the specific requirements of each task."
            ),
        ]
        
        for agent in default_agents:
            self.register(agent)
        
        logger.info(f"Registered {len(default_agents)} default agent types")
    
    def register(self, config: AgentConfig):
        """Register an agent configuration"""
        self._agents[config.agent_type] = config
        logger.info(f"Registered agent: {config.agent_type.value}")
    
    def get(self, agent_type: AgentType) -> Optional[AgentConfig]:
        """Get agent configuration by type"""
        return self._agents.get(agent_type)
    
    def list_all(self) -> List[AgentConfig]:
        """List all registered agents"""
        return list(self._agents.values())
    
    def list_enabled(self) -> List[AgentConfig]:
        """List all enabled agents"""
        return list(self._agents.values())
    
    def get_by_type(self, agent_type: str) -> Optional[AgentConfig]:
        """Get agent by type string"""
        try:
            return self._agents.get(AgentType(agent_type))
        except ValueError:
            return None


# Global registry instance
agent_registry = AgentRegistry()