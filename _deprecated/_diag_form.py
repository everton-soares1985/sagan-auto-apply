"""Diagnostico rapido - inspeciona estrutura real do formulario Sagan"""
import json, time, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

data = json.loads(Path("sagan_jobs.json").read_text(encoding="utf-8"))
job = data["jobs"][0]
url = job["url"]
print(f"Vaga: {job['title']}")
print(f"URL: {url}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    
    print("\n1. Navegando...")
    page.goto(url, wait_until="networkidle")
    time.sleep(2)
    
    print("2. Clicando APPLY...")
    page.click("a:has-text('APPLY FOR THIS JOB')")
    time.sleep(4)
    
    # Check for iframes
    frames = page.frames
    print(f"\n3. Frames na pagina: {len(frames)}")
    for i, f in enumerate(frames):
        print(f"   Frame {i}: url={f.url[:80]}")
    
    # Find the form
    print("\n4. Procurando formulario...")
    forms = page.query_selector_all("form")
    print(f"   Tags <form>: {len(forms)}")
    
    # Check ALL inputs/selects/textarea on page
    print("\n5. Todos os campos input/select/textarea:")
    fields = page.evaluate("""() => {
        const result = [];
        const elements = document.querySelectorAll('input, select, textarea');
        elements.forEach((el, i) => {
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            result.push({
                idx: i,
                tag: el.tagName,
                type: el.type || '',
                name: el.name || '',
                id: el.id || '',
                placeholder: el.placeholder || '',
                class: (el.className || '').substring(0, 60),
                visible: style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0,
                rect: {x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height)},
                disabled: el.disabled,
                readonly: el.readOnly,
                value: (el.value || '').substring(0, 30),
                inIframe: el.ownerDocument !== document
            });
        });
        return result;
    }""")
    
    visible = [f for f in fields if f['visible']]
    hidden = [f for f in fields if not f['visible']]
    
    print(f"\n   VISIVEIS ({len(visible)}):")
    for f in visible:
        print(f"   [{f['idx']}] <{f['tag']}> name='{f['name']}' type='{f['type']}' "
              f"placeholder='{f['placeholder']}' rect=({f['rect']['x']},{f['rect']['y']},{f['rect']['w']}x{f['rect']['h']}) "
              f"val='{f['value']}'")
    
    print(f"\n   OCULTOS ({len(hidden)}):")
    for f in hidden[:10]:
        print(f"   [{f['idx']}] <{f['tag']}> name='{f['name']}' class='{f['class']}' val='{f['value']}'")
    
    # Check specific names
    target_names = ["pt_user_fname", "pt_user_lname", "user_email", "user_phone", 
                    "academic-level", "Age", "gender", "industry"]
    print("\n6. Verificacao de seletores por name:")
    for name in target_names:
        sel = f'[name="{name}"]'
        try:
            elem = page.query_selector(sel)
            if elem:
                tag = elem.evaluate("el => el.tagName")
                vis = elem.is_visible()
                bbox = elem.bounding_box()
                print(f"   {sel} -> <{tag}> visible={vis} bbox={bbox}")
            else:
                print(f"   {sel} -> NAO ENCONTRADO")
        except Exception as e:
            print(f"   {sel} -> ERRO: {e}")
    
    time.sleep(3)
    browser.close()
    print("\n=== FIM DIAGNOSTICO ===")