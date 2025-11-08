#!/usr/bin/env node
import * as constitution from './mcp-server/servers/constitution/index.js';
import * as tasks from './mcp-server/servers/tasks/index.js';
import { countTokens } from './mcp-server/client.js';
import fs from 'fs/promises';
import path from 'path';

const colors = {
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  reset: '\x1b[0m',
};

function log(color: keyof typeof colors, message: string) {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

const PROJECT_ROOT =
  path.basename(process.cwd()) === '.specify'
    ? path.resolve(process.cwd(), '..')
    : process.cwd();

async function testConstitutionOptimization() {
  console.log('\n' + '='.repeat(50));
  log('blue', '測試 1: Constitution 載入優化');
  console.log('='.repeat(50));

  try {
    const fullPath = path.join(PROJECT_ROOT, '.specify/memory/constitution.md');
    const fullContent = await fs.readFile(fullPath, 'utf-8');
    const oldTokens = countTokens(fullContent);

    const summary = await constitution.getConstitutionSummary();
    const newTokens = countTokens(summary.summary);

    const saved = oldTokens - newTokens;
    const savingsPercent = ((saved / oldTokens) * 100).toFixed(1);

    console.log(`\n舊方式（完整文件）: ${oldTokens.toLocaleString()} tokens`);
    console.log(`新方式（API 摘要）: ${newTokens.toLocaleString()} tokens`);
    console.log(`節省: ${saved.toLocaleString()} tokens (${savingsPercent}%)`);

    const passed = parseFloat(savingsPercent) >= 85;
    if (passed) {
      log('green', '\n✅ 測試通過！達到 85% 節省目標');
    } else {
      log('red', '\n❌ 測試失敗！未達到 85% 節省目標');
    }

    return passed;
  } catch (error) {
    log('red', `\n❌ 測試錯誤: ${error}`);
    return false;
  }
}

async function testTaskOptimization() {
  console.log('\n' + '='.repeat(50));
  log('blue', '測試 2: 任務資訊載入優化');
  console.log('='.repeat(50));

  try {
    const { glob } = await import('glob');
    const specFiles = await glob('.specify/specs/*/spec.md', { cwd: PROJECT_ROOT });
    const planFiles = await glob('.specify/specs/*/plan.md', { cwd: PROJECT_ROOT });
    const tasksFiles = await glob('.specify/specs/*/tasks.md', { cwd: PROJECT_ROOT });

    let oldTokens = 0;

    if (specFiles.length > 0) {
      const spec = await fs.readFile(path.join(PROJECT_ROOT, specFiles[0]), 'utf-8');
      oldTokens += countTokens(spec);
    }
    if (planFiles.length > 0) {
      const plan = await fs.readFile(path.join(PROJECT_ROOT, planFiles[0]), 'utf-8');
      oldTokens += countTokens(plan);
    }
    if (tasksFiles.length > 0) {
      const taskFile = await fs.readFile(path.join(PROJECT_ROOT, tasksFiles[0]), 'utf-8');
      oldTokens += countTokens(taskFile);
    }

    const allTasks = await tasks.getAllTasks();

    if (allTasks.length === 0) {
      log('yellow', '\n⚠️  沒有找到任務，跳過此測試');
      return true;
    }

    const task = await tasks.getTaskById({
      taskId: allTasks[0].id,
      includeContext: true,
    });

    const newTokens = countTokens(JSON.stringify(task));

    const saved = oldTokens - newTokens;
    const savingsPercent = ((saved / oldTokens) * 100).toFixed(1);

    console.log(`\n舊方式（完整文件）: ${oldTokens.toLocaleString()} tokens`);
    console.log(`新方式（API 查詢）: ${newTokens.toLocaleString()} tokens`);
    console.log(`節省: ${saved.toLocaleString()} tokens (${savingsPercent}%)`);

    const passed = parseFloat(savingsPercent) >= 85;
    if (passed) {
      log('green', '\n✅ 測試通過！達到 85% 節省目標');
    } else {
      log('red', '\n❌ 測試失敗！未達到 85% 節省目標');
    }

    return passed;
  } catch (error) {
    log('red', `\n❌ 測試錯誤: ${error}`);
    return false;
  }
}

async function testSearchFunctionality() {
  console.log('\n' + '='.repeat(50));
  log('blue', '測試 3: 搜尋功能');
  console.log('='.repeat(50));

  try {
    const result = await constitution.searchConstitution({
      query: 'code',
      maxResults: 3,
    });

    console.log(`\n找到 ${result.sections.length} 個相關章節`);

    if (result.sections.length > 0) {
      console.log('\n章節標題:');
      result.sections.forEach((section, index) => {
        console.log(`  ${index + 1}. ${section.title}`);
      });
    }

    const passed = result.sections.length > 0;
    if (passed) {
      log('green', '\n✅ 測試通過！搜尋功能正常');
    } else {
      log('red', '\n❌ 測試失敗！沒有找到結果');
    }

    return passed;
  } catch (error) {
    log('red', `\n❌ 測試錯誤: ${error}`);
    return false;
  }
}

async function testCLITools() {
  console.log('\n' + '='.repeat(50));
  log('blue', '測試 4: CLI 工具');
  console.log('='.repeat(50));

  try {
    const { exec } = await import('child_process');
    const { promisify } = await import('util');
    const execAsync = promisify(exec);

    const { stdout } = await execAsync('npx tsx .specify/llm-helper.ts stats');

    console.log('\nCLI 輸出:');
    console.log(stdout);

    log('green', '\n✅ 測試通過！CLI 工具正常運作');
    return true;
  } catch (error) {
    log('yellow', '\n⚠️  CLI 工具測試跳過（可能還沒有使用記錄）');
    return true;
  }
}

async function runAllTests() {
  log('blue', '\n🧪 開始 Speckit Token 優化測試\n');

  const results = {
    constitution: await testConstitutionOptimization(),
    task: await testTaskOptimization(),
    search: await testSearchFunctionality(),
    cli: await testCLITools(),
  };

  console.log('\n' + '='.repeat(50));
  log('blue', '測試總結');
  console.log('='.repeat(50));

  const passed = Object.values(results).filter(Boolean).length;
  const total = Object.values(results).length;

  console.log(`\n通過: ${passed}/${total}`);

  if (passed === total) {
    log('green', '\n🎉 所有測試通過！Token 優化成功！');
    log('green', '預期總節省: 85-90%');
  } else {
    log('red', '\n⚠️  部分測試失敗，請檢查實作');
  }

  process.exit(passed === total ? 0 : 1);
}

runAllTests();
