"""
Debug rápido dos campos select
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
import time

data = json.loads(Path("sagan_jobs.json").read_text(encoding="utf-8"))
profile = json.loads(Path("candidate_profile.json").read_text(encoding="utf-8"))
first_job = data["jobs"][0]

print("=== DEBUG CAMPOS SELECT ===")
print(f"Vaga: {first_job['title']}\n")

test_fields = {
    "academic-level": profile["academic_level"],
    "Age": profile["age"],
    "gender": profile["gender"],
    "industry": profile["industry"]
}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    page.goto(first_job['url'])
    time.sleep(2)
    page.click("a:has-text('APPLY FOR THIS JOB')")
    time.sleep(3)
    
    for field_name, value in test_fields.items():
        print(f"\n[{field_name}] = '{value}'")
        selector = f"[name='{field_name}']"
        
        try:
            elem = page.query_selector(selector)
            if elem:
                tag = elem.evaluate("el => el.tagName")
                if tag.lower() == "select":
                    options = elem.query_selector_all("option")
                    print(f"  ✓ SELECT encontrado com {len(options)} opções:")
                    for opt in options[:5]:
                        val = opt.get_attribute("value") or ""
                        txt = opt.inner_text().strip()
                        print(f"    - value='{val}' text='{txt}'")
                    
                    # Tentar selecionar
                    try:
                        page.select_option(selector, label=value)
                        print(f"  ✓ PREENCHIDO com sucesso!")
                    except Exception as e:
                        print(f"  ✗ Falha: {str(e)[:100]}")
                else:
                    print(f"  ✗ Não é select, é {tag}")
            else:
                print(f"  ✗ Elemento não encontrado: {selector}")
        except Exception as e:
            print(f"  ✗ Erro: {str(e)[:100]}")
    
    time.sleep(5)
    browser.close()

print("\n=== CONCLUÍDO ===")
