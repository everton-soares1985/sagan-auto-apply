"""Diagnostico 4 - investigar labels/placeholders do forms.saganrecruitment.com"""
import json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

forms_url = "https://forms.saganrecruitment.com/t/5tpJr2NbgJus?utm_source=saganrecruitmentdotcom"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    
    page.goto(forms_url, wait_until="networkidle")
    time.sleep(4)
    
    # Pegar labels/placeholders/ordem
    fields = page.evaluate("""() => {
        const r = [];
        document.querySelectorAll('input, select, textarea').forEach((el, i) => {
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) return;
            
            // Subir para achar label
            let label = '';
            let parent = el.parentElement;
            for (let p = 0; p < 5 && parent; p++) {
                const lbl = parent.querySelector('label');
                if (lbl && lbl.innerText.trim()) {
                    label = lbl.innerText.trim();
                    break;
                }
                parent = parent.parentElement;
            }
            
            // Procurar label apos
            if (!label) {
                let next = el.nextElementSibling;
                while (next && !label) {
                    if (next.tagName === 'LABEL' || next.querySelector) {
                        const lbl = next.querySelector ? next.querySelector('label') : null;
                        if (lbl) label = lbl.innerText.trim();
                    }
                    next = next.nextElementSibling;
                }
            }
            
            // Tambem pegar o label "for" associado
            if (!label && el.id) {
                const lbl = document.querySelector(`label[for="${el.id}"]`);
                if (lbl) label = lbl.innerText.trim();
            }
            
            r.push({
                idx: i,
                tag: el.tagName,
                type: el.type || '',
                name: el.name || '',
                id: el.id || '',
                placeholder: el.placeholder || '',
                label: label,
                y: Math.round(rect.y),
                x: Math.round(rect.x),
                visible: rect.width > 0
            });
        });
        return r;
    }""")
    
    print(f"Total campos: {len(fields)}\n")
    for f in fields:
        print(f"  y={f['y']:5d} x={f['x']:5d} [{f['tag']}] type={f['type']:10s} name='{f['name']}' id='{f['id']}' ph='{f['placeholder'][:50]}' label='{f['label'][:60]}'")
    
    # Pegar HTML do form inteiro
    print("\n\n=== HTML do body (apenas labels e inputs) ===")
    html = page.evaluate("""() => {
        const r = [];
        document.querySelectorAll('label, input, select, textarea').forEach(el => {
            const rect = el.getBoundingClientRect();
            if (rect.width > 0 || el.tagName === 'LABEL') {
                r.push({
                    tag: el.tagName,
                    text: (el.innerText || el.value || el.placeholder || '').trim().substring(0, 100),
                    forAttr: el.getAttribute('for') || '',
                    y: Math.round(rect.y)
                });
            }
        });
        return r;
    }""")
    for h in html[:60]:
        print(f"  y={h['y']:5d} <{h['tag']:10s}> for='{h['forAttr']}' '{h['text'][:80]}'")
    
    time.sleep(2)
    browser.close()