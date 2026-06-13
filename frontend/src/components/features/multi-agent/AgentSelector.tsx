/**
 * Agent Selector Component
 * Allows selection of agent types for multi-agent execution
 */

import React, { useState, useEffect } from "react";
import { Button } from "#/ui/button";
import { Badge } from "#/ui/badge";
import { AgentCard } from "./AgentCard";
import { multiAgentService, type AgentType } from "#/services/multi-agent-service";

interface AgentSelectorProps {
  selected: string[];
  onChange: (types: string[]) => void;
  maxAgents?: number;
}

export const AgentSelector: React.FC<AgentSelectorProps> = ({
  selected,
  onChange,
  maxAgents = 5,
}) => {
  const [agents, setAgents] = useState<AgentType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAgentTypes();
  }, []);

  const loadAgentTypes = async () => {
    try {
      setLoading(true);
      setError(null);
      const types = await multiAgentService.getAgentTypes();
      setAgents(types);
    } catch (err) {
      setError("Failed to load agent types");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = (type: string) => {
    if (selected.includes(type)) {
      onChange(selected.filter((t) => t !== type));
    } else if (selected.length < maxAgents) {
      onChange([...selected, type]);
    }
  };

  const handleSelectAll = () => {
    onChange(agents.map((a) => a.type));
  };

  const handleClearAll = () => {
    onChange([]);
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">Select Agents</h3>
          <Badge variant="secondary">Loading...</Badge>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-32 bg-muted animate-pulse rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">Select Agents</h3>
          <Button variant="outline" size="sm" onClick={loadAgentTypes}>
            Retry
          </Button>
        </div>
        <div className="text-center py-8 text-muted-foreground">{error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold">Select Agents</h3>
          <Badge variant="secondary">
            {selected.length}/{maxAgents}
          </Badge>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={handleSelectAll}>
            Select All
          </Button>
          <Button variant="ghost" size="sm" onClick={handleClearAll}>
            Clear
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[400px] overflow-y-auto p-1">
        {agents.map((agent) => (
          <AgentCard
            key={agent.type}
            agent={agent}
            selected={selected.includes(agent.type)}
            onToggle={handleToggle}
          />
        ))}
      </div>

      {selected.length === 0 && (
        <p className="text-sm text-muted-foreground text-center py-2">
          Select at least one agent to continue
        </p>
      )}
    </div>
  );
};