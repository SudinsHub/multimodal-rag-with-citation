import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { documentService } from "../services/documentService";
import { DocumentDetailsPayload } from "../types/document";

export function useDocuments() {
  const queryClient = useQueryClient();

  const documentsQuery = useQuery({
    queryKey: ["documents"],
    queryFn: documentService.listDocuments,
    // Poll every 3 seconds while documents are processing
    refetchInterval: (query) => {
      const data = query.state.data;
      const isProcessing = data?.some((d) => d.status === "processing" || d.status === "uploaded");
      return isProcessing ? 3000 : 15000;
    },
  });

  const uploadMutation = useMutation({
    mutationFn: (payload: DocumentDetailsPayload) => documentService.uploadDocument(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => documentService.deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  return {
    documents: documentsQuery.data || [],
    isLoading: documentsQuery.isLoading,
    isError: documentsQuery.isError,
    error: documentsQuery.error,
    uploadDocument: uploadMutation.mutateAsync,
    isUploading: uploadMutation.isPending,
    deleteDocument: deleteMutation.mutateAsync,
  };
}
