filepath = r'C:\Users\User\OneDrive\Área de Trabalho\CODEX_OMNIROUTE\sagan_auto_apply.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================================
# PATCH 1: trigger_cta -> navigate_to_apply_form
# Troca click+modal por: pegar href do CTA e navegar ate forms.saganrecruitment.com
# ============================================================
old_cta = '''    def trigger_cta_modal(self) -> bool:
        for cta in CTA_SELECTORS:
            try:
                btn = self.page.query_selector(cta)
                if btn:
                    btn.scroll_into_view_if_needed()
                    self.human_delay(0.8, 2.0)
                    btn.click(force=True)
                    self.human_delay(1.2, 2.5)
                    log(f"Modal aberto via CTA: {cta}")
                    return True
            except Exception:
                continue
        return False'''

new_cta = '''    def navigate_to_apply_form(self) -> bool:
        """Extrai href do botao APPLY FOR THIS JOB e navega ate o forms.saganrecruitment.com"""
        for sel in [
            "a:has-text('APPLY FOR THIS JOB')",
            "a:has-text('APPLY NOW')",
            "a:has-text('Apply Now')",
            "a:has-text('Apply for this Job')",
        ]:
            try:
                btn = self.page.query_selector(sel)
                if not btn:
                    continue
                href = btn.get_attribute("href")
                if not href:
                    continue
                # Se for link externo, navegar ate ele
                if "forms.saganrecruitment.com" in href or "sagan" in href:
                    log(f"  -> Navegando para: {href[:80]}")
                    self.page.goto(href, wait_until="networkidle")
                    self.human_delay(2.0, 3.5)
                    return True
                # Senao, clicar
                btn.scroll_into_view_if_needed()
                self.human_delay(0.8, 1.5)
                btn.click(force=True)
                self.human_delay(2.0, 3.5)
                # Checar se navegou
                if "forms.saganrecruitment.com" in self.page.url:
                    return True
            except Exception as e:
                log(f"  ? Tentativa {sel}: {type(e).__name__}", "WARN")
                continue
        return False'''

if old_cta in content:
    content = content.replace(old_cta, new_cta)
    print("PATCH 1 OK: trigger_cta_modal -> navigate_to_apply_form")
else:
    print("PATCH 1 FAIL: not found")

# ============================================================
# PATCH 2: Reescrever apply_to_job para nova estrategia
# - Remover select_map antigo
# - Mapear por labels (sem usar selectors do sagan_fields.csv)
# - Usar fill_react_select_field
# ============================================================
old_apply = '''            text_map = {
                "First Name": ("first_name", self.profile.first_name),
                "Last Name": ("last_name", self.profile.last_name),
                "Email": ("email", self.profile.email),
                "Phone": ("phone", self.profile.phone),
                "Job Title": ("job_title", self.profile.job_title),
                "Current Salary": ("current_salary", self.profile.current_salary),
                "Salary Expectation": ("salary_expectation", self.profile.salary_expectation),
            }
            for label, (pk, val) in text_map.items():
                if self.fill_text_field(get_selectors(pk), val):
                    filled_fields.append(label)
                elif val:
                    failed_fields.append(label)

            select_map = {
                "Academic Level": ("academic_level", self.profile.academic_level),
                "Age": ("age", self.profile.age),
                "Gender": ("gender", self.profile.gender),
                "Industry": ("industry", self.profile.industry),
            }
            for label, (pk, val) in select_map.items():
                # Tentar Selectize primeiro, fallback para select nativo
                success = self.fill_selectize_field(get_selectors(pk), val)
                if not success:
                    success = self.select_option_fuzzy(get_selectors(pk), val)
                if success:
                    filled_fields.append(label)
                elif val:
                    failed_fields.append(label)

            if self.profile.cv_file_path:
                if self.upload_file(get_selectors("cv_file_path"), self.profile.cv_file_path):
                    filled_fields.append("CV Upload")
                else:
                    failed_fields.append("CV Upload")

            if self.profile.cover_letter:
                if self.fill_text_field(get_selectors("cover_letter"), self.profile.cover_letter):
                    filled_fields.append("Cover Letter")
                else:
                    failed_fields.append("Cover Letter")

            if self.check_terms(get_selectors("terms_cond_check")):
                filled_fields.append("Terms Checkbox")
            else:
                failed_fields.append("Terms Checkbox")'''

