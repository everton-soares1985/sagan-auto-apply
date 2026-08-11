import sys
fix_path = "sagan_auto_apply.py"
s = open(fix_path, encoding="utf-8").read()

# Corrige a policy
s = s.replace(
    "asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())",
    "# Windows Proactor Event Loop (default) suporta subprocessos"
)

open(fix_path, "w", encoding="utf-8").write(s)
print("fix corrigido - removendo WindowsSelectorEventLoopPolicy")
