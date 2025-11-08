import path from 'path';
import { readMarkdownFile, PROJECT_ROOT } from '../../client.js';

export interface ConstitutionSummary {
  coreValues: string[];
  keyPrinciples: string[];
  technicalGuidelines: string[];
  summary: string;
}

export interface GetConstitutionSummaryInput {
  maxLength?: number;
}

const DEFAULT_MAX_SUMMARY_LENGTH = 500;

/**
 * Extract high-level sections from the constitution document and compress
 * the content down to a lightweight summary.
 */
export async function getConstitutionSummary(
  input: GetConstitutionSummaryInput = {}
): Promise<ConstitutionSummary> {
  const maxLength = input.maxLength ?? DEFAULT_MAX_SUMMARY_LENGTH;
  const constitutionPath = path.join(
    PROJECT_ROOT,
    '.specify/memory/constitution.md'
  );

  const fullContent = await readMarkdownFile(constitutionPath);
  const { coreValues, keyPrinciples, technicalGuidelines } =
    extractSections(fullContent);

  const truncatedCoreValues = coreValues;
  const truncatedPrinciples = keyPrinciples.slice(0, 5);
  const truncatedGuidelines = technicalGuidelines.slice(0, 3);

  const summaryParts: string[] = [
    '# Constitution Summary',
    '',
    '## Core Values',
    ...truncatedCoreValues.map((value) => `- ${value}`),
    '',
    '## Key Principles',
    ...truncatedPrinciples.map((principle) => `- ${principle}`),
    '',
    '## Technical Guidelines',
    ...truncatedGuidelines.map((guideline) => `- ${guideline}`),
  ];

  let summary = summaryParts.join('\n');
  if (summary.length > maxLength) {
    summary = summary.slice(0, maxLength).concat('...');
  }

  return {
    coreValues: truncatedCoreValues,
    keyPrinciples: truncatedPrinciples,
    technicalGuidelines: truncatedGuidelines,
    summary,
  };
}

/** Parse the markdown to collect list items under each section. */
function extractSections(content: string) {
  const lines = content.split(/\r?\n/);
  const coreValues: string[] = [];
  const keyPrinciples: string[] = [];
  const technicalGuidelines: string[] = [];
  let currentSection = '';

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) continue;

    if (line.startsWith('## ')) {
      currentSection = line.replace(/^##\s+/, '').toLowerCase();
      continue;
    }

    if (/^[*-]\s+/.test(line)) {
      const item = line.replace(/^[*-]\s+/, '').split(':')[0].trim();
      if (!item) continue;

      if (includesKeyword(currentSection, ['core', 'value'])) {
        coreValues.push(item);
      } else if (includesKeyword(currentSection, ['principle'])) {
        keyPrinciples.push(item);
      } else if (
        includesKeyword(currentSection, ['technical']) ||
        includesKeyword(currentSection, ['guideline'])
      ) {
        technicalGuidelines.push(item);
      }
    }
  }

  return { coreValues, keyPrinciples, technicalGuidelines };
}

function includesKeyword(section: string, keywords: string[]): boolean {
  return keywords.some((keyword) => section.includes(keyword));
}
