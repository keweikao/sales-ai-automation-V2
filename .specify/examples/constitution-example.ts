/**
 * 範例：Constitution 階段的最佳實踐
 * 展示如何高效載入 Constitution 內容
 */

import * as constitution from '../mcp-server/servers/constitution/index.js';
import { countTokens } from '../mcp-server/client.js';

async function constitutionExample() {
  console.log('=== Constitution 載入範例 ===\n');

  console.log('步驟 1: 載入摘要...');
  const summary = await constitution.getConstitutionSummary();
  const summaryTokens = countTokens(summary.summary);
  console.log(summary.summary);
  console.log(`\n使用 tokens: ${summaryTokens}`);

  console.log('\n步驟 2: 搜尋特定主題...');
  const searchResult = await constitution.searchConstitution({
    query: 'code quality',
    maxResults: 2,
  });

  if (searchResult.sections.length > 0) {
    console.log(`\n找到 ${searchResult.sections.length} 個相關章節:`);
    searchResult.sections.forEach((section) => {
      console.log(`\n## ${section.title}`);
      console.log(section.content.substring(0, 200) + '...');
    });

    const searchTokens = searchResult.sections.reduce(
      (sum, section) => sum + countTokens(section.content),
      0
    );
    console.log(`\n額外使用 tokens: ${searchTokens}`);
  }

  console.log('\n總結:');
  console.log('- 先載入摘要了解整體結構');
  console.log('- 再按需搜尋特定主題');
  console.log('- 避免載入不需要的內容');
  console.log(`- 總共使用約 ${summaryTokens} tokens`);
  console.log('- 比直接載入完整文件節省約 87%！');
}

constitutionExample();
