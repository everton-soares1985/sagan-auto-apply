#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
SAGAN RECRUITMENT — AUTOMATED JOB APPLICATION SYSTEM v2.1 (SYNC)
=============================================================================
Versao sincrona usando Playwright Sync API para evitar problemas de asyncio no Windows.
"""

import argparse
from contextlib import contextmanager
import json
import os
import random
import sqlite3
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
DEFAULT_APPLICATIONS_DB = BASE_DIR / "sagan_applications.sqlite3"

DEFAULT_TIMEOUT = 24000
NAV_TIMEOUT = 35000
HUMAN_DELAY_MIN = 0.9
HUMAN_DELAY_MAX = 2.2
BATCH_DELAY_MIN = 8.0
BATCH_DELAY_MAX = 17.0
JOB_PAGE_SETTLE_DELAY_MIN = 4.0
JOB_PAGE_SETTLE_DELAY_MAX = 6.5
FORM_PAGE_SETTLE_DELAY_MIN = 5.0
FORM_PAGE_SETTLE_DELAY_MAX = 8.0
FIELD_TO_FIELD_DELAY_MIN = 2.0
FIELD_TO_FIELD_DELAY_MAX = 4.5

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
    "button[data-cy='button-component']",
    "div.fillout-field-button button",
    "button:has-text('Submit')",
    "input[type='submit'][value*='Apply' i]",
    "input[type='submit'][value*='Submit' i]",
    "button[type='submit']",
    "input[type='submit']",
    "button:has-text('Apply')",
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
    vocaroo_url: str = ""
    github_url: str = ""
    source_job: str = "LinkedIn - Sagan Recruitment Page Post"
    full_time_agree: str = "Yes"
    contract_type: str = "Full-time employment"
    story: str = ""
    why_company: str = ""
    background_full: str = ""
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
            vocaroo_url=data.get("vocaroo_url", ""),
            github_url=data.get("github_url", ""),
            source_job=data.get("source_job", "LinkedIn - Sagan Recruitment Page Post"),
            full_time_agree=data.get("full_time_agree", "Yes"),
            contract_type=data.get("contract_type", "Full-time employment"),
            story=data.get("story", ""),
            why_company=data.get("why_company", ""),
            background_full=data.get("background_full", ""),
            exp_1=data.get("exp_1", ""),
            exp_2=data.get("exp_2", ""),
            exp_3=data.get("exp_3", ""),
            exp_4=data.get("exp_4", ""),
            exp_5=data.get("exp_5", ""),
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


class ApplicationStore:
    """Registro local de candidaturas confirmadas e vagas que exigem revisao."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _ensure_schema(self):
        with self._connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS submitted_applications (
                    job_url TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    job_title TEXT NOT NULL,
                    submitted_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS review_applications (
                    job_url TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    job_title TEXT NOT NULL,
                    failure_status TEXT NOT NULL,
                    failed_fields_json TEXT NOT NULL DEFAULT '[]',
                    details TEXT NOT NULL DEFAULT '',
                    screenshot_path TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                )
                """
            )

    def was_submitted(self, job_url: str) -> bool:
        self._ensure_schema()
        with self._connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM submitted_applications WHERE job_url = ?",
                (job_url,),
            ).fetchone()
        return row is not None

    def filter_pending_jobs(self, jobs: List[dict]) -> List[dict]:
        """Retorna somente vagas que nao foram enviadas nem separadas para revisao."""
        self._ensure_schema()
        with self._connection() as conn:
            blocked_urls = {
                row[0]
                for row in conn.execute("SELECT job_url FROM submitted_applications")
            }
            blocked_urls.update(
                row[0]
                for row in conn.execute("SELECT job_url FROM review_applications")
            )
        return [job for job in jobs if job.get("url", "") not in blocked_urls]

    def record_submitted(self, job_id: str, job_title: str, job_url: str):
        self._ensure_schema()
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO submitted_applications (job_url, job_id, job_title, submitted_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(job_url) DO NOTHING
                """,
                (job_url, job_id, job_title, datetime.now().isoformat()),
            )
            conn.execute("DELETE FROM review_applications WHERE job_url = ?", (job_url,))

    def record_needs_review(
        self,
        job_id: str,
        job_title: str,
        job_url: str,
        failure_status: str,
        failed_fields: List[str],
        details: str,
        screenshot_path: str = "",
    ):
        """Separa uma vaga que o site nao aceitou para revisao manual posterior."""
        self._ensure_schema()
        with self._connection() as conn:
            already_submitted = conn.execute(
                "SELECT 1 FROM submitted_applications WHERE job_url = ?", (job_url,)
            ).fetchone()
            if already_submitted:
                return
            conn.execute(
                """
                INSERT INTO review_applications (
                    job_url, job_id, job_title, failure_status, failed_fields_json,
                    details, screenshot_path, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_url) DO UPDATE SET
                    job_id = excluded.job_id,
                    job_title = excluded.job_title,
                    failure_status = excluded.failure_status,
                    failed_fields_json = excluded.failed_fields_json,
                    details = excluded.details,
                    screenshot_path = excluded.screenshot_path,
                    updated_at = excluded.updated_at
                """,
                (
                    job_url,
                    job_id,
                    job_title,
                    failure_status,
                    json.dumps(failed_fields, ensure_ascii=False),
                    details,
                    screenshot_path,
                    datetime.now().isoformat(),
                ),
            )

    def list_review_jobs(self) -> List[dict]:
        self._ensure_schema()
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT job_id, job_title, job_url, failure_status, failed_fields_json,
                       details, screenshot_path, updated_at
                FROM review_applications
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [
            {
                "job_id": row[0],
                "title": row[1],
                "url": row[2],
                "failure_status": row[3],
                "failed_fields": json.loads(row[4]),
                "details": row[5],
                "screenshot_path": row[6],
                "updated_at": row[7],
                "form_fields": [],
            }
            for row in rows
        ]


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
        review_failed: bool = False,
    ):
        self.profile = profile
        self.headless = headless
        self.execute_apply = execute_apply
        self.fill_only = fill_only
        self.review_failed = review_failed
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.results: List[ApplicationResult] = []
        self.application_store = ApplicationStore(DEFAULT_APPLICATIONS_DB)

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

    def fill_react_select(self, react_select_index: int, value: str, short_value: str = "") -> bool:
        """Preenche um react-select-N-input: click + type + clica na 1a opcao do dropdown.
        
        FIX Bug 2: Busca a opcao exclusivamente dentro do container do react-select correto,
        evitando capturar opcoes de outros react-selects abertos na pagina.
        Para textos longos (ex: "LinkedIn - Sagan..."), usa short_value para filtrar melhor.
        """
        if not value:
            return False
        # Para textos longos, digitar apenas o inicio para o react-select filtrar
        # ex: 'LinkedIn - Sagan Recruitment Page Post' -> digitar 'LinkedIn'
        type_value = short_value if short_value else value
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
                    const wrap = el.closest('[class*="control"]') || el.parentElement;
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
                    const wrap = el.closest('[class*="control"]') || el.parentElement;
                    if (wrap) {{ wrap.style.outline = ''; wrap.style.outlineOffset = ''; }}
                }}
            """)
            elem.click(force=True)
            self.human_delay(0.4, 0.7)
            elem.fill(type_value, force=True)
            # Aguardar dropdown abrir
            self.human_delay(1.0, 1.5)
            # Estrategia 1: clicar na opcao pelo ID padrao do react-select
            clicked = False
            try:
                opt = self.page.query_selector(f"#react-select-{react_select_index}-option-0")
                if opt and opt.is_visible():
                    opt.click(force=True)
                    self.human_delay(0.5, 0.8)
                    clicked = True
                    log(f"  V React-select-{react_select_index} (click option-0) = {value!r}")
            except Exception:
                pass
            # Estrategia 2: buscar opcoes DENTRO do container especifico deste react-select
            if not clicked:
                clicked_via_js = self.page.evaluate(f"""
                    () => {{
                        // Encontrar o input do react-select correto
                        const input = document.querySelector('#react-select-{react_select_index}-input');
                        if (!input) return false;
                        // Subir ate o container raiz do react-select
                        const container = input.closest('[class*="container"]') || input.closest('[class*="react-select"]');
                        if (!container) return false;
                        // Buscar o menu/listbox dentro desse container especifico
                        const menu = container.querySelector('[class*="menu"]') || container.querySelector('[role="listbox"]');
                        if (!menu) return false;
                        // Clicar na primeira opcao visivel
                        const opts = menu.querySelectorAll('[class*="option"]');
                        for (const opt of opts) {{
                            const style = window.getComputedStyle(opt);
                            if (style.display !== 'none' && opt.offsetParent !== null) {{
                                opt.click();
                                return true;
                            }}
                        }}
                        return false;
                    }}
                """)
                if clicked_via_js:
                    self.human_delay(0.5, 0.8)
                    clicked = True
                    log(f"  V React-select-{react_select_index} (click JS menu) = {value!r}")
            # Estrategia 3 (fallback): pressionar Enter
            if not clicked:
                elem.press("Enter")
                self.human_delay(0.5, 0.9)
                log(f"  V React-select-{react_select_index} (Enter fallback) = {value!r}")
            return True
        except Exception as e:
            log(f"  X Erro react-select-{react_select_index}: {type(e).__name__}", "WARN")
            return False
    
    def fill_country_select(self) -> bool:
        """Preenche o campo de pais (Brazil).

        FIX DEFINITIVO: O campo Country no forms.saganrecruitment.com NAO e um
        <select> nativo — e um input[type="text"] com aria-label="Your Country of Residence".
        Selector: input[aria-label*="Country"] ou input[data-cy="input-component"][aria-label*="Country"]
        Valor: preencher com texto "Brazil" normalmente.
        """
        try:
            # Seletores para o campo de pais (input de texto, nao select)
            country_selectors = [
                'input[aria-label*="Country"]',
                'input[aria-label*="country"]',
                'input[data-cy="input-component"][aria-label*="Country"]',
                'input[placeholder*="Country"]',
                'input[placeholder*="country"]',
            ]

            elem = None
            used_sel = ""
            for sel in country_selectors:
                e = self.page.query_selector(sel)
                if e and e.is_visible():
                    elem = e
                    used_sel = sel
                    break

            if not elem:
                log("  X Country: input de texto nao encontrado", "WARN")
                return False

            elem.evaluate("""el => {
                el.scrollIntoView({behavior: 'smooth', block: 'center'});
                el.style.outline = '4px solid #ff6600';
                el.style.outlineOffset = '2px';
                el.style.backgroundColor = '#fff3e0';
            }""")
            self.human_delay(0.8, 1.2)
            elem.evaluate("""el => {
                el.style.outline = '';
                el.style.outlineOffset = '';
                el.style.backgroundColor = '';
            }""")
            elem.click(force=True)
            self.human_delay(0.3, 0.5)
            elem.fill("Brazil", force=True)
            self.human_delay(0.4, 0.7)
            # Verificar se preencheu
            actual = ""
            try:
                actual = elem.input_value()
            except Exception:
                actual = elem.evaluate("el => el.value")
            if actual and "brazil" in actual.lower():
                log(f"  V Country = {actual!r} (via {used_sel})")
                return True
            else:
                log(f"  X Country: valor apos fill = {actual!r}", "WARN")
                return False
        except Exception as e:
            log(f"  X Erro country fill: {type(e).__name__}: {e}", "WARN")
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
            inputs = self.page.query_selector_all('input[type="file"]')
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
            log(f"Erro ao fechar browser: {e}", "WARN")

    def human_delay(self, min_sec: float = HUMAN_DELAY_MIN, max_sec: float = HUMAN_DELAY_MAX):
        delay = round(random.uniform(min_sec, max_sec), 2)
        time.sleep(delay)
        return delay

    def _scroll(self):
        """Scroll visivel com smooth para debug visual"""
        for i in range(3):
            self.page.evaluate("""
                window.scrollTo({top: document.body.scrollHeight, behavior: "smooth"});
            """)
            self.human_delay(0.6, 1.0)

    def debug_screenshot(self, prefix: str = "debug") -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = BASE_DIR / f"{prefix}_{ts}.png"
        try:
            self.page.screenshot(path=str(path), full_page=True)
            return str(path)
        except Exception as e:
            return f"erro_screenshot: {e}"

    def navigate_to_apply_form(self) -> bool:
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
                    self.human_delay(FORM_PAGE_SETTLE_DELAY_MIN, FORM_PAGE_SETTLE_DELAY_MAX)
                    return True
                # Senao, clicar
                btn.scroll_into_view_if_needed()
                self.human_delay(0.8, 1.5)
                btn.click(force=True)
                self.human_delay(FORM_PAGE_SETTLE_DELAY_MIN, FORM_PAGE_SETTLE_DELAY_MAX)
                # Checar se navegou
                if "forms.saganrecruitment.com" in self.page.url:
                    return True
            except Exception as e:
                log(f"  ? Tentativa {sel}: {type(e).__name__}", "WARN")
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
        return False

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
                    elem.evaluate("""el => {
                        el.scrollIntoView({behavior: "smooth", block: "center"});
                        el.style.outline = "4px solid #ff6600";
                        el.style.outlineOffset = "2px";
                    }""")
                    self.human_delay(0.8, 1.2)
                    elem.evaluate("el => { el.style.outline = ''; el.style.outlineOffset = ''; }")
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

        if self.execute_apply and self.application_store.was_submitted(job_url):
            msg = "Vaga ja registrada como enviada no banco local. Pulando."
            log(f"  {msg}", "WARN")
            result.status = "SKIPPED_ALREADY_SUBMITTED"
            result.details = msg
            return result

        try:
            self.page.goto(job_url, wait_until="networkidle")
            self.human_delay(JOB_PAGE_SETTLE_DELAY_MIN, JOB_PAGE_SETTLE_DELAY_MAX)
            self._scroll()
            self.navigate_to_apply_form()

            fields_by_name = {f["name"]: f for f in form_fields}

            def get_selectors(profile_key: str) -> List[str]:
                field_name = PROFILE_TO_FIELD_NAME.get(profile_key)
                if not field_name or field_name not in fields_by_name:
                    return []
                base_sel = fields_by_name[field_name].get("selector", "")
                return self._build_selector_list(field_name, base_sel)

            # FORM Sagan em forms.saganrecruitment.com (campos SEM name)
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
                            self.human_delay(FIELD_TO_FIELD_DELAY_MIN, FIELD_TO_FIELD_DELAY_MAX)
                            return True
                    except Exception:
                        pass
                    log(f"  X Falhou {label}", "WARN")
                    failed_fields.append(label)
                    return False
                
                # ===== PREENCHIMENTO SEMANTICO (SaganFieldEngine) =====
                # Detecta cada campo pelo seu label/aria-label/placeholder (nao pela posicao).
                # Campos fixos (nome, email, pais, telefone, linkedin, salario, vocaroo)
                # sao respondidos direto do candidate_profile.json.
                # Campos dinamicos (perguntas abertas nao mapeadas) chamam Gemini Flash via IA.
                # React-selects sao tratados separadamente abaixo.
                try:
                    from sagan_ai_field_engine import SaganFieldEngine
                    engine = SaganFieldEngine(
                        page=self.page,
                        profile=vars(self.profile) if hasattr(self.profile, '__dict__') else self.profile.__dict__,
                        job_title=job_title,
                        job_url=job_url,
                    )
                    engine_result = engine.fill_all_fields()
                    filled_fields.extend(engine_result.get("filled", []))
                    failed_fields.extend(engine_result.get("failed", []))
                    skipped_engine = engine_result.get("skipped", [])
                    if skipped_engine:
                        log(f"  Campos ignorados pelo engine ({len(skipped_engine)}): {', '.join(skipped_engine[:5])}")
                except ImportError:
                    log("  [WARN] sagan_ai_field_engine.py nao encontrado, usando preenchimento legado", "WARN")
                    # === FALLBACK LEGADO (caso o engine nao esteja disponivel) ===
                    full_name_val = self.profile.first_name + " " + self.profile.last_name
                    all_text_inputs = self.page.query_selector_all('input[type="text"]')
                    all_text_inputs = [e for e in all_text_inputs if e.is_visible()]
                    if all_text_inputs:
                        fill_field(all_text_inputs[0], full_name_val, "full_name")
                    email_elem = self.page.query_selector('input[type="email"]')
                    if email_elem and email_elem.is_visible():
                        fill_field(email_elem, self.profile.email, "email")
                    if self.fill_country_select():
                        filled_fields.append("country")
                    else:
                        failed_fields.append("country")
                    phone_elem = self.page.query_selector('input[type="tel"]')
                    if phone_elem and phone_elem.is_visible():
                        fill_field(phone_elem, self.profile.phone, "phone")
                
                # ===== UPLOAD CV (FilePond) — sempre separado =====
                if self.profile.cv_file_path:
                    if self.upload_filepond_resume(self.profile.cv_file_path):
                        filled_fields.append("CV Upload")
                    else:
                        failed_fields.append("CV Upload")
                
                # ===== 3 REACT-SELECTS (Where/sole/contract) — sempre separado =====
                if self.fill_react_select(2, self.profile.source_job or "LinkedIn - Sagan Recruitment Page Post", short_value="LinkedIn"):
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
                shot = self.debug_screenshot(f"fill_error_{job_id}")

            log(f"  Campos preenchidos ({len(filled_fields)}): {', '.join(filled_fields)}")
            if failed_fields:
                log(f"  Campos falharam ({len(failed_fields)}): {', '.join(failed_fields)}", "WARN")

            if self.review_failed:
                log("  REVISAO MANUAL: complete os campos restantes e envie no navegador aberto.")
                log("  Quando o site confirmar o envio, digite ENVIADO no terminal.")
                result.fields_filled = filled_fields
                result.fields_failed = failed_fields
                confirmed = input("Digite 'ENVIADO' apos a confirmacao do site (ou ENTER para manter na fila): ").strip()
                if confirmed == "ENVIADO":
                    self.application_store.record_submitted(job_id, job_title, job_url)
                    result.status = "SUBMITTED_MANUAL"
                    result.details = "Candidatura confirmada manualmente pelo usuario."
                    log("  Vaga marcada como enviada e removida da fila de revisao.")
                else:
                    result.status = "NEEDS_REVIEW"
                    result.details = "Mantida na fila de revisao manual."
                    log("  Vaga mantida na fila de revisao manual.", "WARN")
                return result

            if not self.execute_apply:
                status_str = "FILLED" if self.fill_only else "DRY_RUN"
                msg = f"Modo seguro ({status_str}). Submissao nao realizada."
                log(f"  {msg}")
                result.status = status_str
                result.details = msg
                result.fields_filled = filled_fields
                result.fields_failed = failed_fields
                # Pausa visual: deixa o navegador aberto para revisao manual
                if not self.headless:
                    log("=" * 60)
                    log("  NAVEGADOR ABERTO PARA REVISAO. Verifique o formulario.")
                    log("  Pressione ENTER no terminal para fechar o navegador.")
                    log("=" * 60)
                    input()
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
                # Aguardar para o form processar a resposta
                log("  Aguardando resposta do formulario...")
                time.sleep(3)

                # ===== VERIFICACAO REAL DE SUCESSO =====
                # Detecta erros de validacao que indicam que o form NAO foi aceito
                url_apos = self.page.url
                texto_pagina = ""
                try:
                    texto_pagina = self.page.inner_text("body") or ""
                except Exception:
                    pass

                # Indicadores de FALHA (form rejeitado com campos obrigatorios vazios)
                ERROS_VALIDACAO = [
                    "field is required",
                    "required field",
                    "this field is required",
                    "please fill",
                    "please complete",
                    "campo obrigatorio",
                    "campo requerido",
                    "must be filled",
                ]
                texto_lower = texto_pagina.lower()
                erros_encontrados = [e for e in ERROS_VALIDACAO if e in texto_lower]

                # Indicadores de SUCESSO: o formulario deve mostrar confirmacao real.
                MENSAGENS_SUCESSO = [
                    "thank you",
                    "application received",
                    "successfully submitted",
                    "application submitted",
                    "you have applied",
                    "submission received",
                    "obrigado",
                    "candidatura recebida",
                ]
                mensagem_sucesso = any(m in texto_lower for m in MENSAGENS_SUCESSO)

                if erros_encontrados:
                    # Form REJEITOU — campos obrigatorios ainda vazios
                    shot = self.debug_screenshot(f"submit_validation_fail_{job_id}")
                    log(f"  SUBMIT REJEITADO pelo formulario. Erros de validacao detectados: {erros_encontrados}", "WARN")
                    log(f"  URL atual: {url_apos}", "WARN")
                    log(f"  Screenshot: {shot}", "WARN")
                    result.status = "SUBMIT_VALIDATION_FAILED"
                    result.details = (
                        f"Formulario rejeitou o envio (campos obrigatorios vazios). "
                        f"Erros: {erros_encontrados}. Screenshot: {shot}"
                    )
                    result.fields_filled = filled_fields
                    result.fields_failed = failed_fields
                    self.application_store.record_needs_review(
                        job_id, job_title, job_url, result.status, failed_fields,
                        result.details, str(shot),
                    )
                    log("  Vaga adicionada a fila de revisao manual.", "WARN")
                elif mensagem_sucesso:
                    log(f"  Candidatura ENVIADA com sucesso! URL: {url_apos}")
                    self.application_store.record_submitted(job_id, job_title, job_url)
                    result.status = "SUBMITTED"
                    result.details = "Formulario enviado e confirmado pelo site."
                    result.fields_filled = filled_fields
                    result.fields_failed = failed_fields
                else:
                    # Ambiguo: nao detectou erro nem confirmacao — tira screenshot para revisao
                    shot = self.debug_screenshot(f"submit_ambiguous_{job_id}")
                    log(f"  Status ambiguo apos submit. Sem confirmacao clara. Screenshot: {shot}", "WARN")
                    result.status = "SUBMIT_UNCONFIRMED"
                    result.details = (
                        f"Botao clicado mas nao foi possivel confirmar envio. "
                        f"Revisar screenshot: {shot}"
                    )
                    result.fields_filled = filled_fields
                    result.fields_failed = failed_fields
                    self.application_store.record_needs_review(
                        job_id, job_title, job_url, result.status, failed_fields,
                        result.details, str(shot),
                    )
                    log("  Vaga adicionada a fila de revisao manual.", "WARN")
            else:
                log("  Botao de envio nao encontrado.", "WARN")
                shot = self.debug_screenshot(f"submit_fail_{job_id}")
                result.status = "FAILED"
                result.details = f"Botao submit nao localizado. Screenshot: {shot}"
                result.fields_filled = filled_fields
                result.fields_failed = failed_fields
                self.application_store.record_needs_review(
                    job_id, job_title, job_url, result.status, failed_fields,
                    result.details, str(shot),
                )
                log("  Vaga adicionada a fila de revisao manual.", "WARN")

        except Exception as e:
            log(f"  Erro ao processar vaga {job_id}: {e}", "ERROR")
            shot = self.debug_screenshot(f"error_{job_id}")
            result.status = "FAILED"
            result.details = f"Erro: {e} | Screenshot: {shot}"
            result.fields_filled = filled_fields
            result.fields_failed = failed_fields
            self.application_store.record_needs_review(
                job_id, job_title, job_url, result.status, failed_fields,
                result.details, str(shot),
            )
            log("  Vaga adicionada a fila de revisao manual.", "WARN")

        return result


# =============================================================================
# FUNCOES AUXILIARES
# =============================================================================
def load_jobs(jobs_path: Path, filter_keyword: Optional[str], limit: Optional[int]) -> List[dict]:
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
    parser.add_argument("--review-failed", action="store_true", help="Abre vagas pendentes para revisao e envio manual")
    parser.add_argument("--list-review", action="store_true", help="Lista a fila de vagas que exigem revisao")
    parser.add_argument("--limit", type=int, default=1, help="Numero de vagas")
    parser.add_argument("--job-url", type=str, help="URL de vaga especifica")
    parser.add_argument("--filter-keyword", type=str, help="Filtrar por palavra-chave")
    parser.add_argument("--no-headless", action="store_true", help="Navegador visivel")
    parser.add_argument("--profile", type=str, default=str(DEFAULT_PROFILE_FILE), help="Caminho do perfil")

    args = parser.parse_args()

    if args.review_failed and args.execute_apply:
        parser.error("--review-failed nao pode ser usado com --execute-apply")
    if args.review_failed and not args.no_headless:
        parser.error("--review-failed exige --no-headless para voce revisar no navegador")

    store = ApplicationStore(DEFAULT_APPLICATIONS_DB)
    if args.list_review:
        review_jobs = store.list_review_jobs()
        print(f"Fila de revisao manual: {len(review_jobs)} vaga(s)")
        for index, job in enumerate(review_jobs, 1):
            fields = ", ".join(job["failed_fields"]) or "nao identificado"
            print(f"{index}. {job['title']} [{job['failure_status']}]")
            print(f"   Campos: {fields}")
            print(f"   URL: {job['url']}")
        return

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
    if args.review_failed:
        jobs_to_process = store.list_review_jobs()
        if args.filter_keyword:
            keyword = args.filter_keyword.lower()
            jobs_to_process = [
                job for job in jobs_to_process
                if keyword in job["title"].lower() or keyword in job["url"].lower()
            ]
        jobs_to_process = jobs_to_process[:args.limit]
    elif args.job_url:
        slug = args.job_url.rstrip("/").split("/")[-1] if args.job_url else "direct_url"
        jobs_to_process.append({
            "title": f"Vaga Direta ({slug})",
            "url": args.job_url,
            "job_id": slug,
            "form_fields": [],
        })
    else:
        try:
            all_matching_jobs = load_jobs(jobs_path, args.filter_keyword, limit=None)
            if args.execute_apply:
                pending_jobs = store.filter_pending_jobs(all_matching_jobs)
                skipped_count = len(all_matching_jobs) - len(pending_jobs)
                if skipped_count:
                    log(f"Vagas ja enviadas removidas do lote: {skipped_count}")
                jobs_to_process = pending_jobs[:args.limit]
            else:
                jobs_to_process = all_matching_jobs[:args.limit]
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
        else ("REVISAO MANUAL" if args.review_failed else ("PREENCHIMENTO VISIVEL" if args.fill_only else "DRY-RUN SEGURO"))
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
        review_failed=args.review_failed,
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
            "mode": "EXECUTE_APPLY" if args.execute_apply else ("REVIEW_FAILED" if args.review_failed else ("FILL_ONLY" if args.fill_only else "DRY_RUN")),
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
