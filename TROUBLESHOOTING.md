# Troubleshooting Bot Connection Issues

## ❌ Error Analysis

Your logs show two distinct errors happening in sequence:

1.  **`TelegramConflictError`**:
    > `Conflict: terminated by other getUpdates request; make sure that only one bot instance is running`
    
    **Meaning**: Another instance of your bot is ALREADY running with the same Token. Telegram does not allow two bots to control the same account simultaneously using `getUpdates` (polling). When you start the second one, the first one fights for control, and Telegram terminates the connection.

2.  **`OSError: [Errno 101] Network is unreachable`** / **`ClientConnectorError`**:
    > `Cannot connect to host api.telegram.org:443`
    
    **Meaning**: The bot cannot reach Telegram's servers. This can happen if:
    *   The "Conflict" caused your IP to be temporarily rate-limited or blocked.
    *   You are on a server (like PythonAnywhere Free Tier) without the correct Proxy settings.
    *   The internet connection on the server dropped.

## ✅ Solution Steps

### 1. Stop External Instances (CRITICAL)
If you are running this on a cloud server (like PythonAnywhere):
*   **Check "Always-on tasks":** Go to the execution dashboard and **Delete** or **Stop** any task running your bot.
*   **Check open Consoles:** If you have other terminals/consoles open running the bot, close them or press `Ctrl + C` in them.
*   **Check Scheduled Tasks:** Ensure no scheduled task is launching the bot in the background.

**You cannot run the bot in the "Always-on" background AND testing it in the console at the same time.**

### 2. Check Proxy Settings (If on PythonAnywhere)
If you are using a PythonAnywhere **Free** account, you **MUST** use their proxy to connect to Telegram.

1.  Open your `.env` file.
2.  Ensure you have this exact line:
    ```ini
    PROXY=http://proxy.server:3128
    ```
3.  If this line is missing, your bot will fail to connect (except for lucky moments when the whitelist works).

### 3. Restart Properly
Once you have stopped all other instances:
1.  Wait 10-20 seconds for any connections to close.
2.  Run your bot again:
    ```bash
    python main.py
    ```
