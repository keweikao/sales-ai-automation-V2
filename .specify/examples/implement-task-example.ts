/**
 * 範例：Implement 階段的完整工作流程
 * 展示如何高效實作一個任務
 */

import * as tasks from '../mcp-server/servers/tasks/index.js';
import { countTokens } from '../mcp-server/client.js';

async function implementTaskExample() {
  console.log('=== 實作任務的完整流程 ===\n');

  let totalTokens = 0;

  console.log('步驟 1: 取得下一個要執行的任務...');
  const nextTask = await tasks.getNextTask();

  if (!nextTask) {
    console.log('沒有待執行的任務！');
    return;
  }

  console.log(`下一個任務: ${nextTask.id} - ${nextTask.title}`);
  totalTokens += countTokens(JSON.stringify(nextTask));

  console.log(`\n步驟 2: 載入任務 ${nextTask.id} 的完整資訊...`);
  const task = await tasks.getTaskById({
    taskId: nextTask.id,
    includeContext: true,
  });

  const taskTokens = countTokens(JSON.stringify(task));
  totalTokens += taskTokens;

  console.log(`\n任務: ${task.title}`);
  console.log(`描述: ${task.description}`);

  console.log(`\n步驟 3: 檢查相依任務...`);
  const deps = await tasks.getDependencies({ taskId: task.id });
  if (deps.length > 0) {
    console.log('相依任務:');
    deps.forEach((dep) => {
      console.log(`  - ${dep.id}: ${dep.title}`);
    });
  } else {
    console.log('無相依任務，可以直接開始');
  }
  totalTokens += countTokens(JSON.stringify(deps));

  console.log('\n步驟 4: 要修改的檔案:');
  task.files.forEach((file) => {
    console.log(`  - ${file}`);
  });

  if (task.relatedSpecSections?.length) {
    console.log('\n步驟 5: 相關功能需求:');
    task.relatedSpecSections.slice(0, 2).forEach((section) => {
      console.log(`\n${section.substring(0, 200)}...`);
    });
  }

  if (task.relatedPlanSections?.length) {
    console.log('\n步驟 6: 技術實作細節:');
    task.relatedPlanSections.slice(0, 2).forEach((section) => {
      console.log(`\n${section.substring(0, 200)}...`);
    });
  }

  if (task.acceptanceCriteria?.length) {
    console.log('\n步驟 7: 驗收標準:');
    task.acceptanceCriteria.forEach((criteria, index) => {
      console.log(`  ${index + 1}. ${criteria}`);
    });
  }

  console.log('\n' + '='.repeat(50));
  console.log('Token 使用總結:');
  console.log('='.repeat(50));
  console.log(`總使用: ${totalTokens.toLocaleString()} tokens`);
  console.log('\n對比:');
  console.log('- 傳統方式（載入完整 spec + plan + tasks）: ~12,000 tokens');
  console.log(`- 新方式（API 查詢）: ${totalTokens.toLocaleString()} tokens`);
  console.log(`- 節省: ${((1 - totalTokens / 12000) * 100).toFixed(1)}%`);

  console.log('\n現在可以開始實作任務了！');
}

implementTaskExample();
