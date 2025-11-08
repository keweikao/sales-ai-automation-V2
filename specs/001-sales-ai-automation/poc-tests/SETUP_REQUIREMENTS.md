# POC Execution Setup Requirements

**Purpose**: Complete checklist of system configurations needed to execute POC 1-6 tests.

**Target**: User (Stephen) should complete these setups before running POC tests.

---

## 📋 Quick Checklist

- [ ] **GCP Setup** (30 minutes)
- [ ] **Gemini API Key** (5 minutes)
- [ ] **Slack Workspace** (20 minutes)
- [ ] **Test Data Preparation** (15 minutes)
- [ ] **Local Environment** (10 minutes)

**Total Estimated Time**: ~80 minutes

---

## 1️⃣ GCP Setup (Google Cloud Platform)

### 1.1 Create/Select GCP Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing project
3. **Record your Project ID** (e.g., `sales-ai-automation-poc`)

```bash
export GCP_PROJECT_ID="your-project-id"

```

### 1.2 Enable Billing

1. Go to **Billing** → Link billing account
2. Verify billing is enabled for the project
3. ⚠️ **Warning**: POC tests will incur small costs (~$1-2)

### 1.3 Enable Required APIs

Enable the following APIs (can be done via Console or CLI):

```bash
gcloud config set project $GCP_PROJECT_ID

# Enable APIs
gcloud services enable firestore.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable aiplatform.googleapis.com
```

**Or via Console**:

- Go to **APIs & Services** → **Enable APIs and Services**
- Search and enable:
  - ✅ Cloud Firestore API
  - ✅ Cloud Storage API
  - ✅ Vertex AI API

### 1.4 Create Firestore Database (for POC 5)

