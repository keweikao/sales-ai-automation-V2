import path from 'path';
import { glob } from 'glob';
import { readMarkdownFile, PROJECT_ROOT } from '../../client.js';

export interface Task {
  id: string;
  title: string;
  description: string;
  phase?: string;
  dependencies: string[];
  files: string[];
  status?: 'pending' | 'in-progress' | 'completed';
  parallelMarker?: boolean;
}

export async function parseTasksFile(): Promise<Task[]> {
  const taskFiles = await glob('.specify/specs/*/tasks.md', {
    cwd: PROJECT_ROOT,
  });

  if (taskFiles.length === 0) {
    throw new Error('No tasks.md file found');
  }

  const tasksPath = path.join(PROJECT_ROOT, taskFiles[0]);
  const content = await readMarkdownFile(tasksPath);

  const tasks: Task[] = [];
  const lines = content.split(/\r?\n/);

  let currentPhase = '';
  let currentTask: Partial<Task> | null = null;
  let inDescriptionBlock = false;

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (line.match(/^##\s+Phase\s+\d+/i)) {
      currentPhase = line.replace(/^##\s+/, '').trim();
      continue;
    }

    const taskMatch = line.match(/^(?:###\s+)?Task\s+([\d.]+):\s+(.+?)(\s+\[P\])?$/i);
    if (taskMatch) {
      if (currentTask && currentTask.id) {
        tasks.push(finalizeTask(currentTask));
      }

      currentTask = {
        id: taskMatch[1],
        title: taskMatch[2].trim(),
        phase: currentPhase,
        dependencies: [],
        files: [],
        parallelMarker: Boolean(taskMatch[3]),
        description: '',
      };

      inDescriptionBlock = false;
      continue;
    }

    if (!currentTask) continue;

    if (line.startsWith('**Description:**') || line.startsWith('Description:')) {
      inDescriptionBlock = true;
      const desc = line.replace(/\*\*Description:\*\*|Description:/i, '').trim();
      currentTask.description = desc;
      continue;
    }

    if (line.startsWith('**Dependencies:**') || line.startsWith('Dependencies:')) {
      const depsMatch = line.match(/Dependencies:\s*(.+)/i);
      if (depsMatch && currentTask.dependencies) {
        const depsStr = depsMatch[1].trim();
        if (depsStr.toLowerCase() !== 'none') {
          currentTask.dependencies = depsStr
            .split(',')
            .map((dep) => dep.trim())
            .filter(Boolean);
        }
      }
      inDescriptionBlock = false;
      continue;
    }

    if (line.startsWith('**Files:**') || line.startsWith('Files:')) {
      inDescriptionBlock = false;
      continue;
    }

    if (line.startsWith('- `') && line.includes('`')) {
      const fileMatch = line.match(/`([^`]+)`/);
      if (fileMatch && currentTask.files) {
        currentTask.files.push(fileMatch[1]);
      }
      continue;
    }

    if (inDescriptionBlock && line.length > 0 && !line.startsWith('**')) {
      currentTask.description = `${currentTask.description} ${line}`.trim();
    }
  }

  if (currentTask && currentTask.id) {
    tasks.push(finalizeTask(currentTask));
  }

  return tasks;
}

function finalizeTask(task: Partial<Task>): Task {
  return {
    id: task.id!,
    title: task.title || '',
    description: task.description?.trim() || '',
    phase: task.phase,
    dependencies: task.dependencies ?? [],
    files: task.files ?? [],
    status: task.status,
    parallelMarker: task.parallelMarker,
  };
}

export function findTaskById(tasks: Task[], taskId: string): Task | undefined {
  return tasks.find((task) => task.id === taskId);
}

export function getTaskDependencies(tasks: Task[], taskId: string): Task[] {
  const task = findTaskById(tasks, taskId);
  if (!task) return [];

  return task.dependencies
    .map((depId) => findTaskById(tasks, depId))
    .filter((dep): dep is Task => Boolean(dep));
}
