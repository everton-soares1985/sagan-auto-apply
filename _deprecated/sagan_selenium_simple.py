"""
SAGAN AUTOMATION v3 - Selenium Edition
Versao usando Selenium para evitar problemas de permissao do Playwright no Windows.
"""

import json
import os
import random
import sys
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
import tempfile
import uuid
from typing import List, Optional
import argparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except:
        pass

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_JOBS_FILE = BASE_DIR / "sagan_jobs.json"
DEFAULT_PROFILE_FILE = BASE_DIR / "candidate_profile.json"
DEFAULT_REPORT_FILE = BASE_DIR / "sagan_apply_report.json"
DEFAULT_LOG_FILE = BASE_DIR / "sagan_apply.log"

PROFILE_TO_FIELD_NAME = {
    "first_name": "pt_user_fname",
    "last_name": "pt_user_lname",
    "email": "user_email",
    "phone": "user_phone",
    "job_title": "user_job_title",
    "current_salary": "user_salary",
    "academic_level": "academic-level",
    "age": "Age",
    "salary_expectation": "salary",
    "gender": "gender",
    "industry": "industry",
    "cv_file_path": "cand_woutreg_cv_file",
    "cover_letter": "cand_cover_letter",
    "terms_cond_check": "terms_cond_check",
}

@dataclass
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
    def load_from_json(cls, path: Path):
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(**{k: data.get(k, "") for k in cls.__annotations__})

@dataclass
class ApplicationResult:
    job_id: str
    job_title: str
    url: str
    status: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    details: str = ""
    fields_filled: List[str] = field(default_factory=list)
    fields_failed: List[str] = field(default_factory=list)
    
    def to_dict(self):
        return asdict(self)

