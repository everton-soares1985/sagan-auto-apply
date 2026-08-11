#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
SAGAN RECRUITMENT — AUTOMATED JOB APPLICATION SYSTEM v2.1 (SYNC)
=============================================================================
Versao sincrona usando Playwright Sync API para evitar problemas de asyncio no Windows.
"""

import argparse
import json
import os
import random
import sys
import time
import warnings
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    sync_playwright,
)

warnings.filterwarnings("ignore", category=ResourceWarning)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# =============================================================================
# CONFIGURACOES
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_JOBS_FILE = BASE_DIR / "sagan_jobs.json"
DEFAULT_FIELDS_FILE = BASE_DIR / "sagan_fields.csv"
DEFAULT_PROFILE_FILE = BASE_DIR / "candidate_profile.json"
DEFAULT_REPORT_FILE = BASE_DIR / "sagan_apply_report.json"
DEFAULT_LOG_FILE = BASE_DIR / "sagan_apply.log"

DEFAULT_TIMEOUT = 15000
NAV_TIMEOUT = 30000
HUMAN_DELAY_MIN = 0.4
HUMAN_DELAY_MAX = 1.5
BATCH_DELAY_MIN = 5.0
BATCH_DELAY_MAX = 12.0

CTA_SELECTORS = [
    "a:has-text('APPLY FOR THIS JOB')",
    "button:has-text('APPLY FOR THIS JOB')",
    "a:has-text('Apply Now')",
    "button:has-text('Apply Now')",
    "a:has-text('Apply for this Job')",
    ".jobsearch-applyjob-btn",
    "a[class*='apply' i]",
]

SUBMIT_BUTTON_SELECTORS = [
    "input[type='submit'][value*='Apply' i]",
    "input[type='submit'][value*='Submit' i]",
    "button[type='submit']",
    "input[type='submit']",
    "button:has-text('Apply')",
    ".job-apply-btn",
]

PROFILE_TO_FIELD_NAME = {
    "first_name":         "pt_user_fname",
    "last_name":          "pt_user_lname",
    "email":              "user_email",
    "phone":              "user_phone",
    "job_title":          "user_job_title",
    "current_salary":     "user_salary",
    "academic_level":     "academic-level",
    "age":                "Age",
    "salary_expectation": "salary",
    "gender":             "gender",
    "industry":           "industry",
    "cv_file_path":       "cand_woutreg_cv_file",
    "cover_letter":       "cand_cover_letter",
    "terms_cond_check":   "terms_cond_check",
}


# =============================================================================
# CLASSES DE DADOS
# =============================================================================
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
        )


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
    except Exception:
        pass
    print(line, flush=True)


# =============================================================================
# MOTOR DE APLICACAO (SYNC)
# =============================================================================
class SaganAutoApplier:
    def __init__(
        self,
        profile: CandidateProfile,
        headless: bool = True,
        execute_apply: bool = False,
        fill_only: bool = False,
    ):
        self.profile = profile
        self.headless = headless
        self.execute_apply = execute_apply
        self.fill_only = fill_only
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.results: List[ApplicationResult] = []

    def start(self):
        p = sync_playwright().start()
        self.browser = p.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        self.context = self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        self.page = self.context.new_page()
        self.page.set_default_timeout(DEFAULT_TIMEOUT)
        self.page.set_default_navigation_timeout(NAV_TIMEOUT)
        log("Browser iniciado com sucesso.")

    def close(self):
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            log("Browser fechado.")
        except Exception as e:
            log(f"Erro ao fechar browser: {e}", "WARN")

    def human_delay(self, min_sec: float = HUMAN_DELAY_MIN, max_sec: float = HUMAN_DELAY_MAX):
        delay = round(random.uniform(min_sec, max_sec), 2)
        time.sleep(delay)
        return delay

    def _scroll(self):
        for _ in range(3):
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.human_delay(0.3, 0.7)

    def debug_screenshot(self, prefix: str = "debug") -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = BASE_DIR / f"{prefix}_{ts}.png"
        try:
            self.page.screenshot(path=str(path), full_page=True)
            return str(path)
        except Exception as e:
            return f"erro_screenshot: {e}"

    def trigger_cta_modal(self) -> bool:
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
        return False

    def _build_selector_list(self, field_name: str, base_selector: str) -> List[str]:
        selectors = []
        if base_selector:
            selectors.append(base_selector)
        selectors.append(f"[name='{field_name}']")
        return selectors

    def fill_text_field(self, selectors: List[str], value: str) -> bool:
        if not value:
            return False
        for sel in selectors:
            try:
                elem = self.page.query_selector(sel)
                if elem:
                    elem.scroll_into_view_if_needed(timeout=3000)
                    elem.fill(value, force=True)
                    self.human_delay(0.3, 0.8)
                    return True
            except Exception:
                continue
        return False

    def select_option_fuzzy(self, selectors: List[str], target_value: str) -> bool:
        if not target_value:
            return False
        for sel in selectors:
            try:
                elem = self.page.query_selector(sel)
                if elem:
                    options = elem.query_selector_all("option")
                    if not options:
                        continue
                    best_val = None
                    target_lower = target_value.lower().strip()
                    for opt in options:
                        val = opt.get_attribute("value") or ""
                        text = opt.inner_text().strip()
                        if text.lower() == target_lower or val.lower() == target_lower:
                            best_val = val if val else text
                            break
                    if not best_val:
                        for opt in options:
                            val = opt.get_attribute("value") or ""
                            text = opt.inner_text().strip()
                            if target_lower in text.lower() or target_lower in val.lower():
                                best_val = val if val else text
                                break
                    if not best_val and len(options) > 1:
                        val1 = options[1].get_attribute("value")
                        if val1:
                            best_val = val1
                    if best_val:
                        elem.select_option(value=best_val, force=True)
                        self.human_delay(0.4, 0.9)
                        return True
            except Exception:
                continue
        return False

    def upload_file(self, selectors: List[str], file_path: str) -> bool:
        resolved = (BASE_DIR / file_path) if not os.path.isabs(file_path) else Path(file_path)
        if not resolved.exists():
            log(f"Arquivo de CV nao encontrado: {resolved}", "WARN")
            return False
        for sel in selectors:
            try:
                elem = self.page.query_selector(sel)
                if elem:
                    elem.set_input_files(str(resolved))
                    self.human_delay(0.6, 1.2)
                    return True
            except Exception:
                continue
        return False

    def check_terms(self, selectors: List[str]) -> bool:
        for sel in selectors:
            try:
                elem = self.page.query_selector(sel)
                if elem:
                    elem.evaluate(
                        "el => { el.checked = true; "
                        "el.dispatchEvent(new Event('change', {bubbles: true})); }"
                    )
                    self.human_delay(0.5, 1.0)
                    return True
            except Exception:
                continue
        return False

    def apply_to_job(self, job: dict) -> ApplicationResult:
        job_title = job.get("title", "Sem titulo")
        job_url = job.get("url", "")
        job_id = job.get("job_id", "unknown")
        form_fields = job.get("form_fields", [])

        log(f"Processando: {job_title}")
        log(f"  URL: {job_url}")

        filled_fields = []
        failed_fields = []
        result = ApplicationResult(
            job_id=job_id, job_title=job_title, url=job_url, status="DRY_RUN"
        )

        try:
            self.page.goto(job_url, wait_until="networkidle")
            self.human_delay(1.5, 3.0)
            self._scroll()
            self.trigger_cta_modal()

            fields_by_name = {f["name"]: f for f in form_fields}

            def get_selectors(profile_key: str) -> List[str]:
                field_name = PROFILE_TO_FIELD_NAME.get(profile_key)
                if not field_name or field_name not in fields_by_name:
                    return []
                base_sel = fields_by_name[field_name].get("selector", "")
                return self._build_selector_list(field_name, base_sel)

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
                if self.select_option_fuzzy(get_selectors(pk), val):
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
                failed_fields.append("Terms Checkbox")

            log(f"  Campos preenchidos ({len(filled_fields)}): {', '.join(filled_fields)}")
            if failed_fields:
                log(f"  Campos falharam ({len(failed_fields)}): {', '.join(failed_fields)}", "WARN")

            if not self.execute_apply:
                status_str = "FILLED" if self.fill_only else "DRY_RUN"
                msg = f"Modo seguro ({status_str}). Submissao nao realizada."
                log(f"  {msg}")
                result.status = status_str
                result.details = msg
                result.fields_filled = filled_fields
                result.fields_failed = failed_fields
                return result

            log("  Simulando revisao humana dos dados (hesitacao natural)...")
            self.human_delay(2.5, 5.0)

            log("  Enviando candidatura (Modo Ativo)...", "INFO")
            submitted = False
            for btn_sel in SUBMIT_BUTTON_SELECTORS:
                try:
                    btn = self.page.query_selector(btn_sel)
                    if btn:
                        btn.scroll_into_view_if_needed()
                        self.human_delay(0.5, 1.2)
                        btn.click(force=True)
                        submitted = True
                        log(f"  Clique no botao de envio: '{btn_sel}'")
                        break
                except Exception:
                    continue

            if submitted:
                if not self.headless:
                    log("  Navegador aberto por 10s para revisao visual...")
                    time.sleep(10)
                else:
                    self.human_delay(3.0, 6.0)
                log("  Candidatura enviada com sucesso!")
                result.status = "SUBMITTED"
                result.details = "Formulario enviado com sucesso."
                result.fields_filled = filled_fields
                result.fields_failed = failed_fields
            else:
                log("  Botao de envio nao encontrado.", "WARN")
                shot = self.debug_screenshot(f"submit_fail_{job_id}")
                result.status = "FAILED"
                result.details = f"Botao submit nao localizado. Screenshot: {shot}"
                result.fields_filled = filled_fields
                result.fields_failed = failed_fields

        except Exception as e:
            log(f"  Erro ao processar vaga {job_id}: {e}", "ERROR")
            shot = self.debug_screenshot(f"error_{job_id}")
            result.status = "FAILED"
            result.details = f"Erro: {e} | Screenshot: {shot}"
            result.fields_filled = filled_fields
            result.fields_failed = failed_fields

        return result


# =============================================================================
# FUNCOES AUXILIARES
# =============================================================================
def load_jobs(jobs_path: Path, filter_keyword: Optional[str], limit: int) -> List[dict]:
    if not jobs_path.exists():
        raise FileNotFoundError(f"Banco de vagas nao encontrado: {jobs_path}")
    data = json.loads(jobs_path.read_text(encoding="utf-8"))
    all_jobs = data.get("jobs", [])
    if filter_keyword:
        kw = filter_keyword.lower()
        all_jobs = [j for j in all_jobs if kw in j.get("title", "").lower() or kw in j.get("description", "").lower()]
        log(f"Vagas filtradas por '{filter_keyword}': {len(all_jobs)}")
    return all_jobs[:limit]


def self_check(profile_path: Path, jobs_path: Path, fields_path: Path):
    print("=" * 70)
    print("SAGAN RECRUITMENT — DIAGNOSTICO (SELF-CHECK) v2.1")
    print("=" * 70)

    print(f"\n[1] Perfil do Candidato: {profile_path.name}")
    if profile_path.exists():
        try:
            profile = CandidateProfile.load_from_json(profile_path)
            print(f"  Nome:        {profile.first_name} {profile.last_name}")
            print(f"  Email:       {profile.email}")
            print(f"  Phone:       {profile.phone}")
            print(f"  Job Title:   {profile.job_title}")
            print(f"  CV File:     {profile.cv_file_path}")
            cv_resolved = (BASE_DIR / profile.cv_file_path) if not os.path.isabs(profile.cv_file_path) else Path(profile.cv_file_path)
            if cv_resolved.exists():
                print(f"  CV Status:   Encontrado ({cv_resolved.stat().st_size} bytes)")
            else:
                print(f"  CV Status:   NAO ENCONTRADO em {cv_resolved}")
            print(f"  Status: OK")
        except Exception as e:
            print(f"  Status: ERRO - {e}")
    else:
        print(f"  Status: NAO ENCONTRADO. Crie o arquivo {profile_path}")

    print(f"\n[2] Banco de Vagas: {jobs_path.name}")
    if jobs_path.exists():
        try:
            data = json.loads(jobs_path.read_text(encoding="utf-8"))
            total = len(data.get("jobs", []))
            print(f"  Total de vagas: {total}")
            print(f"  Status: OK")
        except Exception as e:
            print(f"  Status: ERRO - {e}")
    else:
        print(f"  Status: NAO ENCONTRADO.")

    print(f"\n[3] Ambiente")
    print(f"  Python: {sys.version.split()[0]}")
    try:
        import playwright
        print(f"  Playwright: OK")
    except ImportError:
        print(f"  Playwright: NAO INSTALADO.")

    print("\n" + "=" * 70)


# =============================================================================
# CLI PRINCIPAL
# =============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Sagan Recruitment — Automated Application System v2.1 (SYNC)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--self-check", action="store_true", help="Executa diagnostico")
    parser.add_argument("--dry-run", action="store_true", help="Simula preenchimento")
    parser.add_argument("--fill-only", action="store_true", help="Preenche formulario visivel")
    parser.add_argument("--execute-apply", action="store_true", help="EXECUTA ENVIO REAL")
    parser.add_argument("--limit", type=int, default=1, help="Numero de vagas")
    parser.add_argument("--job-url", type=str, help="URL de vaga especifica")
    parser.add_argument("--filter-keyword", type=str, help="Filtrar por palavra-chave")
    parser.add_argument("--no-headless", action="store_true", help="Navegador visivel")
    parser.add_argument("--profile", type=str, default=str(DEFAULT_PROFILE_FILE), help="Caminho do perfil")

    args = parser.parse_args()

    profile_path = Path(args.profile)
    jobs_path = DEFAULT_JOBS_FILE
    fields_path = DEFAULT_FIELDS_FILE

    if args.self_check:
        self_check(profile_path, jobs_path, fields_path)
        return

    if not profile_path.exists():
        print(f"Erro: Perfil '{profile_path}' nao encontrado.")
        sys.exit(1)

    profile = CandidateProfile.load_from_json(profile_path)
    headless = not args.no_headless

    jobs_to_process: List[dict] = []
    if args.job_url:
        slug = args.job_url.rstrip("/").split("/")[-1] if args.job_url else "direct_url"
        jobs_to_process.append({
            "title": f"Vaga Direta ({slug})",
            "url": args.job_url,
            "job_id": slug,
            "form_fields": [],
        })
    else:
        try:
            jobs_to_process = load_jobs(jobs_path, args.filter_keyword, args.limit)
        except FileNotFoundError as e:
            print(f"Erro: {e}")
            sys.exit(1)

    print("=" * 70)
    print("SAGAN RECRUITMENT — AUTOMATED APPLIER v2.1 (SYNC)")
    print("=" * 70)
    print(f"Candidato:   {profile.first_name} {profile.last_name} ({profile.email})")
    print(f"Modo:        {'VISIVEL' if not headless else 'HEADLESS'}")
    action = (
        "SUBMISSAO REAL" if args.execute_apply
        else ("PREENCHIMENTO VISIVEL" if args.fill_only else "DRY-RUN SEGURO")
    )
    print(f"Acao:        {action}")
    print(f"Vagas:       {len(jobs_to_process)}")
    print("=" * 70)

    if args.execute_apply:
        print("\n[!] MODO SUBMISSAO REAL ATIVADO.")
        print(f"[!] Voce esta prestes a enviar {len(jobs_to_process)} candidatura(s) REAIS.")
        confirm = input("Digite 'CONFIRMO' para prosseguir: ").strip()
        if confirm != "CONFIRMO":
            print("Operacao cancelada.")
            return

    applier = SaganAutoApplier(
        profile=profile,
        headless=headless,
        execute_apply=args.execute_apply,
        fill_only=args.fill_only,
    )

    try:
        applier.start()
        for i, j in enumerate(jobs_to_process, 1):
            print(f"\n--- Vaga {i}/{len(jobs_to_process)} ---")
            res = applier.apply_to_job(j)
            applier.results.append(res)

            if i < len(jobs_to_process):
                batch_delay = round(random.uniform(BATCH_DELAY_MIN, BATCH_DELAY_MAX), 2)
                log(f"  Aguardando {batch_delay}s antes da proxima vaga...")
                time.sleep(batch_delay)

        report_data = {
            "timestamp": datetime.now().isoformat(),
            "mode": "EXECUTE_APPLY" if args.execute_apply else ("FILL_ONLY" if args.fill_only else "DRY_RUN"),
            "total_processed": len(applier.results),
            "results": [r.to_dict() for r in applier.results],
        }
        DEFAULT_REPORT_FILE.write_text(
            json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        log(f"Relatorio salvo em: {DEFAULT_REPORT_FILE}")

    finally:
        applier.close()


if __name__ == "__main__":
    main()
