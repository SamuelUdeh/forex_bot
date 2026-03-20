# Deployment Guide - Forex Signal Bot

Deploy your signal bot to run 24/7 without needing your local computer.

---

## Option 1: Railway.app (Recommended - Easiest)

### Step 1: Push Code to GitHub

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - Forex Signal Bot"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/forex-signal-bot.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy on Railway

1. Go to [railway.app](https://railway.app)
2. Sign in with GitHub
3. Click **"New Project"**
4. Select **"Deploy from GitHub repo"**
5. Choose your `forex-signal-bot` repository
6. Railway will auto-detect the Dockerfile

### Step 3: Add Environment Variables

In Railway dashboard, go to **Variables** tab and add:

```
OANDA_API_KEY=your_oanda_api_key
OANDA_ACCOUNT_ID=your_oanda_account_id
OANDA_ENVIRONMENT=practice
DERIV_API_TOKEN=your_deriv_token
DERIV_APP_ID=1089
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
DRY_RUN=false
```

### Step 4: Deploy

Click **"Deploy"** - your bot will run 24/7!

**Cost:** Free tier includes 500 hours/month (enough for testing)
**Paid:** $5/month for always-on

---

## Option 2: DigitalOcean VPS

### Step 1: Create Droplet

1. Go to [digitalocean.com](https://digitalocean.com)
2. Create a Droplet (Ubuntu 22.04, $4/month)
3. SSH into your server

### Step 2: Setup Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install python3.12 python3-pip git -y

# Clone your repo
git clone https://github.com/YOUR_USERNAME/forex-signal-bot.git
cd forex-signal-bot

# Install dependencies
pip3 install -r requirements.txt

# Create .env file
cp .env.example .env
nano .env  # Add your API keys
```

### Step 3: Run with Systemd (Auto-restart)

```bash
# Create service file
sudo nano /etc/systemd/system/forex-bot.service
```

Add this content:
```ini
[Unit]
Description=Forex Signal Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/forex-signal-bot
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable forex-bot
sudo systemctl start forex-bot

# Check status
sudo systemctl status forex-bot

# View logs
sudo journalctl -u forex-bot -f
```

---

## Option 3: Render.com

1. Go to [render.com](https://render.com)
2. Create new **Background Worker**
3. Connect GitHub repo
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `python main.py`
6. Add environment variables
7. Deploy

**Cost:** Free tier available (with sleep after inactivity)

---

## Option 4: PythonAnywhere

1. Go to [pythonanywhere.com](https://pythonanywhere.com)
2. Create free account
3. Upload files via web interface
4. Create scheduled task to run every 4 hours
5. Add environment variables in .env file

**Note:** Free tier has limitations on external requests

---

## Monitoring Your Bot

### Check if Bot is Running

Your bot sends a startup message to Telegram when it starts:
```
🚀 Signal Bot Started!
🕒 2024-03-15 08:00 UTC

📊 Monitoring:
- OANDA: 6 instruments
- Deriv: 8 instruments

⏰ Checking every 4 hours
```

### View Logs (Railway)

In Railway dashboard → Deployments → View Logs

### View Logs (VPS)

```bash
sudo journalctl -u forex-bot -f
```

---

## Troubleshooting

### Bot Not Sending Signals

1. Check `DRY_RUN=false` in environment variables
2. Verify Telegram bot token and chat ID
3. Check logs for errors

### API Connection Failed

1. Verify API keys are correct
2. Check if you're using practice/live environment correctly
3. Ensure account has API access enabled

### Bot Keeps Restarting

1. Check logs for errors
2. Verify all dependencies installed
3. Check memory limits (upgrade if needed)

---

## Cost Comparison

| Platform | Free Tier | Paid |
|----------|-----------|------|
| Railway | 500 hrs/month | $5/month |
| DigitalOcean | None | $4/month |
| Render | Limited | $7/month |
| PythonAnywhere | Limited | $5/month |

**Recommended:** Start with Railway free tier, upgrade when needed.
