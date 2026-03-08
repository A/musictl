#!/usr/bin/env bash
set -euo pipefail

# Generate release notes from a pre-generated changelog.
# Outputs to stdout.
# - If ANTHROPIC_API_KEY is set: AI-enhanced user-friendly notes
# - Otherwise: Use the changelog as-is

CHANGELOG="${1:-}"
if [[ -z "$CHANGELOG" ]]; then
  echo "Usage: $0 <changelog-content>" >&2
  exit 1
fi

TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

TECHNICAL="$TEMP_DIR/technical.md"
echo "$CHANGELOG" > "$TECHNICAL"

# If no API key, just output technical notes
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "No ANTHROPIC_API_KEY set, using technical changelog" >&2
  cat "$TECHNICAL"
  exit 0
fi

# AI enhancement
echo "Enhancing with Claude API..." >&2

read -r -d '' PROMPT << 'EOF' || true
You are a technical writer creating user-friendly release notes for musictl, a music control CLI for MPD + beets.

Transform the technical changelog below into concise, scannable release notes.

# Output Format

Start with a one-line summary of the main theme, then organize into sections (only include sections that have content):

### New Features
List user-facing features. Each should be 1-2 sentences max focusing on what the user can now do.

### Bug Fixes
List fixes users would notice. Be specific about what was broken and is now fixed.

### Changes
Notable changes in behavior or workflow.

### Upgrade Notes
- State if there are breaking changes (look for "breaking" or "remove" in changelog)
- If no breaking changes, say "No breaking changes."
- If breaking changes exist, list migration steps

---

<details>
<summary>Technical Details</summary>

[Include the full technical changelog here, unchanged]

</details>

# Rules
- Write for CLI users, not library consumers
- Use present tense, active voice
- Be specific (not "improved playback" but "random mode now works without a playlist")
- Skip purely internal changes from main sections (put only in Technical Details)
- Be concise
- No emojis

# Technical Changelog to Transform

EOF

# Combine prompt with technical changelog
FULL_PROMPT="$PROMPT

$(cat "$TECHNICAL")"

# Call Claude API
RESPONSE=$(curl -s https://api.anthropic.com/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d "$(jq -n \
    --arg prompt "$FULL_PROMPT" \
    '{
      model: "claude-sonnet-4-20250514",
      max_tokens: 4096,
      messages: [
        {
          role: "user",
          content: $prompt
        }
      ]
    }')")

# Extract content
AI_NOTES=$(echo "$RESPONSE" | jq -r '.content[0].text' 2>/dev/null || echo "")

if [[ -z "$AI_NOTES" || "$AI_NOTES" == "null" ]]; then
  echo "AI enhancement failed, falling back to technical notes" >&2
  echo "Response: $RESPONSE" >&2
  cat "$TECHNICAL"
  exit 0
fi

echo "Release notes generated!" >&2
echo "$AI_NOTES"
