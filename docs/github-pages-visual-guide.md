# GitHub Pages 啟用詳細指引（附圖文說明）

> **適用於**: Repository Admin 找不到 Source 選單的情況

---

## 🔍 方法 1：直接啟用路徑（最常見）

### 步驟 1：進入 Pages 設定頁面

直接訪問此 URL（請確認您已登入 GitHub）：

```text
https://github.com/keweikao/sales-ai-automation-V2/settings/pages
```

或手動導航：

1. 開啟 <https://github.com/keweikao/sales-ai-automation-V2>
2. 點擊右上角的 **「⚙️ Settings」** 標籤（齒輪圖示）
3. 在左側選單往下滾動，找到 **「Pages」** 選項
   - 位置：在 "Code and automation" 區段下
   - 應該在 "Environments"、"Secrets and variables" 下方

### 步驟 2：尋找 Build and deployment 區段

進入 Pages 頁面後，您應該會看到：

#### 情況 A：已經有 "Build and deployment" 區段

畫面應顯示：

```text
Build and deployment
Source: [下拉選單]
```

**下拉選單選項**：

- Deploy from a branch（預設）
- GitHub Actions ← **選擇這個**

選擇 "GitHub Actions" 後：

- 不需要點擊 Save（會自動保存）
- 頁面會顯示：✅ GitHub Actions

#### 情況 B：顯示 "GitHub Pages is currently disabled"

如果您看到類似訊息：

```text
GitHub Pages is currently disabled. Select a source below to enable GitHub Pages for this repository.
```

這表示 Pages 尚未啟用，請繼續以下步驟：

1. 在 **"Source"** 下拉選單中，選擇 **"GitHub Actions"**
2. 頁面會重新載入並顯示 Pages 已啟用

#### 情況 C：完全看不到任何選項

如果頁面是空白或只顯示說明文字，可能有以下原因：

---

## 🔧 方法 2：檢查 Repository 權限

### 檢查項目 1：確認您是 Admin

1. 進入 <https://github.com/keweikao/sales-ai-automation-V2/settings>
2. 查看頁面頂部是否能看到所有設定選項
3. 如果看到 "You must be an admin to view this page"，表示權限不足

### 檢查項目 2：Repository 可見性

GitHub Pages 對於不同可見性的 repository 有不同要求：

**Private Repository**（私有倉庫）：

- 免費帳號：無法使用 GitHub Pages
- GitHub Pro/Team/Enterprise：可以使用 Pages

**Public Repository**（公開倉庫）：

- 所有帳號都可使用 Pages

**檢查方法**：

1. 進入 <https://github.com/keweikao/sales-ai-automation-V2>
2. 查看 repository 名稱旁邊的標籤
   - 如果顯示 "Private"，且您不是 Pro 用戶，需要升級或將 repo 改為 Public

**將 Private 改為 Public**（如果需要）：

1. 進入 Settings → General
2. 滾動到最底部 "Danger Zone"
3. 點擊 "Change repository visibility"
4. 選擇 "Make public"

⚠️ **注意**：改為 Public 後，所有人都能看到您的代碼

---

## 🔧 方法 3：使用 GitHub Actions 方式（不需要 Source 選單）

如果實在找不到 Source 選單，可以用此替代方法：

### 步驟 1：確認 Workflow 權限

1. 進入 <https://github.com/keweikao/sales-ai-automation-V2/settings/actions>
2. 找到 **"Workflow permissions"** 區段
3. 確認選擇了 **"Read and write permissions"**
4. 勾選 **"Allow GitHub Actions to create and approve pull requests"**
5. 點擊 **"Save"**

### 步驟 2：手動觸發 Workflow

1. 進入 <https://github.com/keweikao/sales-ai-automation-V2/actions>
2. 點擊左側的 **"Deploy Documentation to Pages"** workflow
3. 點擊右上角的 **"Run workflow"** 按鈕
4. 選擇 `main` branch
5. 點擊綠色的 **"Run workflow"** 按鈕

### 步驟 3：首次執行會提示啟用 Pages

Workflow 執行時，GitHub 可能會：

1. 自動偵測需要 Pages 功能
2. 顯示提示訊息詢問是否啟用
3. 點擊 **"Enable Pages"** 或 **"Configure Pages"**
4. 系統會自動設定 Source 為 "GitHub Actions"

