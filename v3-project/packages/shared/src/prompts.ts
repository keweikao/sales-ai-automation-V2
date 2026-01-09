import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROMPTS_DIR = join(__dirname, '../../shared/prompts');

/**
 * Load a MEDDIC agent prompt
 */
export function loadMeddicPrompt(
  agent: 'agent1-context' | 'agent2-buyer' | 'agent3-seller' | 'agent4-summary' | 'agent6-crm-extractor' | 'global-context'
): string {
  const path = join(PROMPTS_DIR, 'meddic', `${agent}.md`);
  return readFileSync(path, 'utf-8');
}

/**
 * Load all MEDDIC prompts
 */
export function loadAllMeddicPrompts() {
  return {
    globalContext: loadMeddicPrompt('global-context'),
    agent1Context: loadMeddicPrompt('agent1-context'),
    agent2Buyer: loadMeddicPrompt('agent2-buyer'),
    agent3Seller: loadMeddicPrompt('agent3-seller'),
    agent4Summary: loadMeddicPrompt('agent4-summary'),
    agent6CrmExtractor: loadMeddicPrompt('agent6-crm-extractor'),
  };
}

/**
 * Load a template prompt
 */
export function loadTemplatePrompt(
  template: 'mcp-context-optimization' | 'mcp-tool-discovery'
): string {
  const path = join(PROMPTS_DIR, 'templates', `${template}.md`);
  return readFileSync(path, 'utf-8');
}
