export interface Document {
  id: string;
  name: string;
  uploadedAt: string;
  status: 'processing' | 'completed' | 'failed';
  progress?: number;
}

export interface QASource {
  text: string;
  score: number;
  documentId: string;
  documentName?: string;
}

export interface QAMetrics {
  latencyMs: number;
  chunksUsed: number;
  confidenceScore?: number;
}

export interface QAResult {
  answer: string;
  sources: QASource[];
  metrics: QAMetrics;
}

export interface GraphMetrics extends QAMetrics {
  graphNodesUsed: number;
  graphHops: number;
}

export interface GraphContextNode {
  id: string;
  label: string;
  type: string;
}

export interface GraphContextRelationship {
  source: string;
  target: string;
  type: string;
}

export interface GraphContext {
  nodes: GraphContextNode[];
  relationships: GraphContextRelationship[];
}

export interface GraphQAResult extends Omit<QAResult, 'metrics'> {
  cypherQuery: string | null;
  graphContext: GraphContext[];
  metrics: GraphMetrics;
}

export interface CompareResponse {
  questionId: string;
  question: string;
  vector: QAResult;
  graph: GraphQAResult;
  timestamp: string;
  annotation?: Annotation;
}

export interface Annotation {
  userId: string;
  preference: 'vector' | 'equivalent' | 'graph' | 'both_wrong';
  comment?: string;
  timestamp: string;
}

export interface User {
  id: string;
  email: string;
  name: string;
  role: 'annotator' | 'admin';
}

export interface AnnotationTask {
  id: string;
  questionId: string;
  question: string;
  vectorAnswer: QAResult;
  graphAnswer: GraphQAResult;
  status: 'pending' | 'completed' | 'skipped';
}

export interface AnnotationRating {
  questionId: string;
  vectorCorrectness: number;
  vectorCompleteness: number;
  vectorRelevance: number;
  graphCorrectness: number;
  graphCompleteness: number;
  graphRelevance: number;
  overallComparison: 'vector_much_better' | 'vector_better' | 'equivalent' | 'graph_better' | 'graph_much_better';
  comment?: string;
}

export interface AnnotatorStats {
  totalAssigned: number;
  completedToday: number;
  pendingReview: number;
  agreementRate: number;
}

export interface GraphNode {
  id: string;
  label: string;
  type: 'document' | 'article' | 'tax_type' | 'taxpayer' | 'exemption';
  properties: Record<string, unknown>;
}

export interface GraphLink {
  source: string;
  target: string;
  type: string;
  properties?: Record<string, unknown>;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

export interface UploadProgress {
  taskId: string;
  progress: number;
  step: string;
  estimatedTimeMs?: number;
}
