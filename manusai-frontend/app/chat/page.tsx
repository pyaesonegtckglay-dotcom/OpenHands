"use client";
import DashboardLayout from "@/components/layout/DashboardLayout";
import ChatWindow from "@/components/chat/ChatWindow";

export default function ChatPage() {
  return (
    <DashboardLayout title="Chat">
      <div className="h-full flex flex-col">
        <ChatWindow />
      </div>
    </DashboardLayout>
  );
}
