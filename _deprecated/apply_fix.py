import sys
fix_path = "sagan_auto_apply.py"
s = open(fix_path, encoding="utf-8").read()

# Procura a linha "if sys.platform == "win32":" e adiciona o set_event_loop_policy antes
old_block = '''if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass'''

new_block = '''if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass'''

s = s.replace(old_block, new_block)
open(fix_path, "w", encoding="utf-8").write(s)
print("fix aplicado em sagan_auto_apply.py")
