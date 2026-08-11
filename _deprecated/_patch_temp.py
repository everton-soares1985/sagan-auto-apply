import re

A = chr(0xC1)
filepath = f"C:\\Users\\User\\OneDrive\\{A}rea de Trabalho\\CODEX_OMNIROUTE\\sagan_auto_apply.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

patches_ok = 0

# ===== PATCH 2: fill_text_field =====
old2 = '    def fill_text_field(self, selectors: List[str], value: str) -> bool:\n        if not value:\n            return False\n        for sel in selectors:\n            try:\n                elem = self.page.query_selector(sel)\n                if elem:\n                    elem.scroll_into_view_if_needed(timeout=3000)\n                    elem.fill(value, force=True)\n                    self.human_delay(0.3, 0.8)\n                    return True\n            except Exception:\n                continue\n        return False'

new2 = '''    def fill_text_field(self, selectors: List[str], value: str) -> bool:
        if not value:
            return False
        for sel in selectors:
            try:
                elem = self.page.query_selector(sel)
                if not elem:
                    continue
                tag = elem.evaluate("el => el.tagName")
                # SCROLL + HIGHLIGHT laranja para debug visual
                elem.evaluate("""el => {
                    el.scrollIntoView({behavior: "smooth", block: "center"});
                    el.style.outline = "4px solid #ff6600";
                    el.style.outlineOffset = "2px";
                    el.style.backgroundColor = "#fff3e0";
                }""")
                self.human_delay(1.0, 1.4)
                # Remove highlight
                elem.evaluate("""el => {
                    el.style.outline = "";
                    el.style.outlineOffset = "";
                    el.style.backgroundColor = "";
                }""")
                # CLICK + FILL
                elem.click(force=True)
                self.human_delay(0.3, 0.5)
                elem.fill(value, force=True)
                self.human_delay(0.3, 0.6)
                # VERIFY
                try:
                    actual = elem.input_value()
                    if actual and actual.strip():
                        log(f"  V Preenchido [{tag}]: {sel} = {actual[:40]!r}")
                        return True
                except Exception:
                    pass
                # Fallback: type()
                log(f"  ? Campo vazio apos fill: {sel}, tentando type()...")
                elem.click(force=True)
                elem.fill("", force=True)
                self.human_delay(0.2, 0.4)
                elem.type(value, delay=40)
                self.human_delay(0.3, 0.6)
                try:
                    actual = elem.input_value()
                    if actual and actual.strip():
                        log(f"  V Preenchido via type: {sel} = {actual[:40]!r}")
                        return True
                except Exception:
                    pass
                log(f"  X Falhou preenchimento: {sel}", "WARN")
            except Exception as e:
                log(f"  X Erro fill_text_field {sel}: {type(e).__name__}", "WARN")
                continue
        return False'''

if old2 in content:
    content = content.replace(old2, new2)
    patches_ok += 1
    print("PATCH 2 OK: fill_text_field")
else:
    print("PATCH 2 FAIL")

# ===== PATCH 3: Add fill_selectize_field =====
anchor3 = '\n    def select_option_fuzzy(self, selectors: List[str], target_value: str) -> bool:'

new3 = '''
    def fill_selectize_field(self, selectors: List[str], target_value: str) -> bool:
        """Preenche campos Selectize.js usando autocomplete (digitar + Enter)."""
        if not target_value:
            return False
        for sel in selectors:
            try:
                select_elem = self.page.query_selector(sel)
                if not select_elem:
                    continue
                class_attr = select_elem.get_attribute("class") or ""
                if "selectized" not in class_attr.lower():
                    continue
                input_selector = sel + " + .selectize-control .selectize-input input"
                try:
                    self.page.wait_for_selector(input_selector, timeout=3000)
                except Exception:
                    continue
                # SCROLL + HIGHLIGHT
                self.page.evaluate(f"""
                    const input = document.querySelector('{input_selector}');
                    if (input) {{
                        input.scrollIntoView({{behavior: "smooth", block: "center"}});
                        const wrapper = input.closest(".selectize-control");
                        if (wrapper) {{
                            wrapper.style.outline = "4px solid #ff6600";
                            wrapper.style.outlineOffset = "2px";
                        }}
                    }}
                """)
                self.human_delay(0.8, 1.2)
                # Remove highlight
                self.page.evaluate(f"""
                    const el = document.querySelector('{input_selector}');
                    if (el) {{
                        const wrapper = el.closest(".selectize-control");
                        if (wrapper) {{
                            wrapper.style.outline = "";
                            wrapper.style.outlineOffset = "";
                        }}
                    }}
                """)
                # Clicar + Digitar + Enter
                self.page.click(input_selector, force=True)
                self.human_delay(0.3, 0.5)
                self.page.fill(input_selector, target_value, force=True)
                self.human_delay(0.4, 0.7)
                self.page.press(input_selector, "Enter")
                self.human_delay(0.4, 0.7)
                log(f"  V Selectize preenchido: {sel} = {target_value!r}")
                return True
            except Exception as e:
                log(f"  ? Erro fill_selectize_field {sel}: {type(e).__name__}", "WARN")
                continue
        return False
'''

if anchor3 in content:
    content = content.replace(anchor3, new3 + '\n    def select_option_fuzzy(self, selectors: List[str], target_value: str) -> bool:')
    patches_ok += 1
    print("PATCH 3 OK: fill_selectize_field")
else:
    print("PATCH 3 FAIL")

# ===== PATCH 4: Modify select_map loop =====
old4 = '''            for label, (pk, val) in select_map.items():
                if self.select_option_fuzzy(get_selectors(pk), val):
                    filled_fields.append(label)
                elif val:
                    failed_fields.append(label)'''

new4 = '''            for label, (pk, val) in select_map.items():
                # Tentar Selectize primeiro, fallback para select nativo
                success = self.fill_selectize_field(get_selectors(pk), val)
                if not success:
                    success = self.select_option_fuzzy(get_selectors(pk), val)
                if success:
                    filled_fields.append(label)
                elif val:
                    failed_fields.append(label)'''

if old4 in content:
    content = content.replace(old4, new4)
    patches_ok += 1
    print("PATCH 4 OK: select_map loop")
else:
    print("PATCH 4 FAIL")

# ===== PATCH 5: Scroll in upload_file =====
old5 = '''                if elem:
                    elem.set_input_files(str(resolved))
                    self.human_delay(0.6, 1.2)'''

new5 = '''                if elem:
                    elem.evaluate("""el => {
                        el.scrollIntoView({behavior: "smooth", block: "center"});
                        el.style.outline = "4px solid #ff6600";
                        el.style.outlineOffset = "2px";
                    }""")
                    self.human_delay(0.8, 1.2)
                    elem.evaluate("el => { el.style.outline = ''; el.style.outlineOffset = ''; }")
                    elem.set_input_files(str(resolved))
                    self.human_delay(0.6, 1.2)'''

if old5 in content:
    content = content.replace(old5, new5)
    patches_ok += 1
    print("PATCH 5 OK: upload_file scroll")
else:
    print("PATCH 5 FAIL")

with open(filepath, "w", encoding="utf-8", newline="") as f:
    f.write(content)
print(f"ALL DONE. {patches_ok}/4 patches applied. Saved {len(content)} chars.")