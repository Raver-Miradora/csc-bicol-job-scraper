# Deployment Guide

This guide covers deployment instructions for setting up the CSC Bicol Job Scraper on a server for 24/7 monitoring.

*Note: Phase 14 will automate much of this via Docker, but manual deployment is possible today.*

## Option 1: Systemd Service (Linux/Ubuntu)

The most robust way to run the scraper on a standard Linux VPS is using a `systemd` service.

1. Clone the repository to `/opt/csc-bicol-job-scraper`
2. Run `python3 -m venv venv` and install dependencies.
3. Configure your `.env` and `config/config.yaml`.
4. Create the service file `/etc/systemd/system/csc-scraper.service`:

```ini
[Unit]
Description=CSC Bicol Job Scraper
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/opt/csc-bicol-job-scraper
ExecStart=/opt/csc-bicol-job-scraper/venv/bin/python main.py start
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

5. Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable csc-scraper
sudo systemctl start csc-scraper
```

6. Check the logs:
```bash
sudo journalctl -u csc-scraper -f
```
Or check the application's internal logs: `cat logs/tracker.log`

## Option 2: PM2 (Node.js Process Manager)

If you already use PM2 on your server, you can manage this Python script easily:

```bash
# Start the monitoring loop
pm2 start "python main.py start" --name "csc-scraper"

# Save the process list to start on boot
pm2 save
pm2 startup
```

## Option 3: Cron Job (Headless Run)

If you prefer to let Linux cron handle the scheduling rather than the internal `schedule` library:

1. Edit your crontab: `crontab -e`
2. Add a rule to run the script every hour:
```cron
0 * * * * cd /opt/csc-bicol-job-scraper && /opt/csc-bicol-job-scraper/venv/bin/python main.py check --notify >> logs/cron.log 2>&1
```

*Note: Using cron bypasses the internal loop, meaning you will need a separate cron job for the daily summary if you want one.*
