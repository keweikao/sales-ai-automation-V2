import { parseTasksFile, Task } from './parser.js';

export async function getNextTask(): Promise<Task | null> {
  const tasks = await parseTasksFile();
  const nextTask = tasks.find((task) => !task.status || task.status === 'pending');
  return nextTask ?? null;
}
