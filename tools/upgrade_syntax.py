#!/usr/bin/env python3

import os
import re
import sys

# ============================================================================
# RGBDS 0.9.0 Automatic Syntax Upgrade Utility
#
# Handles:
#
# 1. MACRO? / REPT?
#       MACRO? foo -> MACRO foo
#       REPT? 10   -> REPT 10
#
# 2. #identifier interpolation
#       STRLEN(#foo) -> STRLEN(foo)
#
# 3. Standalone ? placeholders
#       db ? -> db 0
#
# 4. Single-quoted character literals
#       cp 'A' -> cp CHARVAL("A")
#
# 5. BANK function normalization
#       Bank(label) -> BANK(label)
#
# 6. Other RGBDS built-in function normalization
#       High() -> HIGH()
#
# 7. Redundant parentheses inside brackets
#       [label + (macro)] -> [label + macro]
#
# 8. Legacy Register Indirection (RGBDS 0.9.0 Strict Memory Compliance)
#       ld a, (wVar) -> ld a, [wVar]
#       ld (bc), a   -> ld [bc], a
#       add (hl)     -> add [hl]
#       jp (hl)      -> jp hl
#
# 9. Legacy Condition Parentheses
#       IF (DEF(DEBUG)) -> IF DEF(DEBUG)
#
# Preserves:
#       - comments, strings, UTF-8 source
# Excludes:
#       ./rgbds/
# ============================================================================

FUNCTION_FIXES = {
    "bank": "BANK",
    "Bank": "BANK",
    "BANK": "BANK",

    "high": "HIGH",
    "High": "HIGH",
    "HIGH": "HIGH",

    "low": "LOW",
    "Low": "LOW",
    "LOW": "LOW",
}


def replace_char_literal(match):
    inner = match.group(1)
    inner = inner.replace('"', '\\"')
    return f'CHARVAL("{inner}")'


def normalize_rgbds_functions(token):
    for old_name, new_name in FUNCTION_FIXES.items():
        pattern = rf'\b{re.escape(old_name)}\s*\('
        token = re.sub(
            pattern,
            lambda m: f"{new_name}(",
            token
        )
    return token


def clean_bracket_parens(match):
    inner = match.group(1)
    inner = re.sub(r'\(\s*([A-Za-z0-9_]+)\s*\)', r'\1', inner)
    return f'[{inner}]'


def upgrade_code_token(token):
    original = token

    # ------------------------------------------------------------------
    # Fix 1: Legacy Macro / Rept Syntax
    # ------------------------------------------------------------------
    token = re.sub(
        r'\b(MACRO|REPT)\?',
        r'\1',
        token,
        flags=re.IGNORECASE
    )

    # ------------------------------------------------------------------
    # Fix 2: #identifier Interpolation
    # ------------------------------------------------------------------
    token = re.sub(
        r'#([A-Za-z_][A-Za-z0-9_]*)',
        r'\1',
        token
    )

    # ------------------------------------------------------------------
    # Fix 3: Standalone ? Placeholders
    # ------------------------------------------------------------------
    if '?' in token:
        token = re.sub(
            r'(^|[^A-Za-z0-9_])\?(?=[^A-Za-z0-9_]|$)',
            r'\10',
            token
        )

    # ------------------------------------------------------------------
    # Fix 4: Single-quoted Character Literals
    # ------------------------------------------------------------------
    token = re.sub(
        r"'([^']+)'",
        replace_char_literal,
        token
    )

    # ------------------------------------------------------------------
    # Fix 5 / 6: RGBDS Function Capitalization
    # ------------------------------------------------------------------
    token = normalize_rgbds_functions(token)

    # ------------------------------------------------------------------
    # Fix 7: Redundant parentheses in memory dereferences
    # ------------------------------------------------------------------
    token = re.sub(
        r'\[(.*?)\]',
        clean_bracket_parens,
        token
    )

    # ------------------------------------------------------------------
    # Fix 8: Legacy Memory Indirection -> Brackets
    # Targets all permutations of GBZ80 memory ops to avoid breaking math
    # ------------------------------------------------------------------
    
    # Rule 1: Explicit A register reading from ANY memory address/pointer
    token = re.sub(
        r'\b(ld|ldh|add|adc|sub|sbc|and|xor|or|cp)\s+a\s*,\s*\(\s*([^()]+)\s*\)',
        r'\1 a, [\2]',
        token,
        flags=re.IGNORECASE
    )

    # Rule 1.5: Implicit A register memory reads (e.g., `cp (hl)`, `add (wVar)`)
    token = re.sub(
        r'\b(add|adc|sub|sbc|and|xor|or|cp)\s*\(\s*([^()]+)\s*\)',
        r'\1 [\2]',
        token,
        flags=re.IGNORECASE
    )

    # Rule 2: A register writing to ANY memory address/pointer
    token = re.sub(
        r'\b(ld|ldh)\s*\(\s*([^()]+)\s*\)\s*,\s*a\b',
        r'\1 [\2], a',
        token,
        flags=re.IGNORECASE
    )

    # Rule 3: SP writing to ANY memory address
    token = re.sub(
        r'\b(ld)\s*\(\s*([^()]+)\s*\)\s*,\s*sp\b',
        r'\1 [\2], sp',
        token,
        flags=re.IGNORECASE
    )

    # Rule 4: Other 8-bit registers reading from specific valid pointers
    token = re.sub(
        r'\b(ld)\s+([abcdehl])\s*,\s*\(\s*(hl|bc|de|c|hl\+|hl-|hli|hld)\s*\)',
        r'\1 \2, [\3]',
        token,
        flags=re.IGNORECASE
    )

    # Rule 5: Modifying or writing to specific valid pointers (e.g. `ld (hl), 5`)
    token = re.sub(
        r'\b(ld|inc|dec)\s*\(\s*(hl|bc|de|c|hl\+|hl-|hli|hld)\s*\)',
        r'\1 [\2]',
        token,
        flags=re.IGNORECASE
    )

    # Rule 6: Bitwise ops on (hl)
    token = re.sub(
        r'\b(bit|set|res)\s+([0-7])\s*,\s*\(\s*(hl)\s*\)',
        r'\1 \2, [\3]',
        token,
        flags=re.IGNORECASE
    )

    # Rule 7: Strict jp hl formatting
    token = re.sub(
        r'\b(jp)\s*\(\s*(hl)\s*\)',
        r'\1 hl',
        token,
        flags=re.IGNORECASE
    )

    # ------------------------------------------------------------------
    # Fix 9: IF / ELIF parenthesized conditions
    # ------------------------------------------------------------------
    token = re.sub(
        r'\b(IF|ELIF)\s*\(\s*(.*?)\s*\)',
        r'\1 \2',
        token,
        flags=re.IGNORECASE
    )

    return token, token != original


