#!/usr/bin/env node
import { Command } from 'commander';
import * as constitution from './mcp-server/servers/constitution/index.js';
import * as tasks from './mcp-server/servers/tasks/index.js';
import { countTokens } from './mcp-server/client.js';

const program = new Command();

program
  .name('llm-helper')
  .description('Speckit LLM Helper - 高效的文件存取工具')
  .version('2.0.0');

program
  .command('constitution-summary')
  .description('取得 Constitution 摘要')
  .action(async () => {
    try {
      const summary = await constitution.getConstitutionSummary();
      const tokens = countTokens(summary.summary);
      console.log(summary.summary);
      console.log(`\n[Token Usage: ${tokens}]`);
    } catch (error) {
      console.error('Error:', error);
      process.exit(1);
    }
  });

program
  .command('constitution-search')
  .description('搜尋 Constitution')
  .requiredOption('-q, --query <query>', '搜尋關鍵字')
  .option('-n, --max <number>', '最大結果數', '3')
  .action(async (options) => {
    try {
      const result = await constitution.searchConstitution({
        query: options.query,
        maxResults: parseInt(options.max, 10),
      });
      console.log(JSON.stringify(result, null, 2));
      const totalTokens = result.sections.reduce(
        (sum, section) => sum + countTokens(section.content),
        0
      );
      console.log(`\n[Token Usage: ${totalTokens}]`);
    } catch (error) {
      console.error('Error:', error);
      process.exit(1);
    }
  });

program
  .command('task')
  .description('取得特定任務的資訊')
  .requiredOption('-i, --id <taskId>', '任務 ID (例如: 3.2)')
  .option('-c, --context', '包含相關的 spec 和 plan 內容', false)
  .action(async (options) => {
    try {
      const task = await tasks.getTaskById({
        taskId: options.id,
        includeContext: options.context,
      });
      console.log(JSON.stringify(task, null, 2));
      const tokens = countTokens(JSON.stringify(task));
      console.log(`\n[Token Usage: ${tokens}]`);
    } catch (error) {
      console.error('Error:', error);
      process.exit(1);
    }
  });

program
  .command('next-task')
  .description('取得下一個要執行的任務')
  .action(async () => {
    try {
      const task = await tasks.getNextTask();
      if (!task) {
        console.log('No pending tasks found.');
        return;
      }
      console.log(JSON.stringify(task, null, 2));
      const tokens = countTokens(JSON.stringify(task));
      console.log(`\n[Token Usage: ${tokens}]`);
    } catch (error) {
      console.error('Error:', error);
      process.exit(1);
    }
  });

program
  .command('all-tasks')
  .description('列出所有任務')
  .option('-p, --phase <phase>', '只顯示特定階段的任務')
  .action(async (options) => {
    try {
      const allTasks = await tasks.getAllTasks({ phase: options.phase });
      console.log(JSON.stringify(allTasks, null, 2));
      const tokens = countTokens(JSON.stringify(allTasks));
      console.log(`\n[Token Usage: ${tokens}]`);
    } catch (error) {
      console.error('Error:', error);
      process.exit(1);
    }
  });

program
  .command('stats')
  .description('顯示 token 使用統計')
  .action(async () => {
    try {
      const fs = await import('fs/promises');
      const pathModule = await import('path');
      const logPath = pathModule.join(process.cwd(), '.specify/logs/token-usage.json');
      const data = await fs.readFile(logPath, 'utf-8');
      const records = JSON.parse(data);
      const totalTokens = records.reduce((sum: number, record: any) => sum + record.tokens, 0);
      const totalCalls = records.length;
      const avgTokens = totalCalls ? Math.round(totalTokens / totalCalls) : 0;
      const byTool: Record<string, { count: number; tokens: number }> = {};
      records.forEach((record: any) => {
        if (!byTool[record.tool]) {
          byTool[record.tool] = { count: 0, tokens: 0 };
        }
        byTool[record.tool].count += 1;
        byTool[record.tool].tokens += record.tokens;
      });
      console.log('=== Token Usage Statistics ===\n');
      console.log(`Total API Calls: ${totalCalls}`);
      console.log(`Total Tokens: ${totalTokens.toLocaleString()}`);
      console.log(`Average per Call: ${avgTokens.toLocaleString()}`);
      console.log('\nBy Tool:');
      Object.entries(byTool)
        .sort((a, b) => b[1].tokens - a[1].tokens)
        .forEach(([tool, stats]) => {
          console.log(`  ${tool}: ${stats.count} calls, ${stats.tokens.toLocaleString()} tokens`);
        });
    } catch (error) {
      console.log('No usage data found yet.');
    }
  });

program.parse();
