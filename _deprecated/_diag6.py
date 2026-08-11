"""Diagnostico 6 - pegar os 3 selects/inputs entre Phone e Resume"""
import json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

forms_url = "https://forms.saganrecruitment.com/t/5tpJr2NbgJus?utm_source=saganrecruitmentdotcom"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto(forms_url, wait_until="networkidle")
    time.sleep(4)
    
    # Pegar contexto entre 2400 e 2900 (entre country e resume)
    print("=== CAMPOS ENTRE PHONE E UPLOAD (2400-2900) ===")
    html = page.evaluate("""() => {
        const r = [];
        document.querySelectorAll('input, select, textarea, label, div, p').forEach(el => {
            const rect = el.getBoundingClientRect();
            if (rect.width === 0) return;
            const y = rect.y;
            if (y >= 2400 && y <= 2900) {
                r.push({
                    y: Math.round(y),
                    tag: el.tagName,
                    text: (el.innerText || el.value || el.placeholder || '').trim().substring(0, 200),
                    cls: (el.className || '').substring(0, 60)
                });
            }
        });
        // dedup
        const seen = new Set();
        return r.filter(x => {
            const k = x.y + '|' + x.text.substring(0, 50);
            if (seen.has(k)) return false;
            seen.add(k);
            return true;
        });
    }""")
    
    for h in html:
        print(f"  y={h['y']:5d} <{h['tag']:8s}> '{h['text'][:150]}'")
    
    time.sleep(2)
    browser.close()