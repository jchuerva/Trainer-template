# 🚀 Initial Setup

This guide covers the one-time setup for your forked running-trainer repository.

## 📋 Prerequisites

- GitHub account with [GitHub Copilot](https://github.com/features/copilot) subscription (Pro or higher)
- Python 3.x installed locally (optional, for local script execution)
- Apple Watch or device that exports `.fit` files

---

## 1️⃣ Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/running-trainer.git
cd running-trainer

# Install Python dependencies (optional, for local development)
python3 -m pip install -r requirements.txt
```

---

## 2️⃣ Configure Personal Information

All personal settings are centralized in `config/config.yaml`:

```yaml
athlete:
  date_of_birth: '1990-01-15'  # Your date of birth
  weight: 75                    # Weight in kg
  height: 180                   # Height in cm

preferences:
  run_days: [Tuesday, Thursday, Saturday]  # Your running days
  long_run_day: Saturday                   # Day for long runs
  strength_day: Sunday                     # Strength training day
  weekly_runs: 3                           # Runs per week

training_status:
  status: active  # active | sick | injury | holidays | returning
  note: ''        # Optional note about current status

current_goal:
  file: config/goals/2026-11-half-marathon-sub2h.md  # Path to your goal file

copilot:
  plan_model: claude-sonnet-4.6    # Model for weekly training plan generation
  analysis_model: claude-haiku-4.5 # Model for per-workout analysis
```

### Apply Configuration

After editing `config/config.yaml`, sync to templates:

```bash
python3 scripts/setup.py
```

This injects your personal data into all templates for better AI-generated plans.

> **Note:** When you push changes to `config/config.yaml`, the `sync-config.yml` workflow automatically validates and syncs templates.

---

## 3️⃣ Set Your Running Goal

1. Edit `config/goals/2026-11-half-marathon-sub2h.md` (or create a new goal file)
2. Update with your target:
   - Race and date
   - Goal time
   - Intermediate milestones
   - Current fitness baseline

3. Update `config/config.yaml` to point to your goal file:
   ```yaml
   current_goal:
     file: config/goals/your-goal-file.md
   ```

---

## 4️⃣ Set Up GitHub Secrets

GitHub Actions workflows need credentials to run.

### 🔑 Required: Copilot Token

1. Go to **GitHub Settings** > **Developer settings** > **Personal access tokens** > **[Tokens (classic)](https://github.com/settings/tokens)**

2. Click **"Generate new token (classic)"**

3. Configure:
   - **Note:** `Copilot Training Coach`
   - **Expiration:** Your preference (recommend: 1 year or no expiration)
   - **Scopes:**
     - `repo` (Full control of private repositories)
     - `workflow` (Update GitHub Action workflows)
     - Under "Copilot": Enable Copilot access

4. Click **"Generate token"** and **copy it** (you won't see it again)

5. Add to your repository:
   - Go to: **Your repo** > **Settings** > **Secrets and variables** > **Actions**
   - Click **"New repository secret"**
   - **Name:** `COPILOT_TOKEN`
   - **Value:** Paste your token
   - Click **"Add secret"**

### 📱 Optional: Telegram Notifications

To receive notifications when weekly plans are generated:

1. **Create a Telegram Bot:**
   - Open Telegram and search for `@BotFather`
   - Send `/newbot` and follow instructions
   - Copy the bot token

2. **Get Your Chat ID:**
   - Send a message to your new bot
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Find your `chat_id` in the JSON response

3. **Add Secrets:**
   - `TELEGRAM_BOT_TOKEN` - Your bot token
   - `TELEGRAM_CHAT_ID` - Your chat ID

---

## 5️⃣ Enable Workflow Permissions

GitHub Actions needs permission to create pull requests for the iOS Shortcut workflow.

1. Go to **Your repo** > **Settings** > **Actions** > **General**
2. Scroll down to **Workflow permissions**
3. Select **"Read and write permissions"**
4. Enable **"Allow GitHub Actions to create and approve pull requests"**
5. Click **Save**

Without this, workout uploads via iOS Shortcut will fail when trying to create a PR.

---

## 6️⃣ Test the Setup

### Test Workflow

1. Go to **Actions** tab in your repository
2. Select **"Generate Weekly Training Plan"**
3. Click **"Run workflow"** > **"Run workflow"**
4. Wait for completion (~30-60 seconds)
5. Check if a new plan was created in `plans/YYYY/MM/week-YYYY-MM-DD.md`

### Test Locally (Optional)

```bash
# Validate your configuration
python3 scripts/validate_config.py

# Generate the prompt (preview what Copilot receives)
python3 scripts/generate_weekly_plan_prompt.py

# Run all tests
python3 -m pytest tests/ -v
```

---

## 7️⃣ Add Your First Workout

1. Export a `.fit` file from your Apple Watch
2. Add it to `workouts/fit/` folder
3. Commit and push to `main`
4. GitHub Actions automatically:
   - Generates workout analysis
   - Updates `workouts/index.md`
   - Commits changes

---

## ✅ Verification Checklist

- [ ] Repository forked and cloned
- [ ] `config/config.yaml` updated with personal information
- [ ] Goal file created/updated in `config/goals/`
- [ ] `COPILOT_TOKEN` secret configured
- [ ] Python dependencies installed (if running locally)
- [ ] Test workflow ran successfully
- [ ] At least one `.fit` file added to `workouts/fit/`
- [ ] (Optional) Telegram secrets configured

---

## 📖 Next Steps

- **[Usage Guide](USAGE.md)** - Day-to-day usage
- **[Architecture](ARCHITECTURE.md)** - How it works under the hood
