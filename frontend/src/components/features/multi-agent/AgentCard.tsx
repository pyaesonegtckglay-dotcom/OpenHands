/**
 * Agent Card Component
 * Displays agent type information with selection capability
 */

import React from "react";
import { Card } from "#/ui/card";
import { Badge } from "#/ui/badge";
import { Checkbox } from "#/ui/checkbox";
import type { AgentType } from "#/services/multi-agent-service";

interface AgentCardProps {
  agent: AgentType;
  selected: boolean;
  onToggle: (type: string) => void;
}

const agentIcons: Record<string, string> = {
  planner: "📋",
  researcher: "🔍",
  coder: "💻",
  reviewer: "🔎",
  executor: "⚡",
  synthesizer: "🔮",
  coordinator: "🎯",
  generalist: "🧠",
};

export const AgentCard: React.FC<AgentCardProps> = ({ agent, selected, onToggle }) => {
  return (
    <Card
      className={`cursor-pointer transition-all duration-200 p-4 ${
        selected
          ? "ring-2 ring-primary bg-primary/5"
          : "hover:border-primary/50 hover:shadow-md"
      }`}
      onClick={() => onToggle(agent.type)}
    >
      <div className="flex items-start gap-3">
        <Checkbox
          checked={selected}
          onCheckedChange={() => onToggle(agent.type)}
          className="mt-1"
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xl">{agentIcons[agent.type] || "🤖"}</span>
            <h3 className="font-semibold text-sm">{agent.name}</h3>
          </div>
          <p className="text-xs text-muted-foreground mb-2 line-clamp-2">
            {agent.description}
          </p>
          <div className="flex flex-wrap gap-1">
            {agent.capabilities.slice(0, 3).map((cap) => (
              <Badge key={cap} variant="secondary" className="text-xs px-1.5 py-0.5">
                {cap}
              </Badge>
            ))}
            {agent.capabilities.length > 3 && (
              <Badge variant="outline" className="text-xs px-1.5 py-0.5">
                +{agent.capabilities.length - 3}
              </Badge>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
};