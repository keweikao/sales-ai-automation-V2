import { parseTasksFile, Task } from './parser.js';

export interface GetAllTasksInput {
  phase?: string;
}

export async function getAllTasks(
  input: GetAllTasksInput = {}
): Promise<Task[]> {
  const tasks = await parseTasksFile();

  if (input.phase) {
    const phaseLower = input.phase.toLowerCase();
    return tasks.filter((task) => task.phase?.toLowerCase().includes(phaseLower));
  }

  return tasks;
}