---

## 🔧 方法 4：透過 API 啟用（進階）

如果以上方法都不行，可以使用 GitHub CLI：

### 安裝 GitHub CLI（如果還沒有）

```bash
# macOS
brew install gh

# Linux
sudo apt install gh

# Windows
winget install --id GitHub.cli
```

### 登入並啟用 Pages

```bash
# 登入 GitHub
gh auth login

# 啟用 Pages（設定為 GitHub Actions）
gh api \
  --method POST \
  -H "Accept: application/vnd.github+json" \
  /repos/keweikao/sales-ai-automation-V2/pages \
  -f build_type='workflow'
```

如果成功，會返回 Pages 的配置資訊。

---

## 📸 畫面截圖參考位置

### 正確的 Pages 設定頁面應該長這樣

```text
┌─────────────────────────────────────────────────────┐
│ GitHub Pages                                         │
├─────────────────────────────────────────────────────┤
│                                                      │
│ Build and deployment                                 │
│                                                      │
│ Source                                               │
│ ┌──────────────────────────────┐                    │
│ │ GitHub Actions            ▼  │  ← 選擇這個         │
│ └──────────────────────────────┘                    │
│                                                      │
│ ✅ Your site is live at                             │
│ https://keweikao.github.io/sales-ai-automation-V2/  │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Settings 側邊欄位置

```text
Settings (左側選單)
├── General
├── Access
│   ├── Collaborators and teams
│   └── Moderation options
├── Code and automation
│   ├── Branches
│   ├── Tags
│   ├── Actions
│   │   ├── General
│   │   └── Runners
│   ├── Webhooks
│   ├── Environments
│   ├── Pages              ← 在這裡！
│   └── Deployments
└── ...
```

---

## ❓ 常見問題排查

### Q1: 我看到 "Upgrade or make this repository public to enable Pages"

**原因**: Repository 是 Private 且您使用免費帳號

**解決方式**（選一）：

- 升級到 GitHub Pro（$4/月）
- 將 repository 改為 Public
- 暫時不使用 Pages（文檔仍可在 GitHub 上瀏覽）

---

### Q2: 我進入 Settings/Pages 但頁面完全空白

**可能原因**：

1. 瀏覽器快取問題
2. 權限載入延遲

**解決方式**：

```bash
# 清除快取後重試
1. 按 Ctrl+Shift+R (Windows) 或 Cmd+Shift+R (Mac) 強制重新載入
2. 或使用無痕模式重新登入
```

---

### Q3: 我是 Owner 但仍看不到 Pages 選項

**檢查項目**：

1. 確認 repository 不是 fork（fork 的 repo 可能無法啟用 Pages）
2. 確認組織設定沒有禁用 Pages

**檢查組織設定**（如果 repo 屬於組織）：

1. 進入組織設定：`https://github.com/organizations/YOUR_ORG/settings/pages`
2. 確認沒有禁用 GitHub Pages

---

## 🆘 如果以上方法都不行

請提供以下資訊以便進一步排查：

1. **您看到的畫面描述**：
   - 進入 Settings/Pages 後看到什麼？（完全空白 / 有文字但無選單 / 其他）

2. **Repository 狀態**：

   ```bash
   # 執行以下命令並提供輸出
   gh repo view keweikao/sales-ai-automation-V2 --json visibility,owner,permissions
   ```

3. **是否為組織 Repository**：
   - 個人帳號的 repo
   - 組織的 repo（組織名稱：___________）

4. **帳號類型**：
   - GitHub Free
   - GitHub Pro
   - GitHub Team
   - GitHub Enterprise

提供以上資訊後，我可以給出更精確的解決方案。

---

## ✅ 成功確認

啟用成功後，您應該會看到：

```text
✅ Your site is ready to be published at https://keweikao.github.io/sales-ai-automation-V2/
```

然後執行一次 workflow 來部署文檔：

```bash
# 方法 1：修改任何 docs/ 文件並推送
echo "# Test" >> docs/README.md
git add docs/README.md
git commit -m "Test Pages deployment"
git push

# 方法 2：手動觸發（Actions 頁面）
# 進入 Actions → Deploy Documentation to Pages → Run workflow
```

部署完成後（約 2-3 分鐘），文檔網站就會在上述 URL 可用。
