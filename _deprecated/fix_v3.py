import os, sys

# Ler o original
src = r"C:\Users\User\OneDrive\Área de Trabalho\CODEX_OMNIROUTE\sagan_selenium.py"
s = open(src, encoding="utf-8").read()

# Substituir o metodo start()
old = '''    def start(self):
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        # User data dir na pasta do projeto
        import time
        user_data = BASE_DIR / f"chrome_data_{int(time.time())}"
        user_data.mkdir(exist_ok=True)
        options.add_argument(f"--user-data-dir={user_data}")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)'''

# tambem a outra versao
old2 = '''    def start(self):
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        # Minimal options - let Chrome use defaults
        options.add_argument("--remote-debugging-port=9222")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])'''

new = '''    def start(self):
        options = Options()
        # Chrome oficial versao 151
        options.binary_location = r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])'''

s = s.replace(old, new)
s = s.replace(old2, new)

dst = r"C:\PROGRAMACAO\SAGAN_AUTOMATION\sagan_selenium_v3.py"
try:
    open(dst, "w", encoding="utf-8").write(s)
    print(f"OK - salvo em {dst}")
except PermissionError:
    # salva no CODEX_OMNIROUTE em vez disso
    dst2 = "sagan_selenium_v3.py"
    open(dst2, "w", encoding="utf-8").write(s)
    print(f"Sem permissao em PROGRAMACAO. Salvo em {dst2}")
