import { parseTasksFile, getTaskDependencies, Task } from './parser.js';

export interface GetDependenciesInput {
  taskId: string;
}

export async function getDependencies(
  input: GetDependenciesInput
): Promise<Task[]> {
  if (!input?.taskId) {
    throw new Error('taskId is required');
  }

  const tasks = await parseTasksFile();
  return getTaskDependencies(tasks, input.taskId);
}
