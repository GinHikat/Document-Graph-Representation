import type {
  Document,
  CompareResponse,
  QAResult,
  GraphQAResult,
  AnnotationTask,
  AnnotationRating,
  AnnotatorStats,
  User,
  UploadProgress,
  GraphData,
} from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// SSE Event types for RAG streaming
export interface SSEEvent {
  type: 'tool_start' | 'tool_end' | 'text' | 'sources' | 'done' | 'error';
  tool?: string;
  delta?: string;
  chunks?: number;
  sources?: Array<{ id: string; text: string; score: number }>;
  error?: string;
}

// Error handling wrapper
async function fetchWithErrorHandling(url: string, options?: RequestInit): Promise<Response> {
  try {
    const response = await fetch(url, options);

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || error.message || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response;
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error('Network error: Unable to connect to backend. Is the server running?');
    }
    throw error;
  }
}



// Document Service - Real Implementation
export const documentService = {
  list: async (): Promise<Document[]> => {
    const response = await fetchWithErrorHandling(`${API_BASE_URL}/api/documents`);
    return await response.json();
  },

  upload: async (files: File[]): Promise<{ taskId: string; documents: Document[] }> => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    const response = await fetchWithErrorHandling(`${API_BASE_URL}/api/documents/upload`, {
      method: 'POST',
      body: formData,
    });
    return await response.json();
  },

  getProgress: async (taskId: string): Promise<UploadProgress> => {
    // Note: Backend doesn't have progress endpoint yet, return basic status
    return {
      taskId,
      progress: 100,
      step: 'Hoàn tất',
      estimatedTimeMs: 0,
    };
  },

  delete: async (ids: string[]): Promise<void> => {
    await fetchWithErrorHandling(`${API_BASE_URL}/api/documents/batch-delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(ids),
    });
  },

  reprocess: async (ids: string[]): Promise<void> => {
    for (const id of ids) {
      await fetchWithErrorHandling(`${API_BASE_URL}/api/documents/${id}/reprocess`, {
        method: 'POST',
      });
    }
  },
};

// QA Service - Real Implementation with Streaming
export const qaService = {
  // Streaming RAG query
  compareStreaming: async (
    question: string,
    onChunk: (event: SSEEvent) => void
  ): Promise<void> => {
    const response = await fetchWithErrorHandling(`${API_BASE_URL}/api/rag/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, stream: true }),
    });

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) throw new Error('No response body');

    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            onChunk(data);
          } catch (e) {
            console.warn('Failed to parse SSE event:', line);
          }
        }
      }
    }
  },

  // Non-streaming compare - real API only
  compare: async (question: string): Promise<CompareResponse> => {
    const response = await fetchWithErrorHandling(`${API_BASE_URL}/api/rag/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, stream: false }),
    });

    const data = await response.json();
    return {
      questionId: `q_${Date.now()}`,
      question,
      vector: {
        answer: data.answer || '',
        sources: data.sources || [],
        metrics: data.metrics || { latencyMs: 0, chunksUsed: 0 },
      },
      graph: {
        answer: data.answer || '',
        sources: data.sources || [],
        cypherQuery: data.cypher_query || '',
        graphContext: data.graph_context || [],
        metrics: {
          ...(data.metrics || { latencyMs: 0, chunksUsed: 0 }),
          graphNodesUsed: data.graph_nodes_used || 0,
          graphHops: data.graph_hops || 0,
        },
      },
      timestamp: new Date().toISOString(),
    };
  },

  getHistory: async (): Promise<CompareResponse[]> => {
    // No history endpoint in backend yet - return empty array
    return [];
  },

  submitAnnotation: async (questionId: string, preference: string, comment?: string): Promise<void> => {
    await fetchWithErrorHandling(`${API_BASE_URL}/api/annotations/simple`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ questionId, preference, comment }),
    });
  },
};

// Graph Service - Real Implementation
export const graphService = {
  // Get graph nodes from backend
  getGraphNodes: async (limit: number = 100): Promise<GraphData> => {
    const response = await fetchWithErrorHandling(
      `${API_BASE_URL}/api/graph/nodes?limit=${limit}`
    );
    return await response.json();
  },

  // Get graph schema
  getSchema: async (): Promise<{ labels: string[][]; relationships: string[]; properties: string[] }> => {
    const response = await fetchWithErrorHandling(`${API_BASE_URL}/api/graph/schema`);
    return await response.json();
  },

  // Get graph statistics
  getStats: async (): Promise<{ node_count: number; relationship_count: number; avg_connections: number }> => {
    const response = await fetchWithErrorHandling(`${API_BASE_URL}/api/graph/stats`);
    return await response.json();
  },

  // Execute arbitrary Cypher (MATCH only)
  execute: async (cypher: string): Promise<GraphData> => {
    const response = await fetchWithErrorHandling(`${API_BASE_URL}/api/graph/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: cypher }),
    });

    const data = await response.json();

    // Transform execute results to GraphData format
    // This is a simplified transformation - may need adjustment based on actual query
    const nodesMap = new Map<string, GraphData['nodes'][0]>();
    const links: GraphData['links'] = [];

    for (const record of data.results || []) {
      // Extract nodes from result
      for (const key of Object.keys(record)) {
        const value = record[key];
        if (value && typeof value === 'object' && value.id) {
          nodesMap.set(value.id, {
            id: value.id,
            label: value.label || value.text || value.name || value.id,
            type: value.type || 'document',
            properties: value.properties || value,
          });
        }
      }
    }

    return {
      nodes: Array.from(nodesMap.values()),
      links,
    };
  },

  // Text to Cypher - not implemented in backend yet
  text2cypher: async (_query: string): Promise<{ cypher: string }> => {
    throw new Error('Text-to-Cypher not implemented. Use manual Cypher queries.');
  },
};

// Health Service
export const healthService = {
  check: async (): Promise<{
    status: string;
    neo4j_connected: boolean;
    message: string;
    node_count?: number;
  }> => {
    const response = await fetchWithErrorHandling(`${API_BASE_URL}/api/health`);
    return await response.json();
  },
};

// Stats Service - Real Implementation
export interface SystemStats {
  document_count: number;
  question_count: number;
  relationship_count: number;
  avg_response_time_ms?: number;
  accuracy_percent?: number;
}

export const statsService = {
  getStats: async (): Promise<SystemStats> => {
    const response = await fetchWithErrorHandling(`${API_BASE_URL}/api/stats`);
    return await response.json();
  },
};

// Annotation Service - Real Implementation
export const annotationService = {
  getPending: async (): Promise<AnnotationTask[]> => {
    const response = await fetchWithErrorHandling(`${API_BASE_URL}/api/annotations/pending`);
    return await response.json();
  },

  submit: async (rating: AnnotationRating): Promise<void> => {
    await fetchWithErrorHandling(`${API_BASE_URL}/api/annotations/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(rating),
    });
  },

  getStats: async (): Promise<AnnotatorStats> => {
    const response = await fetchWithErrorHandling(`${API_BASE_URL}/api/annotations/stats`);
    return await response.json();
  },
};

// Auth Service - Real Implementation
export const authService = {
  login: async (email: string, password: string): Promise<{ token: string; user: User }> => {
    const response = await fetchWithErrorHandling(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    return await response.json();
  },

  logout: async (): Promise<void> => {
    // Clear local state - backend is stateless
  },

  getProfile: async (): Promise<User> => {
    const response = await fetchWithErrorHandling(`${API_BASE_URL}/api/auth/profile`);
    return await response.json();
  },
};
