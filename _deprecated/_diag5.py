"""Diagnostico 5 - pegar TEXTO COMPLETO do form (labels visiveis)"""
import json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

forms_url = "https://forms.saganrecruitment.com/t/5tpJr2NbgJus?utm_source=saganrecruitmentdotcom"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto(forms_url, wait_until="networkidle")
    time.sleep(4)
    
    # Pegar todo o texto da pagina
    text = page.inner_text("body")
    print("=== TEXTO COMPLETO DA PAGINA ===")
    print(text[:5000])
    print("\n\n=== ESTRUTURA AO REDOR DOS CAMPOS ===")
    
    # Pegar HTML externo (pais) dos campos
    html = page.evaluate("""() => {
        const r = [];
        document.querySelectorAll('input, select, textarea').forEach((el, i) => {
            const rect = el.getBoundingClientRect();
            if (rect.width === 0) return;
            let parent = el.parentElement;
            for (let p = 0; p < 6 && parent; p++) {
                if (parent.innerText && parent.innerText.length > 5 && parent.innerText.length < 500) {
                    r.push({
                        idx: i,
                        y: Math.round(rect.y),
                        parentLevel: p,
                        parentTag: parent.tagName,
                        parentText: parent.innerText.substring(0, 200)
                    });
                    break;
                }
                parent = parent.parentElement;
            }
        });
        return r;
    }""")
    
    for h in html:
        print(f"\n[y={h['y']}] Campo {h['idx']} (parent {h['parentLevel']}x <{h['parentTag']}>):")
        print(f"  {h['parentText']}")
    
    time.sleep(2)
    browser.close()