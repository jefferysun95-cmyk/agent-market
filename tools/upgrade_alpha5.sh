#!/usr/bin/env bash
# Ubuntu single-service upgrade. Expected commit must come from the release record.
set -Eeuo pipefail
umask 022
ROOT=/opt/agent-market-1.1.0-alpha.5
DB=/var/lib/agent-market/market.db
DROPIN=/etc/systemd/system/agent-market.service.d/50-alpha5.conf
MAILENV=/etc/agent-market-registration-alpha5.env
ZONE=/etc/nginx/conf.d/agent-market-alpha5-rate.conf
SITE=/etc/nginx/sites-available/agent-market
PY="$ROOT/.venv/bin/python"
MODE="${1:-}"
MAILJSON="${2:-$HOME/agent-market-private/registration-test-zoho-api.json}"
: "${EXPECTED_COMMIT:?Set EXPECTED_COMMIT to the reviewed release commit}"
[[ "$EXPECTED_COMMIT" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid expected commit'; exit 1; }
[[ "$MODE" == prepare || "$MODE" == activate ]] || { echo 'Usage: prepare | activate [private-mail-json]'; exit 1; }
[[ ! -L "$ROOT" ]] || { echo 'Source target is a symlink; stop'; exit 1; }

if [[ "$MODE" == prepare ]]; then
  if [[ ! -e "$ROOT" ]]; then
    sudo install -d -m 755 -o "$(id -un)" -g "$(id -gn)" "$ROOT"
    git clone --depth 1 --branch v1.1.0-alpha.5 https://github.com/jefferysun95-cmyk/agent-market.git "$ROOT"
  fi
  [[ "$(git -C "$ROOT" rev-parse HEAD)" == "$EXPECTED_COMMIT" ]] || { echo 'Source commit differs; stop'; exit 1; }
  [[ -z "$(git -C "$ROOT" status --porcelain)" ]] || { echo 'Source has edits; stop'; exit 1; }
  python3 -m venv "$ROOT/.venv"
  "$PY" -m pip install -r "$ROOT/requirements.txt"
  cd "$ROOT"
  env -u MARKET_DB -u MARKET_SELF_REGISTRATION "$PY" -m unittest discover -s tests -v
  env -u MARKET_DB -u MARKET_SELF_REGISTRATION "$PY" demo.py
  install -d -m 700 "$HOME/agent-market-private"
  echo 'PREPARE PASSED. Service not changed. Upload private API JSON, then activate.'
  exit 0
fi

[[ -x "$PY" && "$(git -C "$ROOT" rev-parse HEAD)" == "$EXPECTED_COMMIT" ]] || { echo 'Run prepare for the correct commit first'; exit 1; }
[[ -z "$(git -C "$ROOT" status --porcelain)" ]] || { echo 'Source has edits; stop'; exit 1; }
[[ -f "$MAILJSON" ]] || { echo 'Private API JSON missing; no change made'; exit 1; }
sudo test -f "$DB"
sudo test -f "$SITE"
[[ "$(readlink -f /etc/nginx/sites-enabled/agent-market)" == "$SITE" ]] || { echo 'Unexpected active Nginx site; review manually'; exit 1; }
for file in "$DROPIN" "$MAILENV" "$ZONE"; do
  if sudo test -e "$file"; then echo 'Alpha5 configuration already exists; stop rather than overwrite'; exit 1; fi
done
sudo systemctl is-active --quiet agent-market
BACKUP="/var/backups/agent-market/pre-alpha5-$(date -u +%Y%m%dT%H%M%SZ)"
sudo mkdir -m 700 "$BACKUP"
sudo cp -p /etc/agent-market.env "$BACKUP/operator.env"
sudo cp -p "$SITE" "$BACKUP/nginx-before.conf"
sudo sh -c 'umask 077; systemctl cat agent-market > "$1/service-before.txt"' sh "$BACKUP"
sudo "$PY" "$ROOT/tools/alpha5_deploy.py" mail-env "$MAILJSON" "$BACKUP/registration.env"
sudo "$PY" "$ROOT/tools/alpha5_deploy.py" nginx "$SITE" "$BACKUP/nginx-after.conf"

stopped=0; nginx_changed=0; zone_created=0; env_created=0; dropin_created=0
rollback() {
  trap - ERR
  set +e
  if [[ "$dropin_created" == 1 ]]; then sudo rm -f -- "$DROPIN"; fi
  if [[ "$env_created" == 1 ]]; then sudo rm -f -- "$MAILENV"; fi
  if [[ "$nginx_changed" == 1 ]]; then sudo cp -p "$BACKUP/nginx-before.conf" "$SITE"; fi
  if [[ "$zone_created" == 1 ]]; then sudo rm -f -- "$ZONE"; fi
  sudo systemctl daemon-reload
  if [[ "$stopped" == 1 ]]; then sudo systemctl restart agent-market; fi
  sudo nginx -t && sudo systemctl reload nginx
  echo "UPGRADE FAILED. Previous startup/site restored where possible; DB retained. Private backup: $BACKUP"
  exit 1
}
trap rollback ERR
sudo systemctl stop agent-market; stopped=1
sudo "$PY" "$ROOT/manage.py" --db "$DB" backup "$BACKUP/market.db"
sudo "$PY" "$ROOT/tools/alpha5_deploy.py" snapshot "$DB" "$BACKUP/records-before.json"
sudo install -m 600 "$BACKUP/registration.env" "$MAILENV"; env_created=1
sudo install -m 644 "$BACKUP/nginx-after.conf" "$SITE"; nginx_changed=1
printf '%s\n' 'limit_req_zone $binary_remote_addr zone=market_alpha5:10m rate=10r/s;' | sudo tee "$ZONE" >/dev/null
zone_created=1
sudo nginx -t
sudo systemctl reload nginx
sudo install -d -m 755 /etc/systemd/system/agent-market.service.d
sudo tee "$DROPIN" >/dev/null <<'EOF'
[Service]
WorkingDirectory=/opt/agent-market-1.1.0-alpha.5
Environment=MARKET_DB=/var/lib/agent-market/market.db
EnvironmentFile=/etc/agent-market-registration-alpha5.env
ExecStart=
ExecStart=/opt/agent-market-1.1.0-alpha.5/.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8787 --workers 1 --no-access-log --proxy-headers --forwarded-allow-ips=127.0.0.1
ReadWritePaths=/var/lib/agent-market
EOF
dropin_created=1
sudo systemctl daemon-reload
sudo systemctl start agent-market
ready=0
for attempt in $(seq 1 20); do
  if curl -fsS --max-time 5 http://127.0.0.1:8787/health > /dev/null; then ready=1; break; fi
  sleep 1
done
[[ "$ready" == 1 ]]
curl -fsS --max-time 15 https://api.digolives.com/health | "$PY" -c 'import sys,json; d=json.load(sys.stdin); assert d.get("ok") and d.get("version")=="1.1.0-alpha.5" and d.get("self_registration") is True; print("Alpha5 health and registration enabled: PASS")'
sudo "$PY" "$ROOT/tools/alpha5_deploy.py" verify "$DB" "$BACKUP/records-before.json"
[[ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 https://api.digolives.com/me)" == 401 ]]
[[ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 -X POST https://api.digolives.com/mcp -H 'Content-Type: application/json' -d '{}')" == 401 ]]
sudo systemctl is-active --quiet agent-market
trap - ERR
echo "UPGRADE PASSED. Alpha5 enabled; previous identities/orders preserved. Private backup: $BACKUP"
echo 'Next: external new-user registration/doctor check. No test email or fake payment was sent by this script.'
