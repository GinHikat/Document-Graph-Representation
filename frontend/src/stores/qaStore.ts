import { create } from 'zustand';
import type { CompareResponse } from '@/types';
import { qaService, type SSEEvent } from '@/services/api';

interface StreamingState {
  isStreaming: boolean;
  currentTool: string | null;
  streamedText: string;
  retrievedChunks: number;
  sources: Array<{ id: string; text: string; score: number }>;
}

interface QAState {
  currentQuestion: string;
  results: CompareResponse | null;
  history: CompareResponse[];
  isLoading: boolean;
  error: string | null;
  streaming: StreamingState;
  setCurrentQuestion: (question: string) => void;
  compare: (question: string) => Promise<void>;
  compareStreaming: (question: string) => Promise<void>;
  loadHistory: () => Promise<void>;
  submitAnnotation: (questionId: string, preference: string, comment?: string) => Promise<void>;
  resetStreaming: () => void;
}

const initialStreamingState: StreamingState = {
  isStreaming: false,
  currentTool: null,
  streamedText: '',
  retrievedChunks: 0,
  sources: [],
};

export const useQAStore = create<QAState>((set, get) => ({
  currentQuestion: '',
  results: null,
  history: [],
  isLoading: false,
  error: null,
  streaming: { ...initialStreamingState },

  setCurrentQuestion: (question: string) => {
    set({ currentQuestion: question });
  },

  resetStreaming: () => {
    set({ streaming: { ...initialStreamingState } });
  },

  compare: async (question: string) => {
    set({ isLoading: true, error: null, currentQuestion: question });
    try {
      const results = await qaService.compare(question);
      set({ results, isLoading: false });

      // Add to history
      const history = get().history;
      set({ history: [results, ...history] });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Có lỗi xảy ra',
        isLoading: false
      });
    }
  },

  compareStreaming: async (question: string) => {
    set({
      isLoading: true,
      error: null,
      currentQuestion: question,
      streaming: {
        ...initialStreamingState,
        isStreaming: true,
      },
      results: null,
    });

    try {
      await qaService.compareStreaming(question, (event: SSEEvent) => {
        const currentState = get();

        switch (event.type) {
          case 'tool_start':
            set({
              streaming: {
                ...currentState.streaming,
                currentTool: event.tool || null,
              },
            });
            break;

          case 'tool_end':
            set({
              streaming: {
                ...currentState.streaming,
                currentTool: null,
                retrievedChunks: event.chunks || currentState.streaming.retrievedChunks,
              },
            });
            break;

          case 'text':
            set({
              streaming: {
                ...currentState.streaming,
                streamedText: currentState.streaming.streamedText + (event.delta || ''),
              },
            });
            break;

          case 'sources':
            set({
              streaming: {
                ...currentState.streaming,
                sources: event.sources || [],
              },
            });
            break;

          case 'done': {
            const finalText = get().streaming.streamedText;
            const finalSources = get().streaming.sources;

            // Create results from streamed data
            const results: CompareResponse = {
              questionId: `q_${Date.now()}`,
              question,
              vector: {
                answer: finalText,
                sources: finalSources.map(s => ({
                  text: s.text,
                  score: s.score,
                  documentId: s.id,
                  documentName: 'Source Document',
                })),
                metrics: {
                  latencyMs: 0,
                  chunksUsed: get().streaming.retrievedChunks,
                },
              },
              graph: {
                answer: finalText,
                sources: [],
                cypherQuery: null,
                graphContext: [],
                metrics: {
                  latencyMs: 0,
                  chunksUsed: 0,
                  graphNodesUsed: 0,
                  graphHops: 0,
                },
              },
              timestamp: new Date().toISOString(),
            };

            set({
              results,
              streaming: {
                ...get().streaming,
                isStreaming: false,
              },
              isLoading: false,
            });

            // Add to history
            const history = get().history;
            set({ history: [results, ...history] });
            break;
          }

          case 'error':
            set({
              error: event.error || 'Streaming error',
              streaming: {
                ...get().streaming,
                isStreaming: false,
              },
              isLoading: false,
            });
            break;
        }
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Có lỗi xảy ra',
        isLoading: false,
        streaming: {
          ...get().streaming,
          isStreaming: false,
        },
      });
    }
  },

  loadHistory: async () => {
    try {
      const history = await qaService.getHistory();
      set({ history });
    } catch (error) {
      console.error('Failed to load history:', error);
    }
  },

  submitAnnotation: async (questionId: string, preference: string, comment?: string) => {
    try {
      await qaService.submitAnnotation(questionId, preference, comment);

      // Update history with annotation
      const history = get().history.map(item =>
        item.questionId === questionId
          ? {
              ...item,
              annotation: {
                userId: 'current_user',
                preference: preference as 'vector' | 'equivalent' | 'graph' | 'both_wrong',
                comment,
                timestamp: new Date().toISOString(),
              }
            }
          : item
      );
      set({ history });
    } catch (error) {
      console.error('Failed to submit annotation:', error);
      throw error;
    }
  },
}));
