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

// Mock delay to simulate API calls
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

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

// Mock data (kept for fallback)
const mockDocuments: Document[] = [
  {
    id: '1',
    name: 'Thông tư 219/2013/TT-BTC về thuế GTGT.pdf',
    uploadedAt: '2024-01-15T10:30:00Z',
    status: 'completed',
  },
  {
    id: '2',
    name: 'Nghị định 126/2020/NĐ-CP hướng dẫn Luật Quản lý thuế.pdf',
    uploadedAt: '2024-01-14T14:20:00Z',
    status: 'completed',
  },
  {
    id: '3',
    name: 'Công văn 4943/TCT-CS về chính sách thuế.docx',
    uploadedAt: '2024-01-13T09:15:00Z',
    status: 'processing',
    progress: 65,
  },
  {
    id: '4',
    name: 'Luật Thuế Thu nhập doanh nghiệp 2008.pdf',
    uploadedAt: '2024-01-12T16:45:00Z',
    status: 'completed',
  },
  {
    id: '5',
    name: 'Thông tư 78/2014/TT-BTC thuế TNCN.pdf',
    uploadedAt: '2024-01-11T11:00:00Z',
    status: 'failed',
  },
];

const mockQAResult: QAResult = {
  answer: 'Theo Thông tư 219/2013/TT-BTC, thuế suất thuế GTGT áp dụng cho hàng hóa xuất khẩu là 0%. Cụ thể, tại Điều 10 quy định về thuế suất thuế GTGT đối với hàng hóa, dịch vụ xuất khẩu: "Thuế suất thuế GTGT đối với hàng hóa, dịch vụ xuất khẩu là 0%, trừ một số trường hợp đặc biệt theo quy định".',
  sources: [
    {
      text: 'Điều 10. Thuế suất thuế GTGT đối với hàng hóa, dịch vụ xuất khẩu\n1. Thuế suất thuế GTGT đối với hàng hóa, dịch vụ xuất khẩu là 0%.\n2. Hàng hóa, dịch vụ xuất khẩu không áp dụng thuế suất 0% bao gồm...',
      score: 0.95,
      documentId: '1',
      documentName: 'Thông tư 219/2013/TT-BTC',
    },
    {
      text: 'Khoản 1 Điều 9 Luật Thuế GTGT quy định: "Thuế suất thuế GTGT là 0% áp dụng đối với hàng hóa, dịch vụ xuất khẩu; vận tải quốc tế; hàng hóa, dịch vụ không chịu thuế GTGT được quy định tại Điều 5 của Luật này..."',
      score: 0.88,
      documentId: '1',
      documentName: 'Thông tư 219/2013/TT-BTC',
    },
    {
      text: 'Hàng hóa xuất khẩu là hàng hóa được bán để xuất khẩu hoặc mang ra nước ngoài theo quy định của pháp luật về hải quan...',
      score: 0.76,
      documentId: '1',
      documentName: 'Thông tư 219/2013/TT-BTC',
    },
  ],
  metrics: {
    latencyMs: 1240,
    chunksUsed: 8,
    confidenceScore: 0.92,
  },
};

const mockGraphQAResult: GraphQAResult = {
  answer: 'Theo quy định của pháp luật thuế Việt Nam, thuế suất thuế GTGT áp dụng cho hàng hóa xuất khẩu là 0%. Điều này được quy định rõ ràng tại Điều 10 Thông tư 219/2013/TT-BTC và Khoản 1 Điều 9 Luật Thuế GTGT. Thuế suất 0% áp dụng nhằm khuyến khích xuất khẩu và đảm bảo tính cạnh tranh của hàng hóa Việt Nam trên thị trường quốc tế. Doanh nghiệp xuất khẩu được hoàn thuế GTGT đầu vào theo quy định.',
  sources: [
    {
      text: 'Điều 10. Thuế suất thuế GTGT đối với hàng hóa, dịch vụ xuất khẩu\n1. Thuế suất thuế GTGT đối với hàng hóa, dịch vụ xuất khẩu là 0%.',
      score: 0.96,
      documentId: '1',
      documentName: 'Thông tư 219/2013/TT-BTC',
    },
    {
      text: 'Doanh nghiệp xuất khẩu hàng hóa, dịch vụ được hoàn thuế GTGT đầu vào theo quy định tại Điều 15 và Điều 16...',
      score: 0.89,
      documentId: '1',
      documentName: 'Thông tư 219/2013/TT-BTC',
    },
  ],
  cypherQuery: `MATCH (d:Document)-[:CONTAINS]->(a:Article)-[:REGULATES]->(t:TaxRate)
WHERE t.type = 'VAT' AND a.content CONTAINS 'xuất khẩu'
RETURN d, a, t
LIMIT 5`,
  graphContext: [
    {
      nodes: [
        { id: 'd1', label: 'Thông tư 219/2013', type: 'Document' },
        { id: 'a10', label: 'Điều 10', type: 'Article' },
        { id: 't1', label: 'Thuế suất 0%', type: 'TaxRate' },
      ],
      relationships: [
        { source: 'd1', target: 'a10', type: 'CONTAINS' },
        { source: 'a10', target: 't1', type: 'REGULATES' },
      ],
    },
  ],
  metrics: {
    latencyMs: 1580,
    chunksUsed: 6,
    confidenceScore: 0.94,
    graphNodesUsed: 12,
    graphHops: 2,
  },
};

