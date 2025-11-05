# GitHub Pages 啟用指南

> **目的**：解決 GitHub Actions `docs.yml` workflow 的 "Get Pages site failed" 錯誤，啟用專案文檔網站。

---

## 📋 問題說明

**錯誤訊息**:

```text
HttpError: Not Found - Get Pages site failed.
Please verify that the repository has Pages enabled and configured to build using GitHub Actions.
```

**原因**: Repository 尚未啟用 GitHub Pages 功能，但 `.github/workflows/docs.yml` workflow 嘗試部署文檔網站。

**影響**:

- ❌ 無法將文檔部署為網站（如 `https://keweikao.github.io/sales-ai-automation-V2/`）
- ✅ 不影響代碼功能或 Cloud Run 部署
- ✅ Markdown 文檔仍可在 GitHub 上正常瀏覽

---

## ✅ 啟用步驟（需要 Repository Admin 權限）

### 步驟 1：進入 Repository Settings

1. 開啟 GitHub repository: <https://github.com/keweikao/sales-ai-automation-V2>
2. 點擊右上角的 **「Settings」** 標籤
3. 在左側選單中，找到 **「Pages」** 選項（在 "Code and automation" 區段）

### 步驟 2：配置 Pages Source

在 **GitHub Pages** 設定頁面：

1. **Source** 區段：
   - 選擇 **「GitHub Actions」**（不是 "Deploy from a branch"）
   - 這樣可以讓 workflow 自動部署

2. 點擊 **「Save」** 按鈕

### 步驟 3：驗證配置

完成後，頁面應顯示：

```text
✅ Your site is ready to be published at https://keweikao.github.io/sales-ai-automation-V2/
```

---

## 🧪 測試部署

### 方式 1：自動觸發（推薦）

修改任何 `docs/**` 目錄下的文件並推送到 `main` branch，workflow 會自動執行。

```bash
# 範例：更新文檔
echo "test" >> docs/README.md
git add docs/README.md
git commit -m "Test docs deployment"
git push origin main
```

### 方式 2：手動觸發

1. 進入 GitHub repository
2. 點擊 **「Actions」** 標籤
3. 選擇左側的 **「Deploy Documentation to Pages」** workflow
4. 點擊右上角的 **「Run workflow」** 按鈕
5. 選擇 `main` branch 並點擊 **「Run workflow」**

---

## 🔍 檢查部署狀態

### 查看 Workflow 執行狀態

1. 進入 **Actions** 標籤
2. 查看 **「Deploy Documentation to Pages」** workflow 的最新執行

**成功標誌**:

- ✅ Build job 完成（綠色勾號）
- ✅ Deploy job 完成（綠色勾號）
- ✅ 可以看到部署 URL

**失敗處理**:

- 如果仍然出現 "Get Pages site failed"，請確認 Step 2 中 Source 設定為 **「GitHub Actions」**
- 檢查 workflow logs 中的具體錯誤訊息

### 訪問文檔網站

部署成功後，文檔網站將在以下 URL 可用：

```text
https://keweikao.github.io/sales-ai-automation-V2/
```

首次部署可能需要等待 1-2 分鐘。

---

## 📚 關於 DocFX

本專案使用 **DocFX** 來生成文檔網站。

### DocFX 配置文件

- **配置**: `docs/docfx.json`
- **源文件**: `docs/**/*.md`
- **輸出目錄**: `docs/_site/`（自動生成，已在 .gitignore 中）

### DocFX 功能

- 自動生成導航選單
- Markdown 轉換為 HTML
- 語法高亮
- 搜尋功能
- 響應式設計

### 本地預覽（可選）

如果需要在本地預覽文檔網站：

```bash
# 安裝 DocFX
dotnet tool install -g docfx

# 進入 docs 目錄
cd docs

# 構建並預覽
docfx docfx.json --serve
```

預覽網站將在 `http://localhost:8080` 可用。

---

## ⚙️ Workflow 配置說明

**Workflow 文件**: `.github/workflows/docs.yml`

**觸發條件**:

- Push 到 `main` branch 且修改 `docs/**` 目錄
- 手動觸發（workflow_dispatch）

**執行步驟**:

1. **Build Job**:
   - 安裝 .NET SDK
   - 安裝 DocFX
   - 構建文檔（`docfx docfx.json`）
   - 上傳構建產物

2. **Deploy Job**:
   - 部署到 GitHub Pages
   - 更新網站 URL

---

## ⚠️ 常見問題

### Q1: 啟用 Pages 後仍然報錯？

**檢查項目**:

1. 確認 Source 設定為 **「GitHub Actions」**（不是 "Deploy from a branch"）
2. 確認 workflow 有 `pages: write` 權限（已在 docs.yml 中配置）
3. 重新執行 workflow（Actions → 選擇 workflow → Re-run all jobs）

### Q2: 部署成功但網站顯示 404？

**可能原因**:

1. 首次部署需要等待 1-2 分鐘
2. DocFX 構建失敗，檢查 Build job logs

### Q3: 我沒有 Repository Admin 權限怎麼辦？

**解決方式**:

1. 聯絡 repository owner 或 admin
2. 請他們按照本指南的步驟 1-2 啟用 Pages
3. 或者將此文檔轉發給 admin

---

## ✅ 啟用完成確認清單

完成後，請確認：

- [ ] GitHub Pages 已在 Settings → Pages 中啟用
- [ ] Source 設定為 **「GitHub Actions」**
- [ ] Workflow 執行成功（無錯誤）
- [ ] 文檔網站可以訪問（`https://keweikao.github.io/sales-ai-automation-V2/`）
- [ ] 已記錄啟用日期和負責人

---

## 📝 記錄

**啟用日期**: _______________

**負責人**: _______________

**文檔網站 URL**: _______________

**驗證狀態**: ⬜ 成功 ⬜ 失敗（原因：_______________）

---

## 🔗 相關資源

- [GitHub Pages 官方文檔](https://docs.github.com/en/pages)
- [DocFX 官方網站](https://dotnet.github.io/docfx/)
- [GitHub Actions - configure-pages](https://github.com/actions/configure-pages)
