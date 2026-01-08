/**
 * API Client 類型生成腳本
 * 從 OpenAPI Schema 生成 TypeScript 類型
 */
import { execSync } from 'child_process';
import { existsSync } from 'fs';
import { resolve } from 'path';

const OPENAPI_PATH = resolve(__dirname, '../../../../api-gateway/openapi.json');
const OUTPUT_PATH = resolve(__dirname, '../src/schema.d.ts');

console.log('🔍 Checking OpenAPI schema...');

if (!existsSync(OPENAPI_PATH)) {
  console.log('⚠️  OpenAPI schema not found at:', OPENAPI_PATH);
  console.log('📝 Creating placeholder schema.d.ts...');

  // 建立佔位符
  const placeholder = `
// 此檔案由 openapi-typescript 自動生成
// 執行 'bun run generate' 來重新生成
// 需要先啟動 API Gateway 並產生 openapi.json

export interface paths {}
export interface components {}
export interface operations {}
`;

  require('fs').writeFileSync(OUTPUT_PATH, placeholder);
  console.log('✅ Placeholder created');
  process.exit(0);
}

console.log('📦 Generating API client types...');

try {
  execSync(`bunx openapi-typescript ${OPENAPI_PATH} -o ${OUTPUT_PATH}`, {
    stdio: 'inherit',
  });
  console.log('✅ API client types generated successfully!');
} catch (error) {
  console.error('❌ Failed to generate types:', error);
  process.exit(1);
}
