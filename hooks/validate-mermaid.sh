#!/bin/bash
# PostToolUse hook: Validate Mermaid diagram syntax after Write/Edit
# Blocking: in hook mode, errors go to stderr and the script exits 2 so
# Claude Code feeds them back to the model for self-correction.
# In CLI mode (file paths as arguments), failures exit 1.

validate_file() {
  FILE_PATH="$1"

  # Only validate markdown files
  case "$FILE_PATH" in *.md|*.markdown) ;; *) return 0 ;; esac

  # File must exist
  [ -f "$FILE_PATH" ] || return 0

  # Extract mermaid blocks
  MERMAID_BLOCKS=$(awk '/^```mermaid$/,/^```$/' "$FILE_PATH" | grep -v '^```')

  # No mermaid blocks -- nothing to validate
  [ -z "$MERMAID_BLOCKS" ] && return 0

  # Lightweight structural validation
  ERRORS=""
  BLOCK_NUM=0

  while IFS= read -r -d $'\001' block; do
    BLOCK_NUM=$((BLOCK_NUM + 1))
    FIRST_LINE=$(echo "$block" | grep -m1 '[a-zA-Z]')
    if [ -n "$FIRST_LINE" ]; then
      if ! echo "$FIRST_LINE" | grep -qiE '^\s*(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|journey|gantt|pie|quadrantChart|requirementDiagram|gitGraph|C4Context|mindmap|timeline|sankey|xychart|block-beta|packet-beta|kanban|architecture-beta)\b'; then
        ERRORS="${ERRORS}Block $BLOCK_NUM: Unknown diagram type: $(echo "$FIRST_LINE" | head -c 60)\n"
      fi
    else
      ERRORS="${ERRORS}Block $BLOCK_NUM: Empty mermaid block\n"
    fi

    # Check for unbalanced brackets.
    # Strip double-quoted label content first: brackets/parens inside quoted
    # labels (e.g. A["決済 (カード)"]) are legal and must not be counted.
    STRIPPED=$(echo "$block" | sed 's/"[^"]*"//g')
    # Strip erDiagram relationship cardinality markers (e.g. ||--o{, }o--o{, }|..|{)
    # whose braces are relationship syntax, not block delimiters. Attribute-block
    # braces (CUSTOMER { ... }) are preceded by a name/space and stay counted.
    STRIPPED=$(echo "$STRIPPED" | sed -E 's/[.o|-]\{//g; s/\}[o|]//g')
    OPEN_PARENS=$(echo "$STRIPPED" | tr -cd '(' | wc -c | tr -d ' ')
    CLOSE_PARENS=$(echo "$STRIPPED" | tr -cd ')' | wc -c | tr -d ' ')
    OPEN_BRACKETS=$(echo "$STRIPPED" | tr -cd '[' | wc -c | tr -d ' ')
    CLOSE_BRACKETS=$(echo "$STRIPPED" | tr -cd ']' | wc -c | tr -d ' ')
    OPEN_BRACES=$(echo "$STRIPPED" | tr -cd '{' | wc -c | tr -d ' ')
    CLOSE_BRACES=$(echo "$STRIPPED" | tr -cd '}' | wc -c | tr -d ' ')

    [ "$OPEN_PARENS" -ne "$CLOSE_PARENS" ] && \
      ERRORS="${ERRORS}Block $BLOCK_NUM: Unbalanced parentheses ($OPEN_PARENS open, $CLOSE_PARENS close)\n"
    [ "$OPEN_BRACKETS" -ne "$CLOSE_BRACKETS" ] && \
      ERRORS="${ERRORS}Block $BLOCK_NUM: Unbalanced brackets ($OPEN_BRACKETS open, $CLOSE_BRACKETS close)\n"
    [ "$OPEN_BRACES" -ne "$CLOSE_BRACES" ] && \
      ERRORS="${ERRORS}Block $BLOCK_NUM: Unbalanced braces ($OPEN_BRACES open, $CLOSE_BRACES close)\n"

  done < <(awk '/^```mermaid$/{found=1; block=""; next} /^```$/{if(found){printf "%s\001", block; found=0} next} found{block=block (block?"\n":"") $0}' "$FILE_PATH")

  if [ -n "$ERRORS" ]; then
    echo "MERMAID VALIDATION ERRORS in $FILE_PATH:" >&2
    printf "$ERRORS" >&2
    echo "Fix the mermaid syntax before proceeding." >&2
    return 1
  fi

  return 0
}

if [ "$#" -gt 0 ]; then
  STATUS=0
  for FILE_PATH in "$@"; do
    validate_file "$FILE_PATH" || STATUS=1
  done
  exit "$STATUS"
fi

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only run for Write/Edit tools when invoked as a Claude Code hook
case "$TOOL_NAME" in Write|Edit|MultiEdit) ;; *) exit 0 ;; esac

# Exit 2 so Claude Code treats this as blocking feedback (stderr is fed
# back to the model); exit 1 would only be shown to the user.
validate_file "$FILE_PATH" || exit 2
exit 0
