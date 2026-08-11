"""Diagnostico 2 - investiga o que o CTA realmente faz"""
import json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

data = json.loads(Path("sagan_jobs.json").read_text(encoding="utf-8"))
job = data["jobs"][0]
url = job["url"]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    
    page.goto(url, wait_until="networkidle")
    time.sleep(2)
    
    # Tirar screenshot antes do CTA
    page.screenshot(path="diag_before_cta.png")
    print("1. Screenshot antes do CTA: diag_before_cta.png")
    
    # Encontrar TODOS os botoes APPLY visiveis
    btns = page.query_selector_all("a, button")
    apply_btns = []
    for b in btns:
        try:
            txt = b.inner_text().strip().upper()
            if "APPLY" in txt and b.is_visible():
                apply_btns.append((txt, b))
                print(f"   Botao APPLY visivel: '{txt[:60]}' href={b.get_attribute('href')}")
        except:
            pass
    
    print(f"\n2. Clicando no primeiro APPLY...")
    if apply_btns:
        apply_btns[0][1].click(force=True)
    else:
        print("   NENHUM botao APPLY visivel encontrado!")
    
    time.sleep(4)
    
    # Screenshot depois
    page.screenshot(path="diag_after_cta.png")
    print("3. Screenshot depois do CTA: diag_after_cta.png")
    
    # Verificar se ha modais/dialogs abertos
    modals = page.evaluate("""() => {
        const modals = [];
        // Bootstrap modals
        document.querySelectorAll('.modal, .dialog, [role="dialog"], .popup, .overlay, .lightbox').forEach(el => {
            const style = window.getComputedStyle(el);
            if (style.display !== 'none' && style.visibility !== 'hidden') {
                modals.push({
                    tag: el.tagName,
                    class: (el.className || '').substring(0, 80),
                    id: el.id || '',
                    rect: el.getBoundingClientRect()
                });
            }
        });
        return modals;
    }""")
    
    print(f"\n4. Modais/Dialogs visiveis: {len(modals)}")
    for m in modals:
        print(f"   {m['tag']} class='{m['class']}' rect={m['rect']}")
    
    # Verificar campos do form novamente com scroll
    print("\n5. Scroll ate campos do form...")
    try:
        elem = page.query_selector('[name="pt_user_fname"]')
        if elem:
            elem.evaluate("el => el.scrollIntoView({behavior: 'smooth', block: 'center'})")
            time.sleep(2)
            page.screenshot(path="diag_scrolled_to_form.png")
            print("   Scroll feito, screenshot: diag_scrolled_to_form.png")
            
            vis = elem.is_visible()
            bbox = elem.bounding_box()
            print(f"   pt_user_fname: visible={vis} bbox={bbox}")
    except Exception as e:
        print(f"   Erro: {e}")
    
    # Listar todos os inputs visiveis depois do CTA
    visible_now = page.evaluate("""() => {
        const r = [];
        document.querySelectorAll('input, select, textarea').forEach(el => {
            const rect = el.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
                r.push({name: el.name, tag: el.tagName, type: el.type, 
                        y: Math.round(rect.y), h: Math.round(rect.height),
                        val: (el.value||'').substring(0,20)});
            }
        });
        return r;
    }""")
    
    print(f"\n6. Elementos com dimensoes > 0: {len(visible_now)}")
    for v in visible_now[:20]:
        print(f"   <{v['tag']}> name='{v['name']}' type='{v['type']}' y={v['y']} h={v['h']} val='{v['val']}'")
    
    time.sleep(2)
    browser.close()
    print("\n=== FIM ===")