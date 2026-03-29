#!/usr/bin/env python3
"""Red Alert OSINT Notifier — unified notification and intelligence module.

Monitors multiple sources for missile launch alerts and volumetric
nationwide alert thresholds, delivers Pushover notifications, and
generates Groq-powered intelligence reports for Jerusalem events.

Sources:
  1. Telegram @manniefabian (English) — ballistic missile launch reports
     Credit: Emanuel (Mannie) Fabian, Times of Israel military correspondent
     https://www.timesofisrael.com/writers/emanuel-fabian/
  2. Telegram @news0404il (Hebrew) — שיגור (launch) reports
  3. Oref Alert Proxy — volumetric nationwide alert thresholds
  4. Groq OSINT — immediate intel report on Jerusalem missile events
"""

import asyncio
import logging
import os
import sys

from classifiers import classify_en, classify_he
from intel import generate_intel_report
from notifier import send_pushover
from oref_monitor import oref_poll_loop
from telegram_monitor import ChannelMessage, ChannelPoller

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("osint-notifier")

# ── Configuration (all from env) ────────────────────────────────────────────

PUSHOVER_APP_TOKEN = os.environ.get("PUSHOVER_APP_TOKEN", "")
PUSHOVER_GROUP_KEY = os.environ.get("PUSHOVER_GROUP_KEY", "")

TELEGRAM_CHANNEL_EN = os.environ.get("TELEGRAM_CHANNEL_EN", "manniefabian")
TELEGRAM_CHANNEL_HE = os.environ.get("TELEGRAM_CHANNEL_HE", "news0404il")
TELEGRAM_POLL_INTERVAL = int(os.environ.get("TELEGRAM_POLL_INTERVAL", "15"))

OREF_ENABLED = os.environ.get("OREF_ENABLED", "true").lower() in ("true", "1", "yes")
OREF_PROXY_URL = os.environ.get("OREF_PROXY_URL", "http://host.docker.internal:8764/api/alerts")
OREF_POLL_INTERVAL = int(os.environ.get("OREF_POLL_INTERVAL", "3"))
OREF_AREA_THRESHOLDS = sorted(
    int(t) for t in os.environ.get(
        "OREF_AREA_THRESHOLDS", "50,100,200,300,400,500,600,700,800,900,1000"
    ).split(",") if t.strip()
)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


# ── Notification helpers ────────────────────────────────────────────────────

async def notify_missile(source: str, text: str, jerusalem: bool):
    """Send missile launch Pushover alert + optional intel report."""
    if jerusalem:
        title = "MISSILE ALERT — JERUSALEM"
        priority = 2
        sound = "alien"
    else:
        title = "MISSILE LAUNCH DETECTED"
        priority = 1
        sound = "siren"

    body = f"<b>Source: {source}</b>\n\n{text}"
    await send_pushover(PUSHOVER_APP_TOKEN, PUSHOVER_GROUP_KEY, title, body, priority, sound)

    # Trigger Groq intel report for Jerusalem events
    if jerusalem:
        report = await generate_intel_report(text, source, GROQ_API_KEY, GROQ_MODEL)
        if report:
            await send_pushover(
                PUSHOVER_APP_TOKEN, PUSHOVER_GROUP_KEY,
                "INTEL REPORT — Jerusalem Missile Event",
                report,
                priority=1,
                sound="pushover",
            )


async def notify_volumetric(active_count: int, threshold: int):
    """Send Oref volumetric threshold Pushover alert."""
    await send_pushover(
        PUSHOVER_APP_TOKEN, PUSHOVER_GROUP_KEY,
        f"Red Alert: {active_count} Areas Active",
        f"Nationwide alert count has crossed {threshold} areas across Israel.",
        priority=0,
        sound="pushover",
    )


# ── Telegram channel handlers ──────────────────────────────────────────────

async def handle_en(msg: ChannelMessage):
    if len(msg.text.strip()) < 10:
        return
    log.info("EN [%s]: %s", msg.msg_id, msg.text[:120])
    result = classify_en(msg.text)
    log.info("EN classification: %s", result)
    if result["missile_launch"]:
        await notify_missile("Mannie Fabian (@manniefabian)", msg.text, result["jerusalem_targeted"])


async def handle_he(msg: ChannelMessage):
    if len(msg.text.strip()) < 10:
        return
    log.info("HE [%s]: %s", msg.msg_id, msg.text[:120])
    result = classify_he(msg.text)
    log.info("HE classification: %s", result)
    if result["missile_launch"]:
        await notify_missile("חדשות 0404 (@news0404il)", msg.text, result["jerusalem_targeted"])


# ── Poll loops ──────────────────────────────────────────────────────────────

async def telegram_poll_loop(poller: ChannelPoller, handler):
    poller.seed()
    log.info("Polling @%s every %ds", poller.channel, TELEGRAM_POLL_INTERVAL)
    while True:
        for msg in poller.poll_once():
            try:
                await handler(msg)
            except Exception:
                log.exception("Handler failed for %s", msg.msg_id)
        await asyncio.sleep(TELEGRAM_POLL_INTERVAL)


# ── Main ────────────────────────────────────────────────────────────────────

async def run():
    log.info("Starting Red Alert OSINT Notifier")

    if not PUSHOVER_APP_TOKEN or not PUSHOVER_GROUP_KEY:
        log.error("PUSHOVER_APP_TOKEN and PUSHOVER_GROUP_KEY are required. Exiting.")
        sys.exit(1)

    tasks = []

    if TELEGRAM_CHANNEL_EN:
        log.info("EN channel: @%s", TELEGRAM_CHANNEL_EN)
        poller_en = ChannelPoller(TELEGRAM_CHANNEL_EN)
        tasks.append(telegram_poll_loop(poller_en, handle_en))

    if TELEGRAM_CHANNEL_HE:
        log.info("HE channel: @%s", TELEGRAM_CHANNEL_HE)
        poller_he = ChannelPoller(TELEGRAM_CHANNEL_HE)
        tasks.append(telegram_poll_loop(poller_he, handle_he))

    if OREF_ENABLED:
        log.info("Oref volumetric: %s", OREF_PROXY_URL)
        tasks.append(oref_poll_loop(
            OREF_PROXY_URL, OREF_POLL_INTERVAL, OREF_AREA_THRESHOLDS, notify_volumetric,
        ))

    if GROQ_API_KEY:
        log.info("Groq OSINT intel: enabled (model=%s)", GROQ_MODEL)
    else:
        log.info("Groq OSINT intel: disabled (no GROQ_API_KEY)")

    if not tasks:
        log.error("No alert sources enabled. Exiting.")
        sys.exit(1)

    await asyncio.gather(*tasks)


def main():
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        log.info("Shutting down.")


if __name__ == "__main__":
    main()
