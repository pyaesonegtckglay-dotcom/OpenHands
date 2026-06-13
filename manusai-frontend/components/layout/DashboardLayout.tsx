"use client";
import AppShell from "./AppShell";

/**
 * DashboardLayout — thin wrapper around AppShell.
 * Preserved for backward compatibility with existing page imports.
 */
export default function DashboardLayout({
  children,
  title,
}: {
  children: React.ReactNode;
  title?: string;
}) {
  return <AppShell title={title}>{children}</AppShell>;
}
