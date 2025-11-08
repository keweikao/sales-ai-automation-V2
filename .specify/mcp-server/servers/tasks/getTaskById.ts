import path from 'path';
import { glob } from 'glob';
import { parseTasksFile, findTaskById, Task } from './parser.js';
import { readMarkdownFile, PROJECT_ROOT } from '../../client.js';

export interface GetTaskByIdInput {
  taskId: string;
  includeContext?: boolean;
}

export interface TaskWithContext extends Task {
  relatedSpecSections?: string[];
  relatedPlanSections?: string[];
  acceptanceCriteria?: string[];
}

export async function getTaskById(
  input: GetTaskByIdInput
): Promise<TaskWithContext> {
  if (!input?.taskId) {
    throw new Error('taskId is required');
  }

  const tasks = await parseTasksFile();
  const task = findTaskById(tasks, input.taskId);
  if (!task) {
    throw new Error(`Task not found: ${input.taskId}`);
  }

const result: TaskWithContext = { ...task };

  if (input.includeContext) {
    const [specSections, planSections, acceptanceCriteria] = await Promise.all([
      extractRelatedSpecSections(task),
      extractRelatedPlanSections(task),
      extractAcceptanceCriteria(),
    ]);

    result.relatedSpecSections = specSections;
    result.relatedPlanSections = planSections;
    result.acceptanceCriteria = acceptanceCriteria;
  }

  return result;
}

async function extractRelatedSpecSections(task: Task): Promise<string[]> {
  return extractSectionsFromFile(task, 'spec.md');
}

async function extractRelatedPlanSections(task: Task): Promise<string[]> {
  return extractSectionsFromFile(task, 'plan.md');
}

async function extractSectionsFromFile(task: Task, fileName: string) {
  try {
    const files = await glob(`.specify/specs/*/${fileName}`, {
      cwd: PROJECT_ROOT,
    });
    if (!files.length) return [];

    const filePath = path.join(PROJECT_ROOT, files[0]);
    const content = await readMarkdownFile(filePath);
    const keywords = extractKeywords(`${task.title} ${task.description}`);
    const sections = splitIntoSections(content);

    return sections
      .filter((section) => {
        const lower = section.toLowerCase();
        return keywords.some((keyword) => lower.includes(keyword));
      })
      .slice(0, 3)
      .map((section) => truncateSection(section));
  } catch (error) {
    console.error(`Error extracting sections from ${fileName}:`, error);
    return [];
  }
}

async function extractAcceptanceCriteria(): Promise<string[]> {
  try {
    const specFiles = await glob('.specify/specs/*/spec.md', {
      cwd: PROJECT_ROOT,
    });
    if (!specFiles.length) return [];

    const specPath = path.join(PROJECT_ROOT, specFiles[0]);
    const content = await readMarkdownFile(specPath);
    const lines = content.split(/\r?\n/);

    const criteria: string[] = [];
    let inSection = false;

    for (const line of lines) {
      if (line.match(/##.*acceptance criteria/i)) {
        inSection = true;
        continue;
      }

      if (inSection && line.startsWith('## ')) {
        break;
      }

      if (inSection && (line.startsWith('- ') || line.startsWith('* '))) {
        criteria.push(line.replace(/^[*-]\s+/, '').trim());
      }
    }

    return criteria.slice(0, 5);
  } catch (error) {
    console.error('Error extracting acceptance criteria:', error);
    return [];
  }
}

function extractKeywords(text: string): string[] {
  const stopWords = ['the', 'and', 'with', 'from', 'this', 'that'];
  const words = text
    .toLowerCase()
    .replace(/[^\w\s]/g, ' ')
    .split(/\s+/)
    .filter((word) => word.length > 3 && !stopWords.includes(word));

  return [...new Set(words)]
    .sort((a, b) => b.length - a.length)
    .slice(0, 5);
}

function splitIntoSections(content: string): string[] {
  const sections: string[] = [];
  const lines = content.split(/\r?\n/);
  let currentSection: string[] = [];

  for (const line of lines) {
    if (line.startsWith('## ')) {
      if (currentSection.length > 0) {
        sections.push(currentSection.join('\n').trim());
      }
      currentSection = [line.trim()];
    } else {
      currentSection.push(line);
    }
  }

  if (currentSection.length > 0) {
    sections.push(currentSection.join('\n').trim());
  }

  return sections;
}

function truncateSection(section: string, limit = 600): string {
  if (section.length <= limit) {
    return section;
  }
  return `${section.slice(0, limit)}...`;
}
