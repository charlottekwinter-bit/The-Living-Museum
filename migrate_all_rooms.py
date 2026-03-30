#!/usr/bin/env python3
"""
One-shot migration: updates all Museum room scripts from Anthropic to Groq API.
Run via workflow_dispatch. Commits all changes automatically.
"""

import os
import re
from pathlib import Path

MUSEUM_ROOT = Path(__file__).parent


def migrate_content(content):
    c = content

    # URL
    c = c.replace('ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"',
                  'GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"')
    c = c.replace('"https://api.anthropic.com/v1/messages"',
                  '"https://api.groq.com/openai/v1/chat/completions"')
    c = c.replace('ANTHROPIC_API_URL', 'GROQ_API_URL')

    # Env var
    c = c.replace('os.environ.get("ANTHROPIC_API_KEY"', 'os.environ.get("GROQ_API_KEY"')
    c = c.replace("os.environ.get('ANTHROPIC_API_KEY'", "os.environ.get('GROQ_API_KEY'")
    c = c.replace('"ANTHROPIC_API_KEY"', '"GROQ_API_KEY"')
    c = c.replace("'ANTHROPIC_API_KEY'", "'GROQ_API_KEY'")

    # Headers: x-api-key + anthropic-version -> Authorization Bearer
    c = re.sub(
        r'"x-api-key":\s*api_key,\s*\n(\s*)"anthropic-version":\s*"[^"]*",',
        '"Authorization": f"Bearer {api_key}",',
        c
    )
    c = re.sub(
        r'"anthropic-version":\s*"[^"]*",\s*\n(\s*)"x-api-key":\s*api_key,',
        '"Authorization": f"Bearer {api_key}",',
        c
    )
    c = re.sub(r'\s*"anthropic-version":\s*"[^"]*",\n', '\n', c)

    # Model
    c = re.sub(r'"claude-[a-z0-9\-."]+"', '"llama-3.3-70b-versatile"', c)

    # Response parsing: Anthropic -> OpenAI
    c = c.replace('data["content"][0]["text"]', 'data["choices"][0]["message"]["content"]')
    c = c.replace("data['content'][0]['text']", "data['choices'][0]['message']['content']")
    c = re.sub(r'response\.json\(\)\["content"\]\[0\]\["text"\]',
               'response.json()["choices"][0]["message"]["content"]', c)
    c = c.replace('.get("content", [])', '.get("choices", [])')
    c = re.sub(
        r'for block in (\w+):\s*\n\s*if block\.get\("type"\) == "text":\s*\n\s*return block\["text"\]\.strip\(\)',
        r'if \1:\n            return \1[0]["message"]["content"].strip()',
        c
    )

    return c


def main():
    changed = []
    for py_file in sorted(MUSEUM_ROOT.rglob('*.py')):
        rel = str(py_file.relative_to(MUSEUM_ROOT))
        if rel in ('migrate_all_rooms.py', 'gen_workflows.py',
                   'integrate_rooms.py', 'add_message_triggers.py'):
            continue
        if 'integration/validate_room' in rel or 'example-room' in rel:
            continue
        try:
            original = py_file.read_text()
        except Exception as e:
            print(f"SKIP {rel}: {e}")
            continue
        if 'api.anthropic.com' not in original and 'ANTHROPIC_API_KEY' not in original:
            continue
        migrated = migrate_content(original)
        if migrated != original:
            py_file.write_text(migrated)
            changed.append(rel)
            print(f"MIGRATED: {rel}")
        else:
            print(f"NO_CHANGE: {rel}")
    print(f"\nDone: {len(changed)} files migrated")


if __name__ == "__main__":
    main()
