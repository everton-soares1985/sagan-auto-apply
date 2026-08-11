"""Diagnostico 3 - navega direto para forms.saganrecruitment.com"""
import json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

forms_url = "https://forms.saganrecruitment.com/t/5tpJr2NbgJus?utm_source=saganrecruitmentdotcom"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    
    print("Navegando direto para forms.saganrecruitment.com...")
    page.goto(forms_url, wait_until="networkidle")
    time.sleep(4)
    
    page.screenshot(path="diag3_forms_direct.png", full_page=True)
    print("Screenshot: diag3_forms_direct.png")
    
    # Listar todos os campos visiveis
    visible = page.evaluate("""() => {
        const r = [];
        document.querySelectorAll('input, select, textarea').forEach(el => {
            const rect = el.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
                r.push({name: el.name, tag: el.tagName, type: el.type,
                        y: Math.round(rect.y), h: Math.round(rect.height),
                        val: (el.value||'').substring(0,20),
                        ph: el.placeholder || ''});
            }
        });
        return r;
    }""")
    
    print(f"\nCampos visiveis no forms.saganrecruitment.com: {len(visible)}")
    for v in visible:
        print(f"   <{v['tag']}> name='{v['name']}' type='{v['type']}' ph='{v['ph']}' y={v['y']}")
    
    # Testar o campo direto
    print("\nTestando [name='pt_user_fname']...")
    elem = page.query_selector("[name='pt_user_fname']")
    if elem:
        bbox = elem.bounding_box()
        print(f"   bbox={bbox}")
        elem.click(force=True)
        time.sleep(0.3)
        elem.fill("Everton", force=True)
        time.sleep(0.5)
        actual = elem.input_value()
        print(f"   apos fill: {actual!r}")
        page.screenshot(path="diag3_after_fill.png")
    
    time.sleep(2)
    browser.close()
    print("\n=== FIM ===")