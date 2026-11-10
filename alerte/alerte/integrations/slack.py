"""Post a short drill summary to the team's Slack channel (free incoming webhook).

Setup (2 minutes): in Slack, create an app at https://api.slack.com/apps, enable
"Incoming Webhooks", add one to your channel (for example #dev-agents), and put the
URL in .env as ALERTE_SLACK_WEBHOOK_URL. Nothing is sent if the variable is empty.
No personal data is ever sent: only counts and gap titles from the fictional drill.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from alerte import config
from alerte.net import HttpError, post_json

log = logging.getLogger(__name__)


def notify_run(summary: dict[str, Any], run_dir: Path) -> bool:
    url = config.settings.slack_webhook_url
    if not url:
        return False
    cov = summary.get("expected_gap_coverage", {})
    cit = summary.get("citations", {})
    text = (f":rotating_light: *ALERTE drill finished* `{Path(run_dir).name}`\n"
            f"*{summary.get('title')}* ({summary.get('country')}), brain: {summary.get('brain', {}).get('model') or summary.get('brain', {}).get('brain')}\n"
            f"Gaps: *{summary.get('gaps')}* ({summary.get('confirmed_gaps')} confirmed) · planned gaps found: "
            f"{cov.get('found')}/{cov.get('expected')} · quotes verified: {cit.get('verified')}/{cit.get('citations')} · "
            f"{summary.get('seconds')} s · logbook: {summary.get('ledger', {}).get('message', 'see run folder')}")
    try:
        post_json(url, {"text": text}, timeout=10)
        return True
    except HttpError as e:
        log.warning("Slack notification failed: %s", e)
        return False


def post_message(text: str) -> bool:
    url = config.settings.slack_webhook_url
    if not url:
        return False
    try:
        post_json(url, {"text": text}, timeout=10)
        return True
    except HttpError as e:
        log.warning("Slack notification failed: %s", e)
        return False
