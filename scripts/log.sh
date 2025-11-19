#!/bin/bash
set -euxo pipefail

WEBHOOK_URL="${SLACK_WEBHOOK_URL:?SLACK_WEBHOOK_URL is not set}"

curl -X POST \
  --data-urlencode "payload={\"channel\": \"#notify-lab\", \"username\": \"webhookbot\", \"text\": \"${1:-notification}\", \"icon_emoji\": \":ghost:\"}" \
  "$WEBHOOK_URL"
