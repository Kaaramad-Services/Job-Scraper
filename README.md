# Job Tracker Application

Monitors expatriates.com for job postings with specific keywords and sends Discord notifications.

## Features
- Monitors https://www.expatriates.com/classifieds/saudi-arabia/
- Filters jobs by keywords you specify
- Extracts email and WhatsApp numbers
- Sends rich Discord notifications
- Runs 24/7 on Render.com
- Checks every 10 minutes

## Setup Instructions

### 1. Create Discord Webhook
1. Go to your Discord server
2. Channel Settings → Integrations → Webhooks
3. Create New Webhook
4. Copy the Webhook URL

### 2. Deploy to Render.com

**Option A: One-click Deploy**
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

**Option B: Manual Deployment**
1. Push this code to GitHub
2. Go to [Render.com](https://render.com)
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Configure:
   - **Name:** job-tracker
   - **Environment:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`

### 3. Set Environment Variables
In Render dashboard, go to your service → Environment:
- `JOB_KEYWORDS`: driver,engineer,teacher (comma-separated)
- `DISCORD_WEBHOOK_URL`: your_discord_webhook_url
- `CHECK_INTERVAL`: 600 (10 minutes in seconds)

### 4. Local Development
```bash
# Clone repository
git clone https://github.com/yourusername/job-tracker.git
cd job-tracker

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your values

# Run application
python main.py