new_apply = '''            # FORM SAgan em forms.saganrecruitment.com (campos SEM name)
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

if old_apply in content:
    content = content.replace(old_apply, new_apply)
    print("PATCH 2 OK: apply_to_job rewritten")
else:
    print("PATCH 2 FAIL")

# ============================================================
# PATCH 3: Adicionar metodos auxiliares (fill_react_select, fill_country_select, upload_filepond_resume)
# ============================================================
old_close = '''    def close(self):
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            log("Browser fechado.")
        except Exception as e:
            log(f"Erro ao fechar browser: {e}", "WARN")'''

new_close = '''    def fill_react_select(self, react_select_index: int, value: str) -> bool:
        """Preenche um react-select-N-input (click + type + Enter)."""
        if not value:
            return False
        try:
            sel = f"#react-select-{react_select_index}-input"
            elem = self.page.query_selector(sel)
            if not elem:
                log(f"  ? react-select {react_select_index} nao encontrado", "WARN")
                return False
            # SCROLL + HIGHLIGHT
            self.page.evaluate(f"""
                const el = document.querySelector('{sel}');
                if (el) {{
                    const wrap = el.closest('[class*=\"control\"]') || el.parentElement;
                    if (wrap) {{
                        wrap.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                        wrap.style.outline = '4px solid #ff6600';
                        wrap.style.outlineOffset = '2px';
                    }}
                }}
            """)
            self.human_delay(1.0, 1.3)
            self.page.evaluate(f"""
                const el = document.querySelector('{sel}');
                if (el) {{
                    const wrap = el.closest('[class*=\"control\"]') || el.parentElement;
                    if (wrap) {{ wrap.style.outline = ''; wrap.style.outlineOffset = ''; }}
                }}
            """)
            elem.click(force=True)
            self.human_delay(0.4, 0.7)
            elem.fill(value, force=True)
            self.human_delay(0.4, 0.7)
            elem.press("Enter")
            self.human_delay(0.5, 0.9)
            log(f"  V React-select-{react_select_index} = {value!r}")
            return True
        except Exception as e:
            log(f"  X Erro react-select-{react_select_index}: {type(e).__name__}", "WARN")
            return False
    
    def fill_country_select(self) -> bool:
        """Preenche o select de pais (Brazil)."""
        try:
            sel_elem = self.page.query_selector("select")
            if not sel_elem:
                return False
            sel_elem.evaluate("""el => {
                el.scrollIntoView({behavior: 'smooth', block: 'center'});
                el.style.outline = '4px solid #ff6600';
                el.style.outlineOffset = '2px';
            }""")
            self.human_delay(0.8, 1.2)
            sel_elem.evaluate("el => { el.style.outline = ''; el.style.outlineOffset = ''; }")
            sel_elem.select_option(value="Brazil", force=True)
            self.human_delay(0.5, 0.9)
            log(f"  V Country = Brazil")
            return True
        except Exception as e:
            log(f"  X Erro country select: {type(e).__name__}", "WARN")
            return False
    
    def upload_filepond_resume(self, file_path: str) -> bool:
        """Upload via FilePond (input[type=file])."""
        import os
        from pathlib import Path
        resolved = (BASE_DIR / file_path) if not os.path.isabs(file_path) else Path(file_path)
        if not resolved.exists():
            log(f"  X CV nao encontrado: {resolved}", "WARN")
            return False
        try:
            # FilePond usa input[type=file]
            inputs = self.page.query_selector_all('input[type=\"file\"]')
            for inp in inputs:
                if inp.is_visible() or True:  # FilePond input pode estar oculto
                    inp.evaluate("el => { el.scrollIntoView({behavior: 'smooth', block: 'center'}); }")
                    self.human_delay(0.5, 0.8)
                    inp.set_input_files(str(resolved))
                    self.human_delay(1.5, 2.5)
                    log(f"  V CV uploaded: {resolved.name}")
                    return True
            log(f"  X Nenhum input[type=file] encontrado", "WARN")
            return False
        except Exception as e:
            log(f"  X Erro upload: {type(e).__name__}: {e}", "WARN")
            return False

    def close(self):
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            log("Browser fechado.")
        except Exception as e:
            log(f"Erro ao fechar browser: {e}", "WARN")'''

if old_close in content:
    content = content.replace(old_close, new_close)
    print("PATCH 3 OK: metodos auxiliares adicionados")
else:
    print("PATCH 3 FAIL")

# ============================================================
# PATCH 4: Atualizar CandidateProfile + load_from_json com novos campos
# ============================================================
old_profile = '''@dataclass
class CandidateProfile:
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    job_title: str = ""
    current_salary: str = ""
    academic_level: str = ""
    age: str = ""
    salary_expectation: str = ""
    gender: str = ""
    industry: str = ""
    cv_file_path: str = ""
    cover_letter: str = ""

    @classmethod
    def load_from_json(cls, path: Path) -> "CandidateProfile":
        if not path.exists():
            raise FileNotFoundError(f"Arquivo de perfil nao encontrado: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            job_title=data.get("job_title", ""),
            current_salary=data.get("current_salary", ""),
            academic_level=data.get("academic_level", ""),
            age=data.get("age", ""),
            salary_expectation=data.get("salary_expectation", ""),
            gender=data.get("gender", ""),
            industry=data.get("industry", ""),
            cv_file_path=data.get("cv_file_path", ""),
            cover_letter=data.get("cover_letter", ""),
        )'''

new_profile = '''@dataclass
class CandidateProfile:
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    email: str = ""
    phone: str = ""
    job_title: str = ""
    current_salary: str = ""
    academic_level: str = ""
    age: str = ""
    salary_expectation: str = ""
    gender: str = ""
    industry: str = ""
    cv_file_path: str = ""
    cover_letter: str = ""
    # Novos campos para forms.saganrecruitment.com
    linkedin_url: str = ""
    source_job: str = "LinkedIn - Sagan Recruitment Page Post"
    full_time_agree: str = "Yes"
    contract_type: str = "Full-time employment"
    story: str = ""
    exp_1: str = ""
    exp_2: str = ""
    exp_3: str = ""
    exp_4: str = ""
    exp_5: str = ""

    @classmethod
    def load_from_json(cls, path: Path) -> "CandidateProfile":
        if not path.exists():
            raise FileNotFoundError(f"Arquivo de perfil nao encontrado: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        first = data.get("first_name", "")
        last = data.get("last_name", "")
        return cls(
            first_name=first,
            last_name=last,
            full_name=data.get("full_name", f"{first} {last}".strip()),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            job_title=data.get("job_title", ""),
            current_salary=data.get("current_salary", ""),
            academic_level=data.get("academic_level", ""),
            age=data.get("age", ""),
            salary_expectation=data.get("salary_expectation", ""),
            gender=data.get("gender", ""),
            industry=data.get("industry", ""),
            cv_file_path=data.get("cv_file_path", ""),
            cover_letter=data.get("cover_letter", ""),
            linkedin_url=data.get("linkedin_url", ""),
            source_job=data.get("source_job", "LinkedIn - Sagan Recruitment Page Post"),
            full_time_agree=data.get("full_time_agree", "Yes"),
            contract_type=data.get("contract_type", "Full-time employment"),
            story=data.get("story", ""),
            exp_1=data.get("exp_1", ""),
            exp_2=data.get("exp_2", ""),
            exp_3=data.get("exp_3", ""),
            exp_4=data.get("exp_4", ""),
            exp_5=data.get("exp_5", ""),
        )'''

if old_profile in content:
    content = content.replace(old_profile, new_profile)
    print("PATCH 4 OK: CandidateProfile expanded")
else:
    print("PATCH 4 FAIL")

# ============================================================
# PATCH 5: Mudar chamada trigger_cta_modal -> navigate_to_apply_form
# ============================================================
content = content.replace("self.trigger_cta_modal()", "self.navigate_to_apply_form()")
print("PATCH 5 OK: trigger_cta_modal() -> navigate_to_apply_form()")

with open(filepath, 'w', encoding='utf-8', newline='') as f:
    f.write(content)
print(f"\nALL DONE. File saved: {len(content)} chars")