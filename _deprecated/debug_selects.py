"""
Debug script para testar seletores de campos select/dropdown
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
import time

# Carregar dados
data = json.loads(Path("sagan_jobs.json").read_text(encoding="utf-8"))
profile = json.loads(Path("candidate_profile.json").read_text(encoding="utf-8"))
first_job = data["jobs"][0]

print("=== DEBUG: CAMPOS SELECT ===")
print(f"Vaga: {first_job['title']}")
print(f"URL: {first_job['url']}\n")

# Campos para testar
test_fields = {
    "academic-level": profile["academic_level"],
    "Age": profile["age"],
    "gender": profile["gender"],
    "industry": profile["industry"]
}

print("Valores do perfil:")
for field_name, value in test_fields.items():
    print(f"  {field_name}: {value}")

# Mapeamento de seletores
field_selectors = {f["name"]: f.get("selector", "") for f in first_job["form_fields"]}

print("\nSeletores encontrados no JSON:")
for field_name in test_fields.keys():
    selector = field_selectors.get(field_name, "NAO ENCONTRADO")
    print(f"  {field_name}: {selector}")

# Testar no navegador
print("\n=== INICIANDO TESTE NO NAVEGADOR ===")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    print(f"Navegando para: {first_job['url']}")
    page.goto(first_job['url'])
    time.sleep(2)
    
    # Clicar no botão de aplicar
    print("Clicando em 'APPLY FOR THIS JOB'...")
    page.click("a:has-text('APPLY FOR THIS JOB')")
    time.sleep(3)
    
    print("\n=== TESTANDO CAMPOS SELECT ===")
    for field_name, value in test_fields.items():
        print(f"\n[{field_name}] Tentando preencher com: '{value}'")
        
        # Tentar seletor do JSON
        json_selector = field_selectors.get(field_name, "")
        selectors = [json_selector, f"[name='{field_name}']"] if json_selector else [f"[name='{field_name}']"]
        
        filled = False
        for selector in selectors:
            print(f"  Testando seletor: {selector}")
            try:
                elem = page.query_selector(selector)
                if elem:
                    print(f"    ✓ Elemento encontrado!")
                    
                    # Verificar se é um select
                    tag = elem.evaluate("el => el.tagName")
                    print(f"    Tag: {tag}")
                    
                    if tag.lower() == "select":
                        # Listar opções
                        options = elem.query_selector_all("option")
                        print(f"    Opções disponíveis ({len(options)}):")
                        for i, opt in enumerate(options):
                            opt_value = opt.get_attribute("value") or ""
                            opt_text = opt.inner_text().strip()
                            print(f"      [{i}] value='{opt_value}' text='{opt_text}'")
                        
                        # Tentar selecionar
                        try:
                            elem.select_option(label=value)
                            print(f"    ✓ SUCESSO: Selecionado por label")
                            filled = True
                            break
                        except Exception as e1:
                            print(f"    ✗ Falha por label: {e1}")
                            try:
                                elem.select_option(value=value)
                                print(f"    ✓ SUCESSO: Selecionado por value")
                                filled = True
                                break
                            except Exception as e2:
                                print(f"    ✗ Falha por value: {e2}")
                    else:
                        print(f"    ✗ Não é um <select>, é um <{tag}>")
                else:
                    print(f"    ✗ Elemento não encontrado")
            except Exception as e:
                print(f"    ✗ Erro: {e}")
        
        if not filled:
            print(f"  ❌ FALHOU: Não foi possível preencher {field_name}")
    
    print("\n=== AGUARDANDO 30s PARA INSPEÇÃO MANUAL ===")
    time.sleep(30)
    browser.close()

print("\n=== DEBUG CONCLUÍDO ===")
