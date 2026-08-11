filepath = r'C:\Users\User\OneDrive\Área de Trabalho\CODEX_OMNIROUTE\sagan_auto_apply.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================================
# PATCH: Reescrever bloco de preenchimento
# - Buscar campos por tipo DOM (type=text, type=email, type=tel)
# - Preencher 4 primeiros FIXOS: name -> email -> country -> phone
# - Buscar textareas por placeholder/label
# - Buscar salaries por placeholder especifico
# - 3 react-selects por ULTIMO
# ============================================================
old_block = '''            # FORM SAgan em forms.saganrecruitment.com (campos SEM name)
            # Ordem dos campos de texto por ordem visual:
            # 0=Full Name, 1=Email, 2=Phone (tel), 3=Resume text, 4=LinkedIn
            # 5=current salary, 6=target salary
            # depois 3 react-selects: Where/sole/contract
            # depois 5-6 textareas (story, experience...)
            try:
                all_inputs = self.page.evaluate("""() => {
                    const r = [];
                    document.querySelectorAll('input, textarea').forEach((el, i) => {
                        const rect = el.getBoundingClientRect();
                        if (rect.width === 0 || rect.height === 0) return;
                        if (el.type === 'hidden' || el.type === 'file') return;
                        const id = el.id || '';
                        if (id.startsWith('react-select-')) return;
                        r.push({
                            idx: r.length,
                            tag: el.tagName,
                            type: el.type || '',
                            y: Math.round(rect.y),
                            x: Math.round(rect.x),
                            rect: {x: rect.x, y: rect.y, w: rect.width, h: rect.height}
                        });
                    });
                    return r;
                }""")
                
                log(f"  Campos input/textarea visiveis: {len(all_inputs)}")
                
                # Mapear por ordem (formulario fixo)
                order_map = []
                # Heuristica: pegar todos na ordem vertical, agrupar x~proximo
                # Os inputs estao em y=2232,2314,2397,2479(tel),2581(textarea),2734,3238,3339
                
                # Full Name (primeiro input text)
                name_input = next((i for i, x in enumerate(all_inputs) if x['type'] == 'text' and x['y'] < 2300), None)
                if name_input is not None:
                    order_map.append(("full_name", self.profile.first_name + " " + self.profile.last_name))
                
                # Email (input email)
                email_input = next((i for i, x in enumerate(all_inputs) if x['type'] == 'email'), None)
                if email_input is not None:
                    order_map.append(("email", self.profile.email))
                
                # Phone (input tel)
                phone_input = next((i for i, x in enumerate(all_inputs) if x['type'] == 'tel'), None)
                if phone_input is not None:
                    order_map.append(("phone", self.profile.phone))
                
                # Resume text (textarea com texto "Copy and paste")
                resume_text = self.profile.cover_letter or "Experienced professional with strong background."
                order_map.append(("resume_text", resume_text))
                
                # LinkedIn
                if self.profile.linkedin_url:
                    order_map.append(("linkedin", self.profile.linkedin_url))
                
                # Current salary
                order_map.append(("current_salary", self.profile.current_salary))
                # Target salary
                order_map.append(("target_salary", self.profile.salary_expectation))
                
                # Story (textarea 1)
                order_map.append(("story", self.profile.story or "I am a dedicated professional seeking new opportunities."))
                
                # Experience textareas (4-5 perguntas)
                for i, exp in enumerate([
                    self.profile.exp_1 or "I have extensive experience in this field.",
                    self.profile.exp_2 or "I have strong analytical and problem-solving skills.",
                    self.profile.exp_3 or "I am committed to quality and continuous improvement.",
                    self.profile.exp_4 or "I have a proven track record of meeting deadlines.",
                    self.profile.exp_5 or "I bring strong technical and communication skills.",
                ]):
                    order_map.append((f"exp_{i+1}", exp))
                
                # Preencher por indice visual (selecionando por y/x)
                # Estrategia: cada campo unico por y, pegar elem no DOM por posicao
                visible_inputs = self.page.query_selector_all("input, textarea")
                visible_inputs = [e for e in visible_inputs if e.is_visible() and e.evaluate("el => el.type !== 'hidden' && el.type !== 'file'") and not (e.get_attribute('id') or '').startswith('react-select-')]
                
                for idx, (label, val) in enumerate(order_map):
                    if idx >= len(visible_inputs):
                        break
                    if not val:
                        continue
                    elem = visible_inputs[idx]
                    tag = elem.evaluate("el => el.tagName")
                    # SCROLL + HIGHLIGHT laranja
                    elem.evaluate("""el => {
                        el.scrollIntoView({behavior: "smooth", block: "center"});
                        el.style.outline = "4px solid #ff6600";
                        el.style.outlineOffset = "2px";
                        el.style.backgroundColor = "#fff3e0";
                    }""")
                    self.human_delay(1.0, 1.4)
                    elem.evaluate("""el => {
                        el.style.outline = "";
                        el.style.outlineOffset = "";
                        el.style.backgroundColor = "";
                    }""")
                    elem.click(force=True)
                    self.human_delay(0.3, 0.5)
                    elem.fill(val, force=True)
                    self.human_delay(0.3, 0.6)
                    actual = elem.input_value() if tag == 'INPUT' else elem.evaluate("el => el.value || el.innerText")
                    if actual and actual.strip():
                        log(f"  V Preenchido [{label}]: {actual[:40]!r}")
                        filled_fields.append(label)
                    else:
                        log(f"  X Falhou {label}", "WARN")
                        failed_fields.append(label)
                
                # Country select (primeiro SELECT nativo)
                self.fill_country_select()
                
                # Upload CV (FilePond)
                if self.profile.cv_file_path:
                    if self.upload_filepond_resume(self.profile.cv_file_path):
                        filled_fields.append("CV Upload")
                    else:
                        failed_fields.append("CV Upload")
                
                # 3 react-selects: Where/sole/contract
                if self.fill_react_select(2, self.profile.source_job or "LinkedIn - Sagan Recruitment Page Post"):
                    filled_fields.append("Where did you hear")
                if self.fill_react_select(3, self.profile.full_time_agree or "Yes"):
                    filled_fields.append("Sole full-time")
                if self.fill_react_select(4, self.profile.contract_type or "Full-time employment"):
                    filled_fields.append("Contract type")
                    
            except Exception as e:
                log(f"  ERRO preenchimento: {type(e).__name__}: {e}", "ERROR")
                shot = self.debug_screenshot(f"fill_error_{job_id}")'''

