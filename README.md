# K4L1R00TB00
# KaliRootBot

This repository contains the backend for a Telegram bot that integrates with Supabase and Groq.

Quick start (local development):

1. Copy the example env file and fill secrets:

```bash
cp .env.example .env
# Edit .env to add your TELEGRAM_BOT_TOKEN, SUPABASE keys, GROQ key and other variables
```

2. Create and activate a Python virtualenv and install dependencies:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Run the bot in polling mode for development:

```bash
python run_polling.py
```

Detailed setup and deployment instructions are in `README_SUPABASE.md` (includes supabase migrations, webhook vs polling, and deploy notes).

Bot messaging format (HTML)
---------------------------
The bot now formats AI responses as HTML using only tags compatible with Telegram such as `<code>`, `<pre>`, and `<b>` for emphasis. This helps present commands and code snippets in a readable way in Telegram messages.

- Markdown styles (like `*italic*` or `_italic_`) are stripped so replies are consistent; use `**bold**` in prompts if you intend emphasis and the bot will convert it to HTML `<b>` for the final message.
- The bot uses a professional tone; emojis have been removed from automated replies and fields are shown with minimal emphasis using `<b>` only.

If you echo or print messages in your code or tests, make sure to pass `parse_mode=ParseMode.HTML` to the `reply_text` or `send_message` calls (the bot is already updated to do this).

Resolving "terminated by other getUpdates request" / Conflict error
----------------------------------------------------------------
If you see an error like:

```
telegram.error.Conflict: Conflict: terminated by other getUpdates request; make sure that only one bot instance is running
```

It means that your bot is receiving updates by webhook or another polling process is already retrieving updates. Telegram does not allow multiple `getUpdates` polling clients for the same bot token while a webhook is set or another `getUpdates` is running.

Quick debugging commands:

```bash
# Show current webhook info (returns url if set)
curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo" | jq

# Remove webhook (server will stop posting updates and getUpdates/polling can run)
curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/deleteWebhook?drop_pending_updates=true" | jq

# Check for running processes that might be using your bot token
ps aux | grep run_polling.py
ps aux | grep main.py

# Kill a process PID (replace <PID> with actual process id)
kill <PID>
```

Notes and recommendations:
- If you deploy to a hosting environment that uses webhooks (e.g., Render, Fly, Heroku), use webhooks instead of polling and set `TELEGRAM_WEBHOOK_URL`.
- For development, polling is often more convenient: set `TELEGRAM_WEBHOOK_URL` empty and run `python run_polling.py`.
- The project includes a setting `DELETE_WEBHOOK_ON_POLLING` in `config.py`/.env which will attempt to delete the webhook automatically when running `run_polling.py` (helpful in development). Use it carefully to avoid unintended webhook deletion in production.

Groq model errors: "model does not exist" or access denied
---------------------------------------------------------
If you see errors like:

```
groq.NotFoundError: Error code: 404 - {'error': {'message': 'The model `embed-english-3.0` does not exist or you do not have access to it.'}}
```

Then the configured embedding model doesn't exist for your account or your `GROQ_API_KEY` doesn't have access.

How to troubleshoot:

1. Verify your `GROQ_API_KEY` is correct and has permissions.
2. List available models for your account (example script included):
```bash
python groq_model_list.py
```
3. Choose a model ID from that list with an `embed` name (or that supports embeddings) and set it in `.env`:
```bash
export GROQ_EMBEDDING_MODEL="<model-id-from-list>"
```
4. Restart the service after setting the variable.

Implementation note: the bot now tries to auto-detect a suitable embeddings model if `GROQ_EMBEDDING_MODEL` is not set; however, auto-detection depends on the models list available to your API key and will log a message if no embedding model is available.

Emoji support
-------------
The bot also uses emojis to make replies more human-friendly. Examples include:

- ✅ for successful actions (welcome)
- 🔄 for processing
- 💳 or 💰 for purchases and balance
- 🚨 or ❌ for errors

The AI response is prefixed with a small emoji (🤖) to indicate a generated reply.

---

Manual deploy (Render)
----------------------
This repository has been configured to do manual deploys to Render. We archived CI workflows (they are no longer auto-run on push/PR). To deploy manually:

1. Push the branch/tag you want to GitHub.
2. Open Render dashboard and select your service.
3. Ensure Auto-Deploy is turned off.
4. Click 'Manual Deploy' -> 'Deploy Latest' (or similar) to deploy from the latest commit.
5. Ensure environment variables under 'Environment' are set (TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_URL, TELEGRAM_WEBHOOK_SECRET, SUPABASE keys, GROQ_API_KEY, etc.).

If you want to re-enable CI or GitHub-based deploys later, we can restore or add a CI job to only deploy on tags.

