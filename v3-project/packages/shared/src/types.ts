/**
 * Lead Schema Types (from shared/schemas/lead.yaml)
 */
export interface LeadSchema {
  name: string;
  version: string;
  description: string;
  sources: string[];
  statuses: string[];
  fields: LeadField[];
}

export interface LeadField {
  name: string;
  type: string;
  required: boolean;
  description: string;
}

export type LeadSource =
  | 'manual'
  | 'website'
  | 'referral'
  | 'conference'
  | 'cold_outreach'
  | 'inbound_call'
  | 'slack';

export type LeadStatus =
  | 'new'
  | 'contacted'
  | 'qualified'
  | 'proposal'
  | 'negotiation'
  | 'won'
  | 'lost';

/**
 * Conversation Schema Types (from shared/schemas/conversation.yaml)
 */
export interface ConversationSchema {
  name: string;
  version: string;
  description: string;
  statuses: string[];
  types: string[];
  fields: ConversationField[];
}

export interface ConversationField {
  name: string;
  type: string;
  required: boolean;
  description: string;
}

export type ConversationStatus =
  | 'pending'
  | 'transcribing'
  | 'analyzing'
  | 'completed'
  | 'failed';

export type ConversationType =
  | 'discovery_call'
  | 'demo'
  | 'follow_up'
  | 'negotiation'
  | 'closing'
  | 'support';

/**
 * MEDDIC Schema Types (from shared/schemas/meddic.yaml)
 */
export interface MeddicSchema {
  name: string;
  version: string;
  description: string;
  dimensions: MeddicDimension[];
  commitment_events: string[];
  customer_types: CustomerType[];
  scoring: MeddicScoring;
}

export interface MeddicDimension {
  key: string;
  name: string;
  description: string;
  questions: string[];
}

export interface CustomerType {
  type: string;
  description: string;
  priority: string;
}

export interface MeddicScoring {
  levels: ScoringLevel[];
  weights: Record<string, number>;
}

export interface ScoringLevel {
  score: number;
  label: string;
  criteria: string;
}

/**
 * MEDDIC Dimension Keys
 */
export type MeddicDimensionKey =
  | 'metrics'
  | 'economic_buyer'
  | 'decision_criteria'
  | 'decision_process'
  | 'identify_pain'
  | 'champion';

/**
 * MEDDIC Analysis Result
 */
export interface MeddicAnalysis {
  conversationId: string;
  leadId: string;
  analyzedAt: Date;
  dimensions: Record<MeddicDimensionKey, DimensionAnalysis>;
  overallScore: number;
  summary: string;
  nextSteps: string[];
}

export interface DimensionAnalysis {
  score: number;
  evidence: string[];
  gaps: string[];
  recommendations: string[];
}