// Document Service
export const documentService = {
  list: async (): Promise<Document[]> => {
    await delay(500);
    return [...mockDocuments];
  },

  upload: async (files: File[]): Promise<{ taskId: string }> => {
    await delay(1000);
    return { taskId: `task_${Date.now()}` };
  },

  getProgress: async (taskId: string): Promise<UploadProgress> => {
    await delay(300);
    const progress = Math.floor(Math.random() * 100);
    const steps = [
      'Trích xuất văn bản',
      'Trích xuất thực thể',
      'Xây dựng đồ thị',
      'Tạo vector embedding',
    ];
    return {
      taskId,
      progress,
      step: steps[Math.floor(progress / 25)],
      estimatedTimeMs: (100 - progress) * 500,
    };
  },

  delete: async (ids: string[]): Promise<void> => {
    await delay(500);
    console.log('Deleted documents:', ids);
  },

  reprocess: async (ids: string[]): Promise<void> => {
    await delay(800);
    console.log('Reprocessing documents:', ids);
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

  // Non-streaming compare (mock fallback for now)
  compare: async (question: string): Promise<CompareResponse> => {
    try {
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
        graph: mockGraphQAResult, // Graph-based response not implemented yet
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      // Fall back to mock data if backend unavailable
      console.warn('Backend unavailable, using mock data:', error);
      await delay(2000);
      return {
        questionId: `q_${Date.now()}`,
        question,
        vector: mockQAResult,
        graph: mockGraphQAResult,
        timestamp: new Date().toISOString(),
      };
    }
  },

  getHistory: async (): Promise<CompareResponse[]> => {
    await delay(500);
    return [
      {
        questionId: 'q_1',
        question: 'Thuế suất VAT cho dịch vụ giáo dục?',
        vector: mockQAResult,
        graph: mockGraphQAResult,
        timestamp: '2024-01-15T10:30:00Z',
      },
      {
        questionId: 'q_2',
        question: 'Điều kiện được miễn thuế thu nhập cá nhân?',
        vector: mockQAResult,
        graph: mockGraphQAResult,
        timestamp: '2024-01-15T09:15:00Z',
        annotation: {
          userId: 'user1',
          preference: 'graph',
          comment: 'Graph answer có ngữ cảnh rõ ràng hơn',
          timestamp: '2024-01-15T09:20:00Z',
        },
      },
    ];
  },

  submitAnnotation: async (questionId: string, preference: string, comment?: string): Promise<void> => {
    await delay(500);
    console.log('Annotation submitted:', { questionId, preference, comment });
  },
};

// Graph Service - Real Implementation
export const graphService = {
  // Get Test_rel_2 graph data from backend
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

  // Text to Cypher (mock for now - could implement with LLM)
  text2cypher: async (query: string): Promise<{ cypher: string }> => {
    await delay(1500);
    return {
      cypher: `MATCH (n:Test_rel_2)-[r]-(m:Test_rel_2)
WHERE n.text CONTAINS '${query.slice(0, 20)}'
RETURN n, r, m
LIMIT 10`,
    };
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

// Annotation Service
export const annotationService = {
  getPending: async (): Promise<AnnotationTask[]> => {
    await delay(700);
    return [
      {
        id: 'task1',
        questionId: 'q_100',
        question: 'Cách tính thuế thu nhập cá nhân từ tiền lương?',
        vectorAnswer: mockQAResult,
        graphAnswer: mockGraphQAResult,
        status: 'pending',
      },
      {
        id: 'task2',
        questionId: 'q_101',
        question: 'Thời hạn nộp thuế GTGT hàng tháng?',
        vectorAnswer: mockQAResult,
        graphAnswer: mockGraphQAResult,
        status: 'pending',
      },
    ];
  },

  submit: async (rating: AnnotationRating): Promise<void> => {
    await delay(500);
    console.log('Rating submitted:', rating);
  },

  getStats: async (): Promise<AnnotatorStats> => {
    await delay(400);
    return {
      totalAssigned: 150,
      completedToday: 12,
      pendingReview: 38,
      agreementRate: 0.87,
    };
  },
};

// Auth Service
export const authService = {
  login: async (email: string, password: string): Promise<{ token: string; user: User }> => {
    await delay(800);
    // Mock authentication
    if (password === 'demo') {
      return {
        token: `token_${Date.now()}`,
        user: {
          id: 'user1',
          email,
          name: 'Nguyễn Văn A',
          role: 'annotator',
        },
      };
    }
    throw new Error('Thông tin đăng nhập không chính xác');
  },

  logout: async (): Promise<void> => {
    await delay(300);
  },

  getProfile: async (): Promise<User> => {
    await delay(400);
    return {
      id: 'user1',
      email: 'annotator@example.com',
      name: 'Nguyễn Văn A',
      role: 'annotator',
    };
  },
};
