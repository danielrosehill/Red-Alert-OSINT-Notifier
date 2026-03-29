# Red Alert OSINT Notifier

Unified notification and OSINT intelligence module for Israel Red Alert monitoring. Monitors multiple sources for missile launch alerts and nationwide alert thresholds, delivers Pushover notifications, and generates AI-powered intelligence reports for Jerusalem-targeted events.

## Alert Sources

| Source | Type | Description |
|--------|------|-------------|
| `@manniefabian` | Telegram (EN) | Emanuel (Mannie) Fabian, [Times of Israel](https://www.timesofisrael.com/writers/emanuel-fabian/) military correspondent — reports ballistic missile launches often minutes before official sirens |
| `@news0404il` | Telegram (HE) | Hebrew news channel — שיגור (launch) reports with context keywords |
| Oref Alert Proxy | API | Volumetric nationwide alert thresholds (50, 100, 200... 1000 simultaneous areas) |
| Groq OSINT | AI/LLM | Immediate intelligence report on Jerusalem missile events — origin, munitions, scale (rate-limited to 1 per 10 min) |

## How It Works

1. **Telegram monitors** poll public channel web views every 15s for new messages
2. **Keyword classifiers** detect missile launches and Jerusalem targeting:
   - English: `ballistic missile` + `detected`/`identified`/`launch`/`sirens`
   - Hebrew: `שיגור` + `טיל בליסטי`/`טילים`/`איראן`/`אזעקות`
3. **Pushover alerts** fire with priority levels:
   - Emergency (P2) for Jerusalem-targeted missiles
   - High (P1) for other missile launches
   - Normal (P0) for volumetric threshold crossings
4. **Groq intel report** auto-generates on Jerusalem events with a 10-minute cooldown

## Deployment

```bash
cp .env.example .env
# Edit .env with your Pushover credentials and optional Groq key
docker compose up -d
```

### Requirements

- [Pushover](https://pushover.net/) account with app token and delivery group
- [Oref Alert Proxy](https://github.com/danielrosehill/Oref-Alert-Proxy) running (for volumetric alerts)
- [Groq API key](https://console.groq.com/) (optional, for intel reports)

### Integration with Red Alert Stack

This module is designed to run as a service within the [Red Alert Monitoring Stack](https://github.com/danielrosehill/Red-Alert-Monitoring-Stack-Public). Add it as a submodule or copy the service into your stack's `docker-compose.yml`.

## Customisation

### Adding Telegram channels

Add more channels by extending `main.py` with additional pollers and classifiers. Each channel needs:
1. A classifier function in `classifiers.py` (keyword patterns for your language/source)
2. A handler function in `main.py`
3. A `ChannelPoller` instance wired into the main loop

### Adjusting thresholds

Set `OREF_AREA_THRESHOLDS` in `.env` to your preferred comma-separated values.

### Changing the intel prompt

Edit the system/user prompts in `intel.py` to customise what the AI reports on.

## Credits

- **Emanuel (Mannie) Fabian** — Times of Israel military correspondent whose Telegram reporting is a key source for early missile launch alerts. [Profile](https://www.timesofisrael.com/writers/emanuel-fabian/)

## License

MIT
