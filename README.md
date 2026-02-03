# Don-Scrapiovanni 🎭

Monitor Wiener Staatsoper website for ticket availability and get Telegram notifications. This scraper helps monitor the website and sends a notification via Telegram once a day at 09:30 AM, so members of the (Junger) Freundeskreis can buy tickets.

## Features

- 🎭 Monitors Wiener Staatsoper ticket availability
- ⏰ Runs automatically once daily at 09:30 AM Austria time (CET/CEST) with random ±2 minute offset
- 🔔 Sends Telegram notifications when tickets are available
- 🌍 Timezone-aware (handles CET/CEST transitions automatically)
- 🎯 Checks for tomorrow's show specifically
- 🎫 Shows available ticket categories in notifications
- 🤖 Uses Selenium for dynamic content loading

## How It Works

1. **Schedule**: The scraper runs once daily at 09:30 AM Austria time (with a random 0-4 minute delay)
2. **Target**: Checks `https://tickets.wiener-staatsoper.at/webshop/webticket/eventlist`
3. **Logic**:
   - Uses Selenium to load the page and handle JavaScript-rendered content
   - Handles inactivity pages and cookie consent automatically
   - Finds the show scheduled for tomorrow
   - Checks if tickets are available (supports both German and English website versions)
   - Navigates to the seat selection page to determine available categories
   - Sends Telegram notification with event details and available categories

## Prerequisites

- Docker and Docker Compose
- Telegram bot token and chat ID

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/benediktn-msft/Don-Scrapiovanni.git
cd Don-Scrapiovanni
```

### 2. Configure Environment Variables

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` and set:

```bash
# Required for Telegram notifications
TELEGRAM_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
```