new_block = '''            # FORM Sagan em forms.saganrecruitment.com (campos SEM name)
            # Estrategia: buscar por TIPO DOM (type=text, type=email, type=tel) e por PLACEHOLDER
            # Os 4 primeiros campos sao FIXOS: Full Name -> Email -> Country (select) -> Phone (tel)
            try:
                # Helper: highlight laranja antes de preencher
                def highlight(elem):
                    try:
                        elem.evaluate("""el => {
                            el.scrollIntoView({behavior: "smooth", block: "center"});
                            el.style.outline = "4px solid #ff6600";
                            el.style.outlineOffset = "2px";
                            el.style.backgroundColor = "#fff3e0";
                        }""")
                        self.human_delay(0.8, 1.2)
                        elem.evaluate("""el => {
                            el.style.outline = "";
                            el.style.outlineOffset = "";
                            el.style.backgroundColor = "";
                        }""")
                    except Exception:
                        pass
                
                def fill_field(elem, value, label):
                    if not value:
                        return False
                    highlight(elem)
                    elem.click(force=True)
                    self.human_delay(0.3, 0.5)
                    # Para textareas, usar evaluate + dispatchEvent (fill() buga)
                    tag = elem.evaluate("el => el.tagName")
                    if tag == 'TEXTAREA':
                        elem.evaluate("""(el, val) => {
                            const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                            setter.call(el, val);
                            el.dispatchEvent(new Event('input', {bubbles: true}));
                            el.dispatchEvent(new Event('change', {bubbles: true}));
                        }""", value)
                    else:
                        elem.fill(value, force=True)
                    self.human_delay(0.4, 0.7)
                    # Verify
                    try:
                        if tag == 'TEXTAREA':
                            actual = elem.evaluate("el => el.value")
                        else:
                            actual = elem.input_value()
                        if actual and actual.strip():
                            log(f"  V Preenchido [{label}]: {actual[:40]!r}")
                            filled_fields.append(label)
                            return True
                    except Exception:
                        pass
                    log(f"  X Falhou {label}", "WARN")
                    failed_fields.append(label)
                    return False
                
                # ===== 4 PRIMEIROS CAMPOS FIXOS =====
                # 1) Full Name: primeiro <input type="text">
                full_name_val = self.profile.first_name + " " + self.profile.last_name
                all_text_inputs = self.page.query_selector_all('input[type="text"]')
                all_text_inputs = [e for e in all_text_inputs if e.is_visible()]
                if all_text_inputs:
                    fill_field(all_text_inputs[0], full_name_val, "full_name")
                
                # 2) Email: <input type="email">
                email_elem = self.page.query_selector('input[type="email"]')
                if email_elem and email_elem.is_visible():
                    fill_field(email_elem, self.profile.email, "email")
                
                # 3) Country: <select> nativo (PRIMEIRO select)
                if self.fill_country_select():
                    filled_fields.append("country")
                else:
                    failed_fields.append("country")
                
                # 4) Phone: <input type="tel">
                phone_elem = self.page.query_selector('input[type="tel"]')
                if phone_elem and phone_elem.is_visible():
                    fill_field(phone_elem, self.profile.phone, "phone")
                
                # ===== CAMPOS RESTANTES (ordem pode variar) =====
                # 5) Resume text: textarea que contem "resume" no label/placeholder
                textareas = self.page.query_selector_all('textarea')
                textareas = [t for t in textareas if t.is_visible()]
                
                # Resume textarea: label/placeholder com "resume"
                resume_text_val = self.profile.cover_letter or "Experienced professional with strong background in technology and automation."
                resume_filled = False
                for ta in textareas:
                    label_text = ta.evaluate("el => { const p = el.closest('div'); return p ? p.innerText.toLowerCase() : ''; }")
                    if 'resume' in label_text and 'copy' in label_text:
                        if fill_field(ta, resume_text_val, "resume_text"):
                            resume_filled = True
                            break
                if not resume_filled and textareas:
                    # Fallback: primeiro textarea
                    if fill_field(textareas[0], resume_text_val, "resume_text"):
                        resume_filled = True
                
                # 6) LinkedIn: input text (segundo, pos resume)
                # Buscar input que tem label "LinkedIn"
                remaining_text_inputs = all_text_inputs[1:] if len(all_text_inputs) > 1 else []
                linkedin_filled = False
                for inp in remaining_text_inputs:
                    label_text = inp.evaluate("el => { const p = el.closest('div'); return p ? p.innerText.toLowerCase() : ''; }")
                    if 'linkedin' in label_text:
                        if self.profile.linkedin_url:
                            if fill_field(inp, self.profile.linkedin_url, "linkedin"):
                                linkedin_filled = True
                        break
                
                # 7) Current salary: input com placeholder contendo "$" e "base"
                salary_filled_current = False
                for inp in self.page.query_selector_all('input[type="text"]'):
                    if not inp.is_visible():
                        continue
                    ph = inp.get_attribute('placeholder') or ''
                    if 'base' in ph.lower() and '$' in ph:
                        if fill_field(inp, str(self.profile.current_salary), "current_salary"):
                            salary_filled_current = True
                        break
                if not salary_filled_current:
                    for inp in remaining_text_inputs:
                        ph = inp.get_attribute('placeholder') or ''
                        if 'USD' in ph or 'usd' in ph:
                            if fill_field(inp, str(self.profile.current_salary), "current_salary"):
                                salary_filled_current = True
                            break
                
                # 8) Target salary: input com placeholder "USD"
                salary_filled_target = False
                for inp in self.page.query_selector_all('input[type="text"]'):
                    if not inp.is_visible():
                        continue
                    ph = inp.get_attribute('placeholder') or ''
                    if 'usd' in ph.lower() and 'base' not in ph.lower():
                        if fill_field(inp, str(self.profile.salary_expectation), "target_salary"):
                            salary_filled_target = True
                        break
                
                # 9) Story + Experience: textareas restantes (depois da resume_text)
                remaining_textareas = [t for t in textareas if not (t.evaluate("el => el.value") or '').strip()]
                story_val = self.profile.story or "I am a dedicated professional with strong analytical and problem-solving skills, seeking new opportunities to grow."
                exp_vals = [
                    self.profile.exp_1 or "I have extensive experience in this field with proven results.",
                    self.profile.exp_2 or "I have strong analytical and problem-solving skills.",
                    self.profile.exp_3 or "I am committed to quality and continuous improvement.",
                    self.profile.exp_4 or "I have a proven track record of meeting deadlines.",
                    self.profile.exp_5 or "I bring strong technical and communication skills.",
                ]
                
                # Story = primeiro textarea restante
                if remaining_textareas:
                    fill_field(remaining_textareas[0], story_val, "story")
                    # Experience = textareas seguintes
                    for i, ta in enumerate(remaining_textareas[1:]):
                        if i < len(exp_vals):
                            fill_field(ta, exp_vals[i], f"exp_{i+1}")
                
                # ===== UPLOAD CV (FilePond) =====
                if self.profile.cv_file_path:
                    if self.upload_filepond_resume(self.profile.cv_file_path):
                        filled_fields.append("CV Upload")
                    else:
                        failed_fields.append("CV Upload")
                
                # ===== 3 REACT-SELECTS (Where/sole/contract) POR ULTIMO =====
                if self.fill_react_select(2, self.profile.source_job or "LinkedIn - Sagan Recruitment Page Post"):
                    filled_fields.append("Where did you hear")
                else:
                    failed_fields.append("Where did you hear")
                if self.fill_react_select(3, self.profile.full_time_agree or "Yes"):
                    filled_fields.append("Sole full-time")
                else:
                    failed_fields.append("Sole full-time")
                if self.fill_react_select(4, self.profile.contract_type or "Full-time employment"):
                    filled_fields.append("Contract type")
                else:
                    failed_fields.append("Contract type")
                    
            except Exception as e:
                log(f"  ERRO preenchimento: {type(e).__name__}: {e}", "ERROR")
                shot = self.debug_screenshot(f"fill_error_{job_id}")'''

if old_block in content:
    content = content.replace(old_block, new_block)
    print("PATCH OK: bloco de preenchimento reescrito")
else:
    print("PATCH FAIL: bloco nao encontrado")

with open(filepath, 'w', encoding='utf-8', newline='') as f:
    f.write(content)
print(f"Saved: {len(content)} chars")