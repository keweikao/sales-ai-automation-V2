import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { parse } from 'yaml';
import type { LeadSchema, ConversationSchema, MeddicSchema } from './types';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SCHEMAS_DIR = join(__dirname, '../../shared/schemas');

/**
 * Load and parse a YAML schema
 */
function loadYamlSchema<T>(filename: string): T {
  const path = join(SCHEMAS_DIR, filename);
  const content = readFileSync(path, 'utf-8');
  return parse(content) as T;
}

/**
 * Load Lead schema
 */
export function loadLeadSchema(): LeadSchema {
  return loadYamlSchema<LeadSchema>('lead.yaml');
}

/**
 * Load Conversation schema
 */
export function loadConversationSchema(): ConversationSchema {
  return loadYamlSchema<ConversationSchema>('conversation.yaml');
}

/**
 * Load MEDDIC schema
 */
export function loadMeddicSchema(): MeddicSchema {
  return loadYamlSchema<MeddicSchema>('meddic.yaml');
}

/**
 * Load all schemas
 */
export function loadAllSchemas() {
  return {
    lead: loadLeadSchema(),
    conversation: loadConversationSchema(),
    meddic: loadMeddicSchema(),
  };
}
