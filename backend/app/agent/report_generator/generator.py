"""
Report Generator — Phase 3
Generates comprehensive final execution reports.
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExecutionReport:
    """Complete execution report."""
    execution_id: str
    goal: str
    objective: str
    actions_performed: list[dict]
    findings: list[str]
    generated_outputs: list[dict]
    errors_encountered: list[dict]
    execution_statistics: dict
    final_result: str
    report_markdown: str
    created_at: float = field(default_factory=time.time)
    partial: bool = False

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "goal": self.goal,
            "objective": self.objective,
            "actions_performed": self.actions_performed,
            "findings": self.findings,
            "generated_outputs": self.generated_outputs,
            "errors_encountered": self.errors_encountered,
            "execution_statistics": self.execution_statistics,
            "final_result": self.final_result,
            "report_markdown": self.report_markdown,
            "created_at": self.created_at,
            "partial": self.partial,
        }


class ReportGenerator:
    """
    Generates structured execution reports from completed task results.

    Report sections:
    1. Objective
    2. Actions Performed
    3. Findings
    4. Generated Outputs
    5. Errors Encountered
    6. Execution Statistics
    7. Final Result
    """

    def generate(
        self,
        execution_id: str,
        goal: str,
        tasks: dict,  # task_id → ScheduledTask
        events: list,  # list[ActivityEvent]
        partial: bool = False,
    ) -> ExecutionReport:
        """Generate a complete execution report."""
        from app.agent.execution_scheduler import TaskState

        all_tasks = list(tasks.values())
        completed_tasks = [t for t in all_tasks if t.state == TaskState.COMPLETED]
        failed_tasks = [t for t in all_tasks if t.state == TaskState.FAILED]
        cancelled_tasks = [t for t in all_tasks if t.state == TaskState.CANCELLED]

        # --- Actions Performed ---
        actions = []
        for task in all_tasks:
            action = {
                "task": task.title,
                "tool": task.tool_id,
                "status": task.state.value,
                "duration_ms": task.execution_time_ms,
                "retries": task.retries,
            }
            actions.append(action)

        # --- Findings ---
        findings = self._extract_findings(completed_tasks)

        # --- Generated Outputs ---
        outputs = self._extract_outputs(completed_tasks)

        # --- Errors ---
        errors = []
        for task in failed_tasks:
            errors.append({
                "task": task.title,
                "error": task.error or "Unknown error",
                "tool": task.tool_id,
            })

        # --- Execution Statistics ---
        total_time = sum(t.execution_time_ms for t in all_tasks)
        stats = {
            "total_tasks": len(all_tasks),
            "completed": len(completed_tasks),
            "failed": len(failed_tasks),
            "cancelled": len(cancelled_tasks),
            "success_rate": (
                round(len(completed_tasks) / len(all_tasks) * 100, 1)
                if all_tasks else 0
            ),
            "total_execution_time_ms": total_time,
            "total_execution_time_s": round(total_time / 1000, 1),
            "total_retries": sum(t.retries for t in all_tasks),
            "tools_used": list({t.tool_id for t in completed_tasks}),
            "partial": partial,
        }

        # --- Final Result Summary ---
        final_result = self._generate_final_result(
            goal, completed_tasks, failed_tasks, findings, outputs, partial
        )

        # --- Markdown Report ---
        report_md = self._build_markdown_report(
            goal=goal,
            execution_id=execution_id,
            actions=actions,
            findings=findings,
            outputs=outputs,
            errors=errors,
            stats=stats,
            final_result=final_result,
            partial=partial,
        )

        return ExecutionReport(
            execution_id=execution_id,
            goal=goal,
            objective=goal,
            actions_performed=actions,
            findings=findings,
            generated_outputs=outputs,
            errors_encountered=errors,
            execution_statistics=stats,
            final_result=final_result,
            report_markdown=report_md,
            partial=partial,
        )

    def _extract_findings(self, completed_tasks: list) -> list[str]:
        """Extract key findings from completed task results."""
        findings = []
        for task in completed_tasks:
            if not task.result:
                continue
            result = task.result
            if isinstance(result, dict):
                # Web search results
                if result.get("results"):
                    for r in result["results"][:3]:
                        snippet = r.get("snippet", "")[:200]
                        if snippet:
                            findings.append(f"**{task.title}**: {snippet}")
                # AI synthesis result
                elif result.get("result"):
                    text = str(result["result"])
                    # Extract first meaningful paragraph
                    lines = [l.strip() for l in text.split("\n") if l.strip() and not l.startswith("#")]
                    if lines:
                        findings.append(f"**{task.title}**: {lines[0][:300]}")
                # Calculator result
                elif "result" in result and result.get("success"):
                    findings.append(f"**{task.title}**: Result = {result['result']}")
                # HTTP response
                elif result.get("response_preview"):
                    findings.append(f"**{task.title}**: HTTP {result.get('status_code', 'N/A')} — {result['response_preview'][:200]}")
        return findings[:10]  # Cap at 10 findings

    def _extract_outputs(self, completed_tasks: list) -> list[dict]:
        """Extract generated file outputs."""
        outputs = []
        for task in completed_tasks:
            if not task.result:
                continue
            result = task.result
            if isinstance(result, dict):
                # File writer output
                if result.get("filename") and result.get("success"):
                    outputs.append({
                        "type": "file",
                        "filename": result["filename"],
                        "size_bytes": result.get("size_bytes", 0),
                        "task": task.title,
                    })
                # Python executor with file creation
                elif result.get("output") and "WORKSPACE" in str(result.get("output", "")):
                    outputs.append({
                        "type": "code_output",
                        "content": str(result["output"])[:500],
                        "task": task.title,
                    })
        return outputs

    def _generate_final_result(
        self,
        goal: str,
        completed: list,
        failed: list,
        findings: list[str],
        outputs: list[dict],
        partial: bool,
    ) -> str:
        """Generate a concise final result summary."""
        if not completed and not failed:
            return f"Execution completed for goal: {goal}. No tasks were executed."

        status = "partially" if partial else "successfully" if not failed else "with some failures"

        result_parts = [f"Goal '{goal}' executed {status}."]

        if completed:
            result_parts.append(f"{len(completed)} task(s) completed.")
        if failed:
            result_parts.append(f"{len(failed)} task(s) failed.")
        if findings:
            result_parts.append(f"\nKey findings:\n" + "\n".join(f"• {f}" for f in findings[:5]))
        if outputs:
            files = [o["filename"] for o in outputs if o.get("filename")]
            if files:
                result_parts.append(f"\nGenerated files: {', '.join(files)}")

        return " ".join(result_parts)

    def _build_markdown_report(
        self,
        goal: str,
        execution_id: str,
        actions: list[dict],
        findings: list[str],
        outputs: list[dict],
        errors: list[dict],
        stats: dict,
        final_result: str,
        partial: bool,
    ) -> str:
        """Build the full markdown report."""
        from datetime import datetime

        header = "⚠️ PARTIAL REPORT" if partial else "✅ EXECUTION COMPLETE"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        md = [
            f"# {header}",
            f"",
            f"**Execution ID:** `{execution_id}`  ",
            f"**Generated:** {timestamp}  ",
            f"**Goal:** {goal}",
            f"",
            f"---",
            f"",
            f"## 🎯 Objective",
            f"",
            f"{goal}",
            f"",
            f"---",
            f"",
            f"## ⚡ Actions Performed",
            f"",
        ]

        for i, action in enumerate(actions, 1):
            status_emoji = {"COMPLETED": "✅", "FAILED": "❌", "CANCELLED": "🚫", "RUNNING": "🔄"}.get(action["status"], "⏳")
            md.append(f"{i}. {status_emoji} **{action['task']}**")
            md.append(f"   - Tool: `{action['tool']}`")
            md.append(f"   - Status: {action['status']}")
            if action.get("duration_ms"):
                md.append(f"   - Duration: {action['duration_ms']}ms")
            if action.get("retries"):
                md.append(f"   - Retries: {action['retries']}")
            md.append("")

        md.extend([
            f"---",
            f"",
            f"## 🔍 Findings",
            f"",
        ])

        if findings:
            for finding in findings:
                md.append(f"- {finding}")
        else:
            md.append("No specific findings extracted.")

        md.extend([
            f"",
            f"---",
            f"",
            f"## 📁 Generated Outputs",
            f"",
        ])

        if outputs:
            for out in outputs:
                if out.get("type") == "file":
                    md.append(f"- 📄 **{out['filename']}** ({out.get('size_bytes', 0)} bytes) — {out.get('task', '')}")
                else:
                    md.append(f"- 💻 Code output from: **{out.get('task', 'Unknown')}**")
        else:
            md.append("No files generated.")

        md.extend([
            f"",
            f"---",
            f"",
            f"## ⚠️ Errors",
            f"",
        ])

        if errors:
            for err in errors:
                md.append(f"- ❌ **{err['task']}** (`{err['tool']}`): {err['error'][:200]}")
        else:
            md.append("No errors encountered.")

        md.extend([
            f"",
            f"---",
            f"",
            f"## 📊 Execution Statistics",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Tasks | {stats['total_tasks']} |",
            f"| Completed | {stats['completed']} |",
            f"| Failed | {stats['failed']} |",
            f"| Cancelled | {stats['cancelled']} |",
            f"| Success Rate | {stats['success_rate']}% |",
            f"| Total Time | {stats['total_execution_time_s']}s |",
            f"| Total Retries | {stats['total_retries']} |",
            f"| Tools Used | {', '.join(stats['tools_used']) if stats['tools_used'] else 'None'} |",
            f"",
            f"---",
            f"",
            f"## 🏁 Final Result",
            f"",
            f"{final_result}",
            f"",
        ])

        return "\n".join(md)