1. Go to [Firestore Console](https://console.firebase.google.com/project/_/firestore)
2. Click **Create Database**
3. Choose **Native Mode** (not Datastore mode)
4. Select location: **asia-east1** (Taiwan) or **us-central1** (if testing in US)
5. Start in **Test Mode** (for POC only, will change to production rules later)

### 1.5 Create Service Account (for local testing)

```bash
# Create service account
gcloud iam service-accounts create poc-test-sa \
 --display-name="POC Test Service Account"

# Grant necessary roles
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
 --member="serviceAccount:poc-test-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
 --role="roles/datastore.user"

# Create and download key
gcloud iam service-accounts keys create ~/poc-test-sa-key.json \
 --iam-account=poc-test-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com

# Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/poc-test-sa-key.json"
```

**Record**:

- ✅ GCP Project ID: `_______________`
- ✅ Service Account Key Path: `_______________`

---

## 2️⃣ Gemini API Key (for POC 2, 3, 6)

### 2.1 Get Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click **Get API Key**
3. Create API key for your GCP project
4. **Copy and save the API key** (starts with `AIza...`)

```bash
export GEMINI_API_KEY="AIza..."
```

### 2.2 Verify API Access

Test the API key works:

```bash
curl -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}' \
  -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key=${GEMINI_API_KEY}"
```

Expected: JSON response with generated text.

**Record**:

- ✅ Gemini API Key: `AIza_______________` (keep secret!)

---

## 3️⃣ Slack Workspace Setup (for POC 4)

### 3.1 Create Slack Workspace (if needed)

1. Go to [slack.com/create](https://slack.com/create)
2. Create workspace for testing (e.g., "iCHEF Sales AI POC")
3. Create test channel: `#sales-ai-test`

### 3.2 Create Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App** → **From scratch**
3. App Name: `Sales AI POC`
4. Workspace: Select your test workspace
5. Click **Create App**

### 3.3 Enable Socket Mode ⚠️ **IMPORTANT**

1. Go to **Socket Mode** (in sidebar)
2. **Enable Socket Mode** (toggle ON)
3. Generate **App-Level Token**:
   - Token Name: `poc-socket-token`
   - Add scope: `connections:write`
   - Click **Generate**
   - **Copy and save token** (starts with `xapp-...`)

```bash
export SLACK_APP_TOKEN="xapp-..."
```

### 3.4 Configure OAuth Scopes

1. Go to **OAuth & Permissions**
2. Scroll to **Scopes** → **Bot Token Scopes**
3. Add the following scopes:
   - ✅ `chat:write` - Send messages
   - ✅ `chat:write.public` - Send messages to public channels
   - ✅ `commands` - Add slash commands
   - ✅ `files:read` - Read uploaded files
   - ✅ `im:history` - View direct messages

### 3.5 Enable Interactivity & Shortcuts

1. Go to **Interactivity & Shortcuts**
2. **Turn On Interactivity**
3. ⚠️ **Request URL**: You must fill in a URL (required by Slack)
   - For Socket Mode POC testing, use placeholder: `https://example.com/slack/interactive`
   - **Note**: This URL will NOT be used in Socket Mode (WebSocket is used instead)
4. Click **Save Changes**

### 3.6 Enable Slash Commands

1. Go to **Slash Commands**
2. Click **Create New Command**
3. Command: `/sales-ai-test`
4. ⚠️ **Request URL**: Use placeholder: `https://example.com/slack/commands`
   - **Note**: This URL will NOT be used in Socket Mode
5. Short Description: `Test sales AI command`
6. Click **Save**

### 3.7 Install App to Workspace

1. Go to **Install App** (in sidebar)
2. Click **Install to Workspace**
3. Review permissions → Click **Allow**
4. **Copy Bot User OAuth Token** (starts with `xoxb-...`)

```bash
export SLACK_BOT_TOKEN="xoxb-..."
   ```

### 3.8 Get Test Channel ID

1. Open Slack workspace
2. Go to test channel (e.g., `#sales-ai-test`)
3. Click channel name → Scroll to bottom
4. **Copy Channel ID** (starts with `C...`)

```bash
export SLACK_TEST_CHANNEL="C..."

```

### 3.9 Invite Bot to Channel

In Slack, type in `#sales-ai-test`:

```text
/invite @Sales AI POC
```text

**Record**:

- ✅ Slack Bot Token: `xoxb-_______________` (keep secret!)
- ✅ Slack App Token: `xapp-_______________` (keep secret!)
- ✅ Slack Test Channel ID: `C_______________`

---

## 4️⃣ Test Data Preparation

### 4.1 Audio Files (for POC 1)

Prepare **10 test audio files** with variety:

| File | Duration | Speakers | Language | Notes |
|------|----------|----------|----------|-------|
| test_01.m4a | 5 min | 2 | 中文 | Short call |
| test_02.m4a | 15 min | 2 | 中文 | Medium call |
| test_03.m4a | 40 min | 3 | 中文 | Long call, 3 speakers |
| test_04.m4a | 10 min | 2 | 中文 | Background noise |
| test_05.wav | 8 min | 2 | 中文 | WAV format |
| test_06.m4a | 20 min | 4 | 中文 | 4 speakers |
| test_07.m4a | 3 min | 2 | 中文 | Very short |
| test_08.m4a | 30 min | 2 | 中文 | Technical discussion |
| test_09.m4a | 12 min | 2 | 中文 | Price negotiation |
| test_10.m4a | 25 min | 3 | 中文 | Discovery call |

**Where to get test audio**:

- Option A: Use real sales call recordings (anonymized)
- Option B: Record mock sales calls with team members
- Option C: Use existing recordings from legacy system

**Store in**:

```bash
mkdir -p ~/sales-ai-automation-V2/test-data/audio
# Copy files to this directory
```text

### 4.2 Transcripts (for POC 2, 3, 6)

Prepare **30 test transcripts** with variety:

Create in: `~/sales-ai-automation-V2/test-data/transcripts/`

**Transcript format** (JSON):

```json
{
  "fileId": "test_01",
  "duration": 1200,
  "text": "完整逐字稿內容...",
  "speakers": [
 {
   "speaker": "業務",
   "startTime": 0.0,
   "endTime": 5.2,
   "text": "您好，我是 iCHEF 的業務..."
 },
 {
   "speaker": "客戶",
   "startTime": 5.5,
   "endTime": 12.1,
   "text": "你好，我們是餐廳老闆..."
 }
  ]
}
```text

**Variety needed**:

- 10 files: Positive sentiment (interested customer)
- 10 files: Neutral sentiment (information gathering)
- 10 files: Negative sentiment (skeptical, budget concerns)
- Include mentions of iCHEF 22 features (掃碼點餐, 線上訂位, POS系統, etc.)

**Generate transcripts**:

```bash
# If you have audio files, transcribe them first using POC 1
# Or manually create test transcripts based on common sales scenarios
```text

### 4.3 Test Scenarios Template

Create test scenarios file: `test-data/scenarios.json`

```json
[
  {
 "id": "scenario_01",
 "title": "高興趣客戶，尖峰人力不足",
 "description": "客戶明確表示尖峰時段人手不足，對掃碼點餐很有興趣",
 "expected_needs": ["掃碼點餐", "POS點餐系統"],
 "expected_sentiment": "positive"
  },
  {
 "id": "scenario_02",
 "title": "預算限制，先了解功能",
 "description": "客戶預算有限，想先了解基本功能和價格",
 "expected_needs": ["POS點餐系統"],
 "expected_barriers": ["budget"],
 "expected_sentiment": "neutral"
  }
]
```text

**Record**:

- ✅ Audio files prepared: `_____ / 10`
- ✅ Transcripts prepared: `_____ / 30`
- ✅ Test scenarios created: Yes / No

---

## 5️⃣ Local Development Environment

### 5.1 Install Python 3.9+

```bash
# Check Python version
python3 --version  # Should be 3.9 or higher

# If not installed, install Python 3.9+
# macOS (using Homebrew)
brew install python@3.9

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3.9 python3.9-venv python3-pip
```text

### 5.2 Create Virtual Environment

```bash
cd ~/Desktop/sales-ai-automation-V2/specs/001-sales-ai-automation/poc-tests

# Create virtual environment
python3 -m venv poc-venv

# Activate virtual environment
source poc-venv/bin/activate  # On macOS/Linux
# poc-venv\Scripts\activate  # On Windows
```text

### 5.3 Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install dependencies for all POCs
pip install faster-whisper==0.10.0
pip install torch==2.1.0
pip install google-generativeai==0.3.2
pip install google-cloud-firestore==2.14.0
pip install slack-bolt==1.18.0
pip install websocket-client==1.7.0

# For audio processing (POC 1)
pip install ffmpeg-python==0.2.0
pip install pyannote.audio==3.1.1

# For testing utilities
pip install pytest==7.4.3
```text

### 5.4 Install System Dependencies

**macOS**:

```bash
# Install ffmpeg (for audio processing)
brew install ffmpeg
```text

**Ubuntu/Debian**:

```bash
sudo apt-get update
sudo apt-get install ffmpeg
```text

**Windows**:

- Download ffmpeg from [ffmpeg.org](https://ffmpeg.org/download.html)
- Add to PATH

### 5.5 Set Environment Variables

Create `.env` file in `poc-tests/` directory:

```bash
cd ~/Desktop/sales-ai-automation-V2/specs/001-sales-ai-automation/poc-tests

cat > .env << 'EOF'
# GCP Configuration
export GCP_PROJECT_ID="your-project-id"
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/poc-test-sa-key.json"

# Gemini API
export GEMINI_API_KEY="AIza..."

# Slack Configuration
export SLACK_BOT_TOKEN="xoxb-..."
export SLACK_APP_TOKEN="xapp-..."
export SLACK_TEST_CHANNEL="C..."

# Test Data Paths
export TEST_AUDIO_DIR="$HOME/Desktop/sales-ai-automation-V2/test-data/audio"
export TEST_TRANSCRIPT_DIR="$HOME/Desktop/sales-ai-automation-V2/test-data/transcripts"
EOF
```text

Load environment variables:

```bash
source .env
```text

**Record**:

- ✅ Python 3.9+ installed: Yes / No
- ✅ Virtual environment created: Yes / No
- ✅ Dependencies installed: Yes / No
- ✅ Environment variables set: Yes / No

---

## 6️⃣ Verify Setup

### 6.1 Quick Verification Script

Create and run verification script:

```bash
cat > verify_setup.sh << 'EOF'
#!/bin/bash

echo "=== POC Setup Verification ==="
echo ""

# Check Python
echo "✓ Python Version:"
python3 --version
echo ""

# Check environment variables
echo "✓ Environment Variables:"
echo "  GCP_PROJECT_ID: ${GCP_PROJECT_ID:0:20}..."
echo "  GEMINI_API_KEY: ${GEMINI_API_KEY:0:10}..."
echo "  SLACK_BOT_TOKEN: ${SLACK_BOT_TOKEN:0:10}..."
echo "  SLACK_APP_TOKEN: ${SLACK_APP_TOKEN:0:10}..."
echo "  SLACK_TEST_CHANNEL: $SLACK_TEST_CHANNEL"
echo ""

# Check Python packages
echo "✓ Python Packages:"
python3 -c "import faster_whisper; print(f'  faster-whisper: {faster_whisper.__version__}')"
python3 -c "import google.generativeai as genai; print('  google-generativeai: OK')"
python3 -c "import google.cloud.firestore; print('  google-cloud-firestore: OK')"
python3 -c "import slack_bolt; print('  slack-bolt: OK')"
echo ""

# Check ffmpeg
echo "✓ System Dependencies:"
which ffmpeg && echo "  ffmpeg: OK" || echo "  ffmpeg: NOT FOUND"
echo ""

# Check test data
echo "✓ Test Data:"
echo "  Audio files: $(ls -1 $TEST_AUDIO_DIR 2>/dev/null | wc -l) files"
echo "  Transcript files: $(ls -1 $TEST_TRANSCRIPT_DIR 2>/dev/null | wc -l) files"
echo ""

# Test GCP access
echo "✓ GCP Access:"
gcloud config get-value project 2>/dev/null && echo "  gcloud: OK" || echo "  gcloud: NOT CONFIGURED"
echo ""

# Test Gemini API
echo "✓ Gemini API:"
curl -s -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hi"}]}]}' \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${GEMINI_API_KEY}" \
  | grep -q "candidates" && echo "  API Key: VALID" || echo "  API Key: INVALID"
echo ""

echo "=== Setup Verification Complete ==="
EOF

chmod +x verify_setup.sh
./verify_setup.sh
```text

Expected output: All items should show ✓ OK or valid status.

---

## 7️⃣ Ready to Execute POCs

Once all items are checked, you're ready to run POC tests:

### POC Execution Order

```bash
# Activate virtual environment
source poc-venv/bin/activate
source .env

# POC 1: Whisper + Diarization (5-10 min)
cd poc1_whisper
python test_whisper.py

# POC 2: Multi-Agent Parallel (10-15 min)
cd ../poc2_multi_agent
python test_parallel.py

# POC 3: Gemini Structured Output (5-10 min)
cd ../poc3_gemini
python test_structured_output.py

# POC 4: Slack Interactivity (5-10 min)
cd ../poc4_slack
python test_slack_interactivity.py

# POC 5: Firestore Performance (5-10 min)
cd ../poc5_firestore
python test_firestore_performance.py

# POC 6: Questionnaire Extraction (10-15 min)
cd ../poc6_questionnaire
python test_questionnaire.py
```text

**Total POC Execution Time**: ~40-70 minutes

---

## 📝 Troubleshooting

### Issue: GCP Permission Denied

**Solution**:

```bash
# Verify service account has correct roles
gcloud projects get-iam-policy $GCP_PROJECT_ID \
 --flatten="bindings[].members" \
 --filter="bindings.members:poc-test-sa@*"

# Re-grant roles if needed
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
 --member="serviceAccount:poc-test-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
 --role="roles/datastore.user"
```text

### Issue: Gemini API Rate Limit

**Solution**:

- Free tier: 15 requests/minute
- Add delays between tests: `time.sleep(5)`
- Or upgrade to paid tier

### Issue: Slack Socket Mode Connection Failed

**Solution**:

1. Verify App-Level Token has `connections:write` scope
2. Verify Bot Token starts with `xoxb-`
3. Verify App-Level Token starts with `xapp-`
4. Check app is installed to workspace
5. Try regenerating tokens

### Issue: Faster-Whisper CUDA Not Available

**Solution**:

```bash
# Check CUDA availability
python3 -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"

# If False, Whisper will use CPU (slower but works)
# For POC, CPU is acceptable
```text

---

## 📞 Need Help?

**Before running POCs**:

1. Complete this checklist
2. Run verification script
3. Fix any issues found
4. Then proceed to POC execution

**During POC execution**:

- Check logs in console output
- Results saved to `poc*_results.json`
- Errors logged with detailed messages

---

**Checklist Complete**: _____ / 5 sections
**Ready to Execute POCs**: Yes / No
**Estimated POC Execution Time**: 40-70 minutes

---

*Last Updated: 2025-01-29*
*Version: 1.0*
