"""Diagnostico 7 - mapear selects do react-select (Academic/Age/Gender/Industry)"""
import json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

forms_url = "https://forms.saganrecruitment.com/t/5tpJr2NbgJus?utm_source=saganrecruitmentdotcom"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto(forms_url, wait_until="networkidle")
    time.sleep(4)
    
    # Pegar todos os elementos com id react-select
    print("=== REACT-SELECT INPUTS ===")
    rs = page.evaluate("""() => {
        const r = [];
        document.querySelectorAll('[id^="react-select"]').forEach(el => {
            const rect = el.getBoundingClientRect();
            r.push({
                id: el.id,
                tag: el.tagName,
                type: el.type,
                y: Math.round(rect.y),
                parentText: (el.closest('div[class*="field"]') || el.parentElement.parentElement.parentElement).innerText.substring(0, 200)
            });
        });
        return r;
    }""")
    for s in rs:
        print(f"  id={s['id']:30s} tag={s['tag']} y={s['y']}")
        print(f"     parent: {s['parentText'][:150]}")
        print()
    
    # Clicar no primeiro react-select para ver opcoes
    print("\n=== CLICANDO PRIMEIRO REACT-SELECT PARA VER OPCOES ===")
    if rs:
        first = page.query_selector(f"#{rs[0]['id']}")
        if first:
            first.click(force=True)
            time.sleep(2)
            # Pegar opcoes abertas
            options = page.evaluate("""() => {
                const opts = document.querySelectorAll('[class*="option"]');
                return Array.from(opts).slice(0, 20).map(o => o.innerText.trim());
            }""")
            print(f"  Opcoes: {options[:10]}")
    
    time.sleep(2)
    browser.close()