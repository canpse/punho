#!/usr/bin/env python3
"""Liga (ou desliga, com --remover) o hook do punho no ~/.claude/settings.json.
Faz backup em ~/.claude/settings.json.antes-do-punho antes de mexer."""
import json
import shutil
import sys
from pathlib import Path

p = Path.home() / ".claude/settings.json"
cmd = f"python3 {Path(__file__).resolve().parent / 'claude_hook.py'}"
s = json.loads(p.read_text()) if p.exists() else {}
shutil.copy(p, p.with_name("settings.json.antes-do-punho")) if p.exists() else None
hooks = s.setdefault("hooks", {})

if "--remover" in sys.argv:
    for evento in list(hooks):
        hooks[evento] = [g for g in hooks[evento] if not any(h.get("command") == cmd for h in g.get("hooks", []))]
        if not hooks[evento]:
            del hooks[evento]
    print("hook do punho removido")
else:
    for evento, timeout in (("PermissionRequest", 130), ("UserPromptSubmit", 5), ("Stop", 10)):
        grupos = hooks.setdefault(evento, [])
        if not any(h.get("command") == cmd for g in grupos for h in g.get("hooks", [])):
            grupos.append({"hooks": [{"type": "command", "command": cmd, "timeout": timeout}]})
    print("hook do punho ligado (vale pras próximas sessões do Claude Code)")

if not hooks:
    s.pop("hooks")
p.write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n")
