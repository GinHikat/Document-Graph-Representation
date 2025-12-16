import { create } from 'zustand';
import type { Document, UploadProgress } from '@/types';
import { documentService } from '@/services/api';

interface DocumentState {
  documents: Document[];
  selectedIds: string[];
  uploadProgress: UploadProgress | null;
  isLoading: boolean;
  loadDocuments: () => Promise<void>;
  uploadDocuments: (files: File[]) => Promise<void>;
  deleteDocuments: (ids: string[]) => Promise<void>;
  reprocessDocuments: (ids: string[]) => Promise<void>;
  toggleSelection: (id: string) => void;
  clearSelection: () => void;
  selectAll: () => void;
}

export const useDocumentStore = create<DocumentState>((set, get) => ({
  documents: [],
  selectedIds: [],
  uploadProgress: null,
  isLoading: false,

  loadDocuments: async () => {
    set({ isLoading: true });
    try {
      const documents = await documentService.list();
      set({ documents, isLoading: false });
    } catch (error) {
      console.error('Failed to load documents:', error);
      set({ isLoading: false });
    }
  },

  uploadDocuments: async (files: File[]) => {
    try {
      const { taskId } = await documentService.upload(files);
      
      // Simulate progress updates
      const interval = setInterval(async () => {
        const progress = await documentService.getProgress(taskId);
        set({ uploadProgress: progress });
        
        if (progress.progress >= 100) {
          clearInterval(interval);
          set({ uploadProgress: null });
          get().loadDocuments();
        }
      }, 1000);
    } catch (error) {
      console.error('Failed to upload documents:', error);
      throw error;
    }
  },

  deleteDocuments: async (ids: string[]) => {
    try {
      await documentService.delete(ids);
      const documents = get().documents.filter(doc => !ids.includes(doc.id));
      set({ documents, selectedIds: [] });
    } catch (error) {
      console.error('Failed to delete documents:', error);
      throw error;
    }
  },

  reprocessDocuments: async (ids: string[]) => {
    try {
      await documentService.reprocess(ids);
      get().loadDocuments();
    } catch (error) {
      console.error('Failed to reprocess documents:', error);
      throw error;
    }
  },

  toggleSelection: (id: string) => {
    const selectedIds = get().selectedIds;
    if (selectedIds.includes(id)) {
      set({ selectedIds: selectedIds.filter(sid => sid !== id) });
    } else {
      set({ selectedIds: [...selectedIds, id] });
    }
  },

  clearSelection: () => {
    set({ selectedIds: [] });
  },

  selectAll: () => {
    const allIds = get().documents.map(doc => doc.id);
    set({ selectedIds: allIds });
  },
}));
