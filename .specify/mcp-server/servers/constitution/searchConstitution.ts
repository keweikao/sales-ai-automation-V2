import path from 'path';
import { readMarkdownFile, PROJECT_ROOT } from '../../client.js';

export interface SearchConstitutionInput {
  query: string;
  maxResults?: number;
}

export interface ConstitutionSection {
  title: string;
  content: string;
  relevance?: number;
}

export interface SearchConstitutionResult {
  sections: ConstitutionSection[];
  totalFound: number;
}

export async function searchConstitution(
  input: SearchConstitutionInput
): Promise<SearchConstitutionResult> {
  if (!input?.query?.trim()) {
    throw new Error('Query is required for constitution search.');
  }

  const constitutionPath = path.join(
    PROJECT_ROOT,
    '.specify/memory/constitution.md'
  );
  const fullContent = await readMarkdownFile(constitutionPath);
  const maxResults = input.maxResults ?? 3;
  const queryLower = input.query.toLowerCase();
  const sections = parseSections(fullContent);

  const matchedSections = sections
    .map((section) => {
      const titleMatch = section.title.toLowerCase().includes(queryLower);
      const contentMatch = section.content.toLowerCase().includes(queryLower);
      let relevance = 0;
      if (titleMatch) relevance += 0.7;
      if (contentMatch) relevance += 0.3;
      return { ...section, relevance };
    })
    .filter((section) => (section.relevance ?? 0) > 0)
    .sort((a, b) => (b.relevance ?? 0) - (a.relevance ?? 0))
    .slice(0, maxResults);

  return {
    sections: matchedSections,
    totalFound: matchedSections.length,
  };
}

function parseSections(content: string): ConstitutionSection[] {
  const sections: ConstitutionSection[] = [];
  const lines = content.split(/\r?\n/);
  let currentTitle = '';
  let currentContent: string[] = [];

  const pushSection = () => {
    if (!currentTitle || currentContent.length === 0) return;
    sections.push({
      title: currentTitle,
      content: currentContent.join('\n').trim(),
    });
  };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    if (line.startsWith('## ')) {
      pushSection();
      currentTitle = line.replace(/^##\s+/, '').trim();
      currentContent = [];
    } else if (currentTitle) {
      currentContent.push(line);
    }
  }

  pushSection();
  return sections;
}
