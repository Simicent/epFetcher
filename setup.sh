#!/usr/bin/env bash
set -e

error_exit() {
    echo "Error: $1" >&2
    exit 1
}

# Resolve the directory where this script live
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="${1:-venv}"
PYTHON_BIN="$SCRIPT_DIR/$VENV_DIR/bin/python"
MAIN_SCRIPT="$SCRIPT_DIR/main.py"

# Check Python 3 is available
if ! command -v python3 &>/dev/null; then
    error_exit "Python 3 is not installed or not in PATH."
fi

# Create virtual environment
echo "Creating virtual environment in '$VENV_DIR'..."
python3 -m venv "$SCRIPT_DIR/$VENV_DIR" || error_exit "Failed to create virtual environment."

# Install dependencies
if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    echo "Installing dependencies..."
    "$SCRIPT_DIR/$VENV_DIR/bin/pip" install --upgrade pip
    "$SCRIPT_DIR/$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
    echo "Dependencies installed."
else
    error_exit "requirements.txt not found in $SCRIPT_DIR."
fi

# Validate main.py exists
if [ ! -f "$MAIN_SCRIPT" ]; then
    error_exit "main.py not found at $MAIN_SCRIPT."
fi

# Create .env if it doesn't exist
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "Creating .env from .env.example..."
    if [ -f "$SCRIPT_DIR/.env.example" ]; then
        cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
        echo ".env created — fill in your JELLYFIN_URL and JELLYFIN_TOKEN."
    else
        error_exit ".env and .env.example both missing. Cannot continue."
    fi
fi

# Set up cron job
CRON_CMD="* * * * * cd $SCRIPT_DIR && $PYTHON_BIN $MAIN_SCRIPT >> $SCRIPT_DIR/prefetch.log 2>&1"
TMP_CRON=$(mktemp)

crontab -l 2>/dev/null > "$TMP_CRON"

if grep -Fq "$MAIN_SCRIPT" "$TMP_CRON"; then
    echo "Cron job already exists, skipping."
else
    echo "$CRON_CMD" >> "$TMP_CRON"
    crontab "$TMP_CRON"
    echo "Cron job added (every minute)."
fi

rm -f "$TMP_CRON"

echo ""
echo "Setup complete. Edit $SCRIPT_DIR/.env before the cron job runs."