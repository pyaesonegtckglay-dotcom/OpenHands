import { useParams } from "react-router";

export function useConversationId() {
  const { conversationId } = useParams<{ conversationId: string }>();

  if (!conversationId) {
    throw new Error(
      "useConversationId must be used within a route that has a conversationId parameter",
    );
  }

  return { conversationId };
}

/**
 * Safe version of useConversationId that returns null instead of throwing
 * Use this hook in pages that may or may not have a conversationId
 */
export function useSafeConversationId(): { conversationId: string | null } {
  const { conversationId } = useParams<{ conversationId: string }>();
  return { conversationId: conversationId || null };
}