#### Getting a Telegram Bot Token

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow the instructions
3. Copy the token you receive (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

#### Getting Your Telegram Chat ID

1. Send a message to your bot
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Look for `"chat":{"id":123456789}` in the response
4. Copy the ID number

### 3. Build and Run with Docker

```bash
# Build the scraper container
docker compose build

# Start the services
docker compose up -d

# Check logs
docker logs staatsoper-scraper -f
```

### 4. Verify It's Working

The scraper will automatically run at 09:30 AM Austria time. To verify:

```bash
# Check logs for scraper activity
docker logs staatsoper-scraper --tail 100
```

You should see messages like:

```
Starting Wiener Staatsoper Scraper...
Looking for tickets for: 19.01.2026
Found tickets: IDOMENEO at 18:30
Notification sent!
```

## Notification Format

When tickets are available, you'll receive a Telegram message like:

```
🎫 Tickets Available for Tomorrow (19.01.2026)!

• IDOMENEO
  📅 Mo. 19.01.2026 at 18:30
  Status: Tickets
  Available Category: 2
  Buy Tickets Here
```

If multiple categories are available:

```
🎫 Tickets Available for Tomorrow (19.01.2026)!

• IDOMENEO
  📅 Mo. 19.01.2026 at 18:30
  Status: Tickets
  Available Categories: 1, 2, 5
  Buy Tickets Here
```

## Configuration

### Schedule

The scraper runs at **09:30 AM Austria time** (Europe/Vienna timezone) with a random 0-4 minute delay to avoid running exactly at the same time every day.

To change the schedule, edit `scraper/scraper_staatsoper.py`:

```python
# Line ~181: Change the cron schedule
@bp.timer_trigger(schedule="0 30 9 * * *", arg_name="mytimer", run_on_startup=False)
```

### Timezone

The scraper uses `Europe/Vienna` timezone, which automatically handles:
- CET (Central European Time, UTC+1) in winter
- CEST (Central European Summer Time, UTC+2) in summer

## How Ticket Availability is Detected

The scraper uses Selenium to handle JavaScript-rendered content and detects ticket availability by:

1. **Loading the page** with Selenium (headless Chrome)
2. **Handling inactivity pages** - automatically clicks "Weiter" if needed
3. **Accepting cookie consent** - handles ccm19 cookie banners
4. **Finding events** - parses the event list for tomorrow's date
5. **Checking availability** - looks for:
   - German: "Weiterleitung zur Platzauswahl", "Karten", "Restkarten"
   - English: "Go to seat selection", "Tickets"
6. **Determining categories** - navigates to the seat selection page to check which categories (Kategorie 1, 2, etc.) are available

## Troubleshooting

### Scraper Not Running at 09:30

**Check timezone:**
```bash
docker exec staatsoper-scraper date
# Should show Austria time
```

**Check logs:**
```bash
docker logs staatsoper-scraper --tail 100
```

### No Notifications Received

1. **Check if tickets are actually available** - The scraper only notifies when tickets are available (not when sold out)

2. **Verify Telegram credentials:**
   ```bash
   # Check if environment variables are set
   docker exec staatsoper-scraper env | grep TELEGRAM
   ```

3. **Test Telegram bot manually:**
   ```bash
   curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/sendMessage" \
     -d "chat_id=<YOUR_CHAT_ID>" \
     -d "text=Test message"
   ```

4. **Check logs for errors:**
   ```bash
   docker logs staatsoper-scraper | tail -50
   ```

### Website Structure Changed

If the Wiener Staatsoper website changes its HTML structure, you may need to update the selectors in `scraper/scraper_staatsoper.py`. The scraper uses:
- BeautifulSoup for HTML parsing
- Selenium for dynamic content loading
- CSS selectors and XPath for element finding

**To update selectors:**

1. Visit `https://tickets.wiener-staatsoper.at/webshop/webticket/eventlist`
2. Open Developer Tools (F12)
3. Inspect the HTML structure
4. Update the selectors in the scraper code
5. Rebuild: `docker compose build --no-cache && docker compose restart staatsoper-scraper`

### No Events Found

If you see "No events found":

1. **Check if the website is accessible:**
   ```bash
   curl -I https://tickets.wiener-staatsoper.at/webshop/webticket/eventlist
   ```

2. **Check logs for parsing errors:**
   ```bash
   docker logs staatsoper-scraper | grep -i error
   ```

3. **Verify Selenium is working:**
   ```bash
   docker logs staatsoper-scraper | grep -i selenium
   ```

## Development

### Running Locally (without Docker)

1. Install dependencies:
   ```bash
   cd scraper
   pip install -r requirements.txt
   ```

2. Install Chrome/Chromium and chromedriver:
   ```bash
   # On Ubuntu/Debian
   sudo apt-get install chromium chromium-driver
   ```

3. Set environment variables:
   ```bash
   export TELEGRAM_TOKEN=your_token
   export TELEGRAM_CHAT_ID=your_chat_id
   ```

4. Run Azure Functions locally:
   ```bash
   func start
   ```

### Testing

To test the scraper manually, you can temporarily change the schedule:

```python
# In scraper_staatsoper.py, change:
@bp.timer_trigger(schedule="0 30 9 * * *", ...)

# To (runs every minute for testing):
@bp.timer_trigger(schedule="0 * * * * *", ...)
```

Then rebuild and restart:
```bash
docker compose build
docker compose restart staatsoper-scraper
```

## File Structure

```
Don-Scrapiovanni/
├── scraper/
│   ├── scraper_staatsoper.py        # Main scraper implementation
│   ├── function_app.py              # Registers the scraper
│   ├── requirements.txt             # Python dependencies
│   ├── Dockerfile                   # Docker build configuration
│   ├── host.json                    # Azure Functions configuration
│   └── .dockerignore                # Docker ignore file
├── docker-compose.yml               # Docker Compose configuration
├── .env.example                     # Environment variables template
├── .gitignore                       # Git ignore file
└── README.md                        # This file
```

## Dependencies

- **azure-functions**: Azure Functions runtime
- **requests**: HTTP requests
- **beautifulsoup4**: HTML parsing
- **pytz**: Timezone handling
- **selenium**: Browser automation for dynamic content
- **webdriver-manager**: Chrome driver management (optional, uses system chromium)

## Notes

- The scraper only checks for **tomorrow's** show, not all upcoming shows
- Notifications are only sent when tickets are **available** (not when sold out)
- The scraper runs once per day to avoid overloading the website
- Timezone handling is automatic (CET/CEST transitions)
- Uses headless Chrome via Selenium to handle JavaScript-rendered content
- Automatically handles inactivity pages and cookie consent

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review the logs: `docker logs staatsoper-scraper --tail 100`
3. Verify your environment variables are set correctly
4. Check if the website structure has changed

## Acknowledgments

- Built for monitoring Wiener Staatsoper ticket availability
- Uses Selenium for dynamic content handling
- Uses BeautifulSoup for HTML parsing
- Uses pytz for timezone handling
