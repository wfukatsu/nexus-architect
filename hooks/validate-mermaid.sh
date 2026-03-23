#!/bin/bash
# PostToolUse hook: Validate Mermaid diagram syntax after Write/Edit
# Blocking: non-zero exit feeds error back to Claude for self-correction

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only run for Write/Edit tools
case "$TOOL_NAME" in Write|Edit|MultiEdit) ;; *) exit 0 ;; esac

# Only validate markdown files
case "$FILE_PATH" in *.md|*.markdown) ;; *) exit 0 ;; esac

# File must exist
[ -f "$FILE_PATH" ] || exit 0

# Extract mermaid blocks
MERMAID_BLOCKS=$(awk '/^```mermaid$/,/^```$/' "$FILE_PATH" | grep -v '^```')

# No mermaid blocks -- nothing to validate
[ -z "$MERMAID_BLOCKS" ] && exit 0

# Lightweight structural validation
ERRORS=""
BLOCK_NUM=0

while IFS= read -r block; do
  BLOCK_NUM=$((BLOCK_NUM + 1))
  FIRST_LINE=$(echo "$block" | grep -m1 '[a-zA-Z]')
  if [ -n "$FIRST_LINE" ]; then
    if ! echo "$FIRST_LINE" | grep -qiE '^\s*(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|journey|gantt|pie|quadrantChart|requirementDiagram|gitGraph|C4Context|mindmap|timeline|sankey|xychart|block-beta|packet-beta|kanban|architecture-beta)\b'; then
      ERRORS="${ERRORS}Block $BLOCK_NUM: Unknown diagram type: $(echo "$FIRST_LINE" | head -c 60)\n"
    fi
  else
    ERRORS="${ERRORS}Block $BLOCK_NUM: Empty mermaid block\n"
  fi

  # Check for unbalanced brackets
  OPEN_PARENS=$(echo "$block" | tr -cd '(' | wc -c | tr -d ' ')
  CLOSE_PARENS=$(echo "$block" | tr -cd ')' | wc -c | tr -d ' ')
  OPEN_BRACKETS=$(echo "$block" | tr -cd '[' | wc -c | tr -d ' ')
  CLOSE_BRACKETS=$(echo "$block" | tr -cd ']' | wc -c | tr -d ' ')
  OPEN_BRACES=$(echo "$block" | tr -cd '{' | wc -c | tr -d ' ')
  CLOSE_BRACES=$(echo "$block" | tr -cd '}' | wc -c | tr -d ' ')

  [ "$OPEN_PARENS" -ne "$CLOSE_PARENS" ] && \
    ERRORS="${ERRORS}Block $BLOCK_NUM: Unbalanced parentheses ($OPEN_PARENS open, $CLOSE_PARENS close)\n"
  [ "$OPEN_BRACKETS" -ne "$CLOSE_BRACKETS" ] && \
    ERRORS="${ERRORS}Block $BLOCK_NUM: Unbalanced brackets ($OPEN_BRACKETS open, $CLOSE_BRACKETS close)\n"
  [ "$OPEN_BRACES" -ne "$CLOSE_BRACES" ] && \
    ERRORS="${ERRORS}Block $BLOCK_NUM: Unbalanced braces ($OPEN_BRACES open, $CLOSE_BRACES close)\n"

done < <(awk '/^```mermaid$/{found=1; block=""; next} /^```$/{if(found){print block; found=0} next} found{block=block (block?"\n":"") $0}' "$FILE_PATH")

if [ -n "$ERRORS" ]; then
  echo "MERMAID VALIDATION ERRORS in $FILE_PATH:"
  printf "$ERRORS"
  echo "Fix the mermaid syntax before proceeding."
  exit 1
fi

exit 0