def split_code_and_comment(line):
    in_string = False
    for i, ch in enumerate(line):
        if ch == '"':
            in_string = not in_string
        elif ch == ';' and not in_string:
            return line[:i], line[i:]
    return line, ""


def upgrade_line_syntax(line):
    stripped = line.strip()

    if not stripped or stripped.startswith(";"):
        return line, False

    code_part, comment_part = split_code_and_comment(line)
    tokens = re.split(r'(".*?")', code_part)

    modified = False

    for i in range(len(tokens)):
        token = tokens[i]

        if (
            token.startswith('"')
            and token.endswith('"')
            and len(token) >= 2
        ):
            continue

        new_token, changed = upgrade_code_token(token)

        if changed:
            tokens[i] = new_token
            modified = True

    result = "".join(tokens) + comment_part
    return result, modified


def read_source_file(path):
    encodings = ["utf-8", "shift_jis", "cp932", "latin1"]
    for encoding in encodings:
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.readlines()
        except UnicodeDecodeError:
            continue
    return None


def write_source_file(path, lines):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.writelines(lines)


def should_skip_directory(abs_root, rgbds_vendor_dir):
    return (
        abs_root == rgbds_vendor_dir
        or abs_root.startswith(rgbds_vendor_dir + os.sep)
    )


def process_asm_file(filepath):
    lines = read_source_file(filepath)
    if lines is None:
        return False

    modified = False
    for i in range(len(lines)):
        updated_line, changed = upgrade_line_syntax(lines[i])
        if changed:
            lines[i] = updated_line
            modified = True

    if modified:
        write_source_file(filepath, lines)

    return modified


def automate_syntax_upgrade(target_directory):
    modified_files = 0
    abs_target = os.path.abspath(target_directory)
    rgbds_vendor_dir = os.path.join(abs_target, "rgbds")

    print()
    print("========================================")
    print(" RGBDS 0.9.0 Syntax Upgrade")
    print("========================================")
    print(f"Scanning: {abs_target}")
    print()

    for root, dirs, files in os.walk(target_directory):
        abs_root = os.path.abspath(root)

        if should_skip_directory(abs_root, rgbds_vendor_dir):
            dirs.clear()
            continue

        if "rgbds" in dirs:
            dirs.remove("rgbds")

        for filename in files:
            if not filename.lower().endswith(".asm"):
                continue

            filepath = os.path.join(root, filename)
            try:
                if process_asm_file(filepath):
                    modified_files += 1
                    print(f"[+] Updated: {filepath}")
            except Exception as e:
                print(f"[!] Failed: {filepath}")
                print(f"    {e}")

    print()
    print("========================================")
    print(f"Modified files: {modified_files}")
    print("Done.")
    print("========================================")
    print()


if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    automate_syntax_upgrade(target_dir)