def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    try:
        with open(DEFAULT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass
    print(line, flush=True)

class SaganSeleniumApplier:
    def __init__(self, profile: CandidateProfile, headless: bool = True, 
                 execute_apply: bool = False, fill_only: bool = False):
        self.profile = profile
        self.headless = headless
        self.execute_apply = execute_apply
        self.fill_only = fill_only
        self.driver = None
        self.results = []
    
    def start(self):
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        # User data dir unico para evitar conflitos
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.set_page_load_timeout(30)
        self.driver.implicitly_wait(5)
        log("Browser Selenium iniciado.")
    
    def close(self):
        if self.driver:
            self.driver.quit()
            log("Browser fechado.")
    
    def human_delay(self, min_s=0.4, max_s=1.5):
        time.sleep(round(random.uniform(min_s, max_s), 2))
    
    def scroll(self):
        for _ in range(3):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            self.human_delay(0.3, 0.7)
    
    def find_and_fill(self, selectors: List[str], value: str) -> bool:
        if not value:
            return False
        for sel in selectors:
            try:
                # Tenta CSS primeiro
                if sel.startswith("[") or sel.startswith("#") or sel.startswith("."):
                    elem = self.driver.find_element(By.CSS_SELECTOR, sel)
                else:
                    elem = self.driver.find_element(By.NAME, sel)
                elem.clear()
                elem.send_keys(value)
                self.human_delay(0.3, 0.8)
                return True
            except:
                continue
        return False
    
    def find_and_select(self, selectors: List[str], target: str) -> bool:
        if not target:
            return False
        for sel in selectors:
            try:
                if sel.startswith("[") or sel.startswith("#") or sel.startswith("."):
                    elem = self.driver.find_element(By.CSS_SELECTOR, sel)
                else:
                    elem = self.driver.find_element(By.NAME, sel)
                select = Select(elem)
                target_lower = target.lower().strip()
                # Try exact match
                for opt in select.options:
                    if opt.text.lower().strip() == target_lower:
                        select.select_by_visible_text(opt.text)
                        self.human_delay(0.4, 0.9)
                        return True
                # Try partial match
                for opt in select.options:
                    if target_lower in opt.text.lower():
                        select.select_by_visible_text(opt.text)
                        self.human_delay(0.4, 0.9)
                        return True
                # Fallback: second option
                if len(select.options) > 1:
                    select.select_by_index(1)
                    self.human_delay(0.4, 0.9)
                    return True
            except:
                continue
        return False
    
    def find_and_upload(self, selectors: List[str], file_path: str) -> bool:
        resolved = (BASE_DIR / file_path) if not os.path.isabs(file_path) else Path(file_path)
        if not resolved.exists():
            log(f"CV nao encontrado: {resolved}", "WARN")
            return False
        for sel in selectors:
            try:
                if sel.startswith("[") or sel.startswith("#") or sel.startswith("."):
                    elem = self.driver.find_element(By.CSS_SELECTOR, sel)
                else:
                    elem = self.driver.find_element(By.NAME, sel)
                elem.send_keys(str(resolved))
                self.human_delay(0.6, 1.2)
                return True
            except:
                continue
        return False
    
    def find_and_check(self, selectors: List[str]) -> bool:
        for sel in selectors:
            try:
                if sel.startswith("[") or sel.startswith("#") or sel.startswith("."):
                    elem = self.driver.find_element(By.CSS_SELECTOR, sel)
                else:
                    elem = self.driver.find_element(By.NAME, sel)
                if not elem.is_selected():
                    elem.click()
                self.human_delay(0.5, 1.0)
                return True
            except:
                continue
        return False
    
    def _build_selectors(self, profile_key: str, fields_map: dict) -> List[str]:
        field_name = PROFILE_TO_FIELD_NAME.get(profile_key)
        if not field_name or field_name not in fields_map:
            return []
        base_sel = fields_map[field_name].get("selector", "")
        return [base_sel, f"[name='{field_name}']", field_name] if base_sel else [f"[name='{field_name}']", field_name]
    
    def apply_to_job(self, job: dict) -> ApplicationResult:
        job_title = job.get("title", "Sem titulo")
        job_url = job.get("url", "")
        job_id = job.get("job_id", "unknown")
        form_fields = job.get("form_fields", [])
        
        log(f"Processando: {job_title}")
        log(f"  URL: {job_url}")
        
        filled = []
        failed = []
        result = ApplicationResult(job_id=job_id, job_title=job_title, url=job_url, status="DRY_RUN")
        
        try:
            self.driver.get(job_url)
            self.human_delay(2, 4)
            self.scroll()
            
            fields_map = {f["name"]: f for f in form_fields}
            
            # Text fields
            text_map = {
                "First Name": ("first_name", self.profile.first_name),
                "Last Name": ("last_name", self.profile.last_name),
                "Email": ("email", self.profile.email),
                "Phone": ("phone", self.profile.phone),
                "Job Title": ("job_title", self.profile.job_title),
                "Current Salary": ("current_salary", self.profile.current_salary),
                "Salary Expectation": ("salary_expectation", self.profile.salary_expectation),
            }
            for label, (pk, val) in text_map.items():
                if self.find_and_fill(self._build_selectors(pk, fields_map), val):
                    filled.append(label)
                elif val:
                    failed.append(label)
            
            # Selects
            select_map = {
                "Academic Level": ("academic_level", self.profile.academic_level),
                "Age": ("age", self.profile.age),
                "Gender": ("gender", self.profile.gender),
                "Industry": ("industry", self.profile.industry),
            }
            for label, (pk, val) in select_map.items():
                if self.find_and_select(self._build_selectors(pk, fields_map), val):
                    filled.append(label)
                elif val:
                    failed.append(label)
            
            # CV Upload
            if self.profile.cv_file_path:
                if self.find_and_upload(self._build_selectors("cv_file_path", fields_map), self.profile.cv_file_path):
                    filled.append("CV Upload")
                else:
                    failed.append("CV Upload")
            
            # Cover Letter
            if self.profile.cover_letter:
                if self.find_and_fill(self._build_selectors("cover_letter", fields_map), self.profile.cover_letter):
                    filled.append("Cover Letter")
                else:
                    failed.append("Cover Letter")
            
            # Terms checkbox
            if self.find_and_check(self._build_selectors("terms_cond_check", fields_map)):
                filled.append("Terms Checkbox")
            else:
                failed.append("Terms Checkbox")
            
            log(f"  Preenchidos ({len(filled)}): {', '.join(filled)}")
            if failed:
                log(f"  Falharam ({len(failed)}): {', '.join(failed)}", "WARN")
            
            if not self.execute_apply:
                status = "FILLED" if self.fill_only else "DRY_RUN"
                result.status = status
                result.details = f"Modo seguro ({status})."
                result.fields_filled = filled
                result.fields_failed = failed
                return result
            
            # Submit (real mode)
            log("  Enviando candidatura...", "INFO")
            self.human_delay(2.5, 5.0)
            submit_selectors = [
                "input[type='submit'][value*='Apply']",
                "button[type='submit']",
                "input[type='submit']"
            ]
            submitted = False
            for sel in submit_selectors:
                try:
                    btn = self.driver.find_element(By.CSS_SELECTOR, sel)
                    btn.click()
                    submitted = True
                    log(f"  Clicou em: {sel}")
                    break
                except:
                    continue
            
            if submitted:
                if not self.headless:
                    time.sleep(10)
                else:
                    self.human_delay(3, 6)
                result.status = "SUBMITTED"
                result.details = "Enviado com sucesso."
                result.fields_filled = filled
                result.fields_failed = failed
            else:
                result.status = "FAILED"
                result.details = "Botao submit nao encontrado."
                result.fields_filled = filled
                result.fields_failed = failed
        
        except Exception as e:
            log(f"  Erro: {e}", "ERROR")
            result.status = "FAILED"
            result.details = str(e)
            result.fields_filled = filled
            result.fields_failed = failed
        
        return result

def main():
    parser = argparse.ArgumentParser(description="Sagan Automation v3 (Selenium)")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fill-only", action="store_true")
    parser.add_argument("--execute-apply", action="store_true")
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--job-url", type=str)
    parser.add_argument("--filter-keyword", type=str)
    parser.add_argument("--no-headless", action="store_true")
    parser.add_argument("--profile", type=str, default=str(DEFAULT_PROFILE_FILE))
    
    args = parser.parse_args()
    
    if args.self_check:
        print("Self-check basico:")
        print(f"  Profile: {DEFAULT_PROFILE_FILE.exists()}")
        print(f"  Jobs: {DEFAULT_JOBS_FILE.exists()}")
        return
    
    profile = CandidateProfile.load_from_json(Path(args.profile))
    
    jobs = []
    if args.job_url:
        slug = args.job_url.rstrip("/").split("/")[-1]
        jobs.append({"title": f"Vaga ({slug})", "url": args.job_url, "job_id": slug, "form_fields": []})
    else:
        data = json.loads(DEFAULT_JOBS_FILE.read_text(encoding="utf-8"))
        all_jobs = data.get("jobs", [])
        if args.filter_keyword:
            kw = args.filter_keyword.lower()
            all_jobs = [j for j in all_jobs if kw in j.get("title", "").lower()]
        jobs = all_jobs[:args.limit]
    
    print("=" * 70)
    print("SAGAN AUTOMATION v3 (Selenium)")
    print("=" * 70)
    print(f"Candidato: {profile.first_name} {profile.last_name}")
    print(f"Modo: {'VISIVEL' if args.no_headless else 'HEADLESS'}")
    print(f"Acao: {'SUBMIT REAL' if args.execute_apply else ('FILL' if args.fill_only else 'DRY-RUN')}")
    print(f"Vagas: {len(jobs)}")
    print("=" * 70)
    
    if args.execute_apply:
        confirm = input("Digite 'CONFIRMO' para envio real: ").strip()
        if confirm != "CONFIRMO":
            print("Cancelado.")
            return
    
    applier = SaganSeleniumApplier(
        profile=profile,
        headless=not args.no_headless,
        execute_apply=args.execute_apply,
        fill_only=args.fill_only
    )
    
    try:
        applier.start()
        for i, job in enumerate(jobs, 1):
            print(f"\n--- Vaga {i}/{len(jobs)} ---")
            res = applier.apply_to_job(job)
            applier.results.append(res)
            if i < len(jobs):
                delay = round(random.uniform(5, 12), 2)
                log(f"  Aguardando {delay}s...")
                time.sleep(delay)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "mode": "EXECUTE" if args.execute_apply else ("FILL" if args.fill_only else "DRY_RUN"),
            "total": len(applier.results),
            "results": [r.to_dict() for r in applier.results]
        }
        DEFAULT_REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        log(f"Relatorio: {DEFAULT_REPORT_FILE}")
    
    finally:
        applier.close()

if __name__ == "__main__":
    main()
