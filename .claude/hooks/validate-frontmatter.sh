#!/bin/bash
# PostToolUse hook: Validate YAML frontmatter in output files
# Blocking: non-zero exit feeds error back to Claude for self-correction

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only run for Write/Edit tools
case "$TOOL_NAME" in Write|Edit|MultiEdit) ;; *) exit 0 ;; esac

# Only validate markdown files in reports/ directory
case "$FILE_PATH" in */reports/*.md) ;; *) exit 0 ;; esac

# File must exist
[ -f "$FILE_PATH" ] || exit 0

# Check if file starts with frontmatter delimiter
FIRST_LINE=$(head -1 "$FILE_PATH")
[ "$FIRST_LINE" != "---" ] && {
  echo "FRONTMATTER ERROR in $FILE_PATH:"
  echo "  Output files in reports/ must start with YAML frontmatter (---)"
  exit 1
}

# Extract frontmatter
FRONTMATTER=$(awk 'NR==1 && /^---$/{found=1; next} found && /^---$/{exit} found{print}' "$FILE_PATH")

if [ -z "$FRONTMATTER" ]; then
  echo "FRONTMATTER ERROR in $FILE_PATH:"
  echo "  File starts with '---' but no closing '---' found."
  exit 1
fi

# Check closing delimiter
HAS_CLOSING=$(awk 'NR==1 && /^---$/{found=1; next} found && /^---$/{print "yes"; exit}' "$FILE_PATH")
if [ "$HAS_CLOSING" != "yes" ]; then
  echo "FRONTMATTER ERROR in $FILE_PATH:"
  echo "  Unclosed frontmatter block. Missing closing '---'."
  exit 1
fi

# Validate YAML syntax
if command -v python3 &>/dev/null; then
  YAML_ERROR=$(python3 -c "
import sys, yaml
try:
    data = yaml.safe_load(sys.stdin.read())
    if data is None:
        print('Empty frontmatter')
        sys.exit(1)
    if not isinstance(data, dict):
        print('Frontmatter must be a YAML mapping, got: ' + type(data).__name__)
        sys.exit(1)
    # Check required fields for report files
    required = ['title', 'schema_version', 'skill']
    missing = [f for f in required if f not in data]
    if missing:
        print('Missing required fields: ' + ', '.join(missing))
        sys.exit(1)
except yaml.YAMLError as e:
    print(str(e))
    sys.exit(1)
" <<< "$FRONTMATTER" 2>&1)
  if [ $? -ne 0 ]; then
    echo "FRONTMATTER VALIDATION ERROR in $FILE_PATH:"
    echo "  $YAML_ERROR"
    exit 1
  fi
fi

exit 0
