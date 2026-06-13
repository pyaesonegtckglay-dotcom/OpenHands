/**
 * Team Panel Component
 * Displays list of agent teams with status
 */

import React, { useState, useEffect } from "react";
import { Card,  } from "#/ui/card";
import { Button } from "#/ui/button";
import { Badge } from "#/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "#/ui/tabs";
import { multiAgentService, type Team } from "#/services/multi-agent-service";

interface TeamPanelProps {
  onSelectTeam?: (team: Team) => void;
  selectedTeamId?: string;
}

const statusColors: Record<string, string> = {
  initializing: "bg-yellow-500",
  running: "bg-blue-500",
  completed: "bg-green-500",
  failed: "bg-red-500",
};

const collaborationModeLabels: Record<string, string> = {
  sequential: "Sequential",
  parallel: "Parallel",
  hierarchical: "Hierarchical",
};

export const TeamPanel: React.FC<TeamPanelProps> = ({ onSelectTeam, selectedTeamId }) => {
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>("all");

  useEffect(() => {
    loadTeams();
  }, []);

  const loadTeams = async () => {
    try {
      setLoading(true);
      setError(null);
      const teamList = await multiAgentService.listTeams();
      setTeams(teamList);
    } catch (err) {
      setError("Failed to load teams");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const filteredTeams = teams.filter((team) => {
    if (activeTab === "all") return true;
    if (activeTab === "active") return team.status !== "completed" && team.status !== "failed";
    return team.status === activeTab;
  });

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      initializing: "bg-yellow-100 text-yellow-800",
      running: "bg-blue-100 text-blue-800",
      completed: "bg-green-100 text-green-800",
      failed: "bg-red-100 text-red-800",
    };
    return (
      <Badge className={colors[status] || "bg-gray-100"}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </Badge>
    );
  };

  if (loading) {
    return (
      <Card>
        <div className="pb-3">
          <div className="h-6 w-24 bg-muted animate-pulse rounded" />
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 bg-muted animate-pulse rounded-lg" />
          ))}
        </div>
      </Card>
    );
  }

  return (
    <Card className="h-full flex flex-col">
      <div className="pb-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-lg">Agent Teams</h2>
          <Button variant="outline" size="sm" onClick={loadTeams}>
            Refresh
          </Button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="w-full grid grid-cols-3">
            <TabsTrigger value="all">All ({teams.length})</TabsTrigger>
            <TabsTrigger value="active">
              Active ({teams.filter((t) => t.status !== "completed" && t.status !== "failed").length})
            </TabsTrigger>
            <TabsTrigger value="completed">
              Done ({teams.filter((t) => t.status === "completed").length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value={activeTab} className="mt-4 space-y-3 max-h-[500px] overflow-y-auto">
            {error && (
              <div className="text-center py-4 text-muted-foreground">
                <p>{error}</p>
                <Button variant="link" onClick={loadTeams}>
                  Try again
                </Button>
              </div>
            )}

            {!error && filteredTeams.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                <p>No teams found</p>
                <p className="text-sm mt-1">Create a new team to get started</p>
              </div>
            )}

            {filteredTeams.map((team) => (
              <Card
                key={team.id}
                className={`cursor-pointer transition-all p-3 ${
                  selectedTeamId === team.id ? "ring-2 ring-primary" : "hover:bg-muted/50"
                }`}
                onClick={() => onSelectTeam?.(team)}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={`w-2 h-2 rounded-full ${
                          statusColors[team.status] || "bg-gray-500"
                        }`}
                      />
                      <h3 className="font-medium text-sm truncate">{team.name}</h3>
                    </div>
                    <p className="text-xs text-muted-foreground truncate mb-2">{team.goal}</p>
                    <div className="flex items-center gap-2 flex-wrap">
                      {getStatusBadge(team.status)}
                      <Badge variant="outline" className="text-xs">
                        {collaborationModeLabels[team.collaboration_mode] || team.collaboration_mode}
                      </Badge>
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground text-right">
                    {new Date(team.created_at).toLocaleDateString()}
                  </div>
                </div>
              </Card>
            ))}
          </TabsContent>
        </Tabs>
      </div>
    </Card>
  );
};