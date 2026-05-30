#!/usr/bin/env python3
import os
import re
import sys

# ---------------------------------------------------------------------------
# RGBDS 0.9.0 legacy syntax transformations applied per non-string code token:
#
#   1. MACRO? / rept? keyword suffix:
#      The trailing '?' on MACRO and REPT was a pre-0.9.0 shorthand allowing
#      forward-declared macros. It is now a syntax error. Strip it.
#      e.g.  "MACRO? foo"  ->  "MACRO foo"
#            "rept? \1"    ->  "rept \1"
#
#   2. Hash-prefixed string variable interpolation:
#      STRLEN(#varname) / STRSLICE(#varname, ...) used a '#' prefix to
#      interpolate a string equate. In 0.9.0 the prefix is dropped.
#      e.g.  "STRLEN(#chars)"  ->  "STRLEN(chars)"
#
#   3. Standalone '?' placeholder -> 0:
#      Isolated '?' tokens not adjacent to word characters (legacy unknown-
#      value placeholders in data tables) are converted to literal 0.
#      e.g.  "db ?"  ->  "db 0"
#
#   4. Single-quoted character literals -> CHARVAL("X"):
#      RGBDS 0.9.0 removed C-style single-quoted character literals entirely.
#      All occurrences of 'X' in code context are replaced with CHARVAL("X"),
#      which correctly resolves via the active charmap (including special
#      characters like '♂' that have non-ASCII charmap values).
#      e.g.  "cp ' '"      ->  "cp CHARVAL(\" \")"
#            "cp '9' + 1"  ->  "cp CHARVAL(\"9\") + 1"
#            "cp '♂'"      ->  "cp CHARVAL(\"♂\")"
# ---------------------------------------------------------------------------

def upgrade_line_syntax(line: str) -> tuple[str, bool]:
    """
    Parses an assembly line, strictly separating active code, string literals,
    and comments to safely apply all RGBDS 0.9.0 syntax upgrades without
    corrupting string data (e.g. db "Where is Pikachu?").
    """
    if not line.strip() or line.strip().startswith(';'):
        return line, False

    # Isolate trailing comment so text inside comments is never modified.
    comment_parts = line.split(';', 1)
    code_part = comment_parts[0]
    comment_part = f";{comment_parts[1]}" if len(comment_parts) > 1 else ""

    # Tokenize by double-quoted string literals so we only transform code outside quotes.
    string_tokens = re.split(r'(".*?")', code_part)

    line_modified = False
    for i in range(len(string_tokens)):
        token = string_tokens[i]
        # Skip double-quoted string literal tokens entirely.
        if token.startswith('"') and token.endswith('"') and len(token) >= 2:
            continue

        original_token = token

        # --- Fix 1: MACRO? / rept? keyword suffix ---
        # Strip '?' that immediately follows a word character (letter/digit/_).
        token = re.sub(r'([a-zA-Z0-9_])\?', r'\1', token)

        # --- Fix 2: #varname hash-prefixed string variable interpolation ---
        # Remove the '#' prefix before bare identifiers.
        token = re.sub(r'#([a-zA-Z_][a-zA-Z0-9_]*)', r'\1', token)

        # --- Fix 3: Standalone '?' placeholder -> 0 ---
        if '?' in token:
            updated = re.sub(r'(^|[^a-zA-Z0-9_])\?(?=[^a-zA-Z0-9_]|$)',
                             r'\1__TEMP_ZERO__', token)
            token = updated.replace('__TEMP_ZERO__', '0')

        # --- Fix 4: Single-quoted character literals -> CHARVAL("X") ---
        # Matches 'X' where X is one or more characters (handles Unicode like '♂').
        # The replacement wraps the character in CHARVAL("...") so the charmap
        # is consulted at assemble time, preserving correct byte values.
        # Uses a two-pass approach to avoid matching double-quoted content:
        # we are already outside double-quoted strings at this point.
        def replace_char_literal(m):
            inner = m.group(1)
            # Escape any double-quote that might appear inside (shouldn't occur
            # in practice for these source files, but handle defensively).
            inner_escaped = inner.replace('"', '\\"')
            return f'CHARVAL("{inner_escaped}")'

        token = re.sub(r"'([^']+)'", replace_char_literal, token)

        if token != original_token:
            string_tokens[i] = token
            line_modified = True

    new_line = "".join(string_tokens) + comment_part
    return new_line, line_modified


def automate_syntax_upgrade(target_directory):
    """
    Recursively scans all .asm files in the target folder and applies all
    RGBDS 0.9.0 syntax upgrades in a single pass.
    Excludes the vendored ./rgbds/ subtree to avoid corrupting tool test files.
    """
    modified_files = 0
    print(f"Beginning legacy symbol syntax scan in: {target_directory}")

    abs_target = os.path.abspath(target_directory)
    rgbds_vendor_dir = os.path.join(abs_target, "rgbds")

    for root, dirs, files in os.walk(target_directory):
        abs_root = os.path.abspath(root)
        if abs_root == rgbds_vendor_dir or abs_root.startswith(rgbds_vendor_dir + os.sep):
            dirs.clear()
            continue
        if "rgbds" in dirs:
            dirs.remove("rgbds")

        for filename in files:
            if filename.endswith(".asm"):
                filepath = os.path.join(root, filename)

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                except UnicodeDecodeError:
                    try:
                        with open(filepath, 'r', encoding='shift_jis') as f:
                            lines = f.readlines()
                    except Exception:
                        continue

                file_changed = False
                for i, line in enumerate(lines):
                    updated_line, line_changed = upgrade_line_syntax(line)
                    if line_changed:
                        lines[i] = updated_line
                        file_changed = True

                if file_changed:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    print(f"[+] Cleaned legacy syntax tokens in: {filepath}")
                    modified_files += 1

    print(f"Syntax upgrade complete. Modified {modified_files} source files.")


if __name__ == "__main__":
    directory = sys.argv[1] if len(sys.argv) > 1 else "."
    automate_syntax_upgrade(directory)
