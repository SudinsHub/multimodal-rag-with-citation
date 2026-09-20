import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { chatService } from "../services/chatService";

export function useChat(activeSessionId: string | null) {
  const queryClient = useQueryClient();

  const sessionsQuery = useQuery({
    queryKey: ["chat-sessions"],
    queryFn: chatService.listSessions,
  });

  const messagesQuery = useQuery({
    queryKey: ["chat-messages", activeSessionId],
    queryFn: () => (activeSessionId ? chatService.getMessages(activeSessionId) : Promise.resolve([])),
    enabled: Boolean(activeSessionId),
  });

  const createSessionMutation = useMutation({
    mutationFn: ({ title, documentId }: { title?: string; documentId?: string }) =>
      chatService.createSession(title, documentId),
    onSuccess: (newSession) => {
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
      return newSession;
    },
  });

  const deleteSessionMutation = useMutation({
    mutationFn: (sessionId: string) => chatService.deleteSession(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
    },
  });

  const sendMessageMutation = useMutation({
    mutationFn: ({
      sessionId,
      message,
      documentId,
    }: {
      sessionId: string;
      message: string;
      documentId?: string;
    }) => chatService.sendMessage(sessionId, message, documentId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["chat-messages", variables.sessionId] });
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
    },
  });

  return {
    sessions: sessionsQuery.data || [],
    isLoadingSessions: sessionsQuery.isLoading,
    messages: messagesQuery.data || [],
    isLoadingMessages: messagesQuery.isLoading,
    createSession: createSessionMutation.mutateAsync,
    isCreatingSession: createSessionMutation.isPending,
    deleteSession: deleteSessionMutation.mutateAsync,
    sendMessage: sendMessageMutation.mutateAsync,
    isSending: sendMessageMutation.isPending,
  };
}
