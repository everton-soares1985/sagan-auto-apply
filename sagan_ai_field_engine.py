# =============================================================================
# SAGAN AI FIELD ENGINE — v1.0
# Módulo de detecção semântica de campos + chamada Gemini Flash para perguntas dinâmicas
#
# ARQUITETURA (baseada no Wellfound GrowthTech AIOS):
#   Python detecta campos por label (aria-label, placeholder, texto do label HTML)
#   Python decide o tipo de campo e qual resposta usar
#   IA (Gemini Flash / OpenRouter) gera texto APENAS para campos dinâmicos não mapeados
#   Python valida a resposta da IA antes de digitar
#   Python preenche. IA nunca clica, navega ou submete.
#
# DEPENDÊNCIAS:
#   pip install playwright
#   OPENROUTER_API_KEY ou GEMINI_API_KEY no ambiente (ou .env na pasta do script)
#
# USO:
#   Importado por sagan_auto_apply.py
#   Instanciar SaganFieldEngine(page, profile, job_title) e chamar fill_all_fields()
# =============================================================================

from __future__ import annotations

import json
import os
import queue
import re
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# CONFIGURAÇÕES DA API
# ---------------------------------------------------------------------------
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY_ENV = "OPENROUTER_API_KEY"

# Modelos em ordem de preferência (primário + fallbacks, fornecedores diferentes)
AI_MODELS = [
    "google/gemini-2.5-flash-lite",   # Primário: rápido, barato, JSON sólido
    "minimax/minimax-m2.7",            # Fallback 1: fornecedor diferente
    "qwen/qwen3-235b-a22b-2507",       # Fallback 2: fornecedor diferente
]

AI_TEMPERATURE = 0.2
AI_MAX_TOKENS = 800
AI_SOCKET_TIMEOUT = 30
AI_TOTAL_TIMEOUT = 60

# ---------------------------------------------------------------------------
# MAPEAMENTO SEMÂNTICO DE CAMPOS (Python puro, sem IA)
# ---------------------------------------------------------------------------
# Cada categoria tem palavras-chave que batem contra:
#   - aria-label do input
#   - placeholder do input
#   - Texto do label HTML mais próximo
#   - Texto completo do container do campo

FIELD_CATEGORIES = {
    "full_name":         ["full name", "your name", "nome completo"],
    "email":             ["email", "e-mail", "correio"],
    "country":           ["country of residence", "your country", "country"],
    "phone":             ["phone", "telefone", "mobile", "cel"],
    "resume_text":       ["paste.*resume", "copy.*resume", "resume text", "unstructured text", "paste your cv", "paste the text of your resume"],
    "vocaroo":           ["vocaroo", "voca.ro", "60-second", "60 second", "audio introduction", "voice introduction",
                          "paste the vocaroo", "vocaroo link", "60 second introduction", "record a 60"],
    "linkedin":          ["linkedin", "linked in", "linkedin profile", "paste linkedin"],
    "github":            ["github", "git hub", "portfolio", "website", "portifolio"],
    "current_salary":    ["current salary", "current compensation", "base salary", "current base", "current monthly compensation"],
    "target_salary":     ["salary expectation", "desired salary", "expected salary", "target salary", "target monthly compensation"],
    "job_title":         ["current title", "job title", "current position", "your title"],
    "story":             ["tell us about yourself", "your story", "about yourself", "introduce yourself", "background",
                          "story (150", "your story (150"],
    "why_company":       ["why.*company", "why.*interested", "what interests you", "why do you want"],
    "experience_tech":   ["experience with", "technical experience", "relevant experience", "describe your experience",
                          "experience preparing", "experience sourcing", "experience leading", "experience managing"],
    "experience_detail": ["tell us more", "additional information", "anything else", "more about"],
    "source_job":        ["how did you hear", "where did you hear", "how did you find", "referral"],
    "full_time_agree":   ["sole.*full.*time", "full.time.*sole", "only job", "primary employment"],
    "contract_type":     ["contract type", "employment type", "work type", "type of contract"],
}


def detectar_categoria_campo(label: str, placeholder: str = "", aria_label: str = "") -> str:
    """Classifica um campo pela categoria semântica baseando-se no texto visível.
    
    REGRA: Keywords de categorias fixas (email, phone, etc.) só batem se o label
    for CURTO (<= 80 chars) ou a keyword aparecer no INICIO do texto.
    Perguntas longas (>80 chars) são sempre 'unknown' a menos que contenham
    keywords de categorias de perguntas abertas (experience_tech, story, etc.)
    """
    # Usa aria-label ou placeholder se disponível (labels curtos e precisos)
    label_curto = aria_label or placeholder or ""
    label_full = label.strip()
    
    # Texto principal para matching
    texto = " ".join([label_curto, label_full]).casefold().strip()
    
    if not texto:
        return "unknown"
    
    # Categorias FIXAS — só batem em labels curtos (<= 80 chars) para evitar
    # falsos positivos em perguntas longas (ex: "through phone calls" → phone)
    CATEGORIAS_FIXAS = {
        "full_name", "email", "country", "phone", "resume_text",
        "vocaroo", "linkedin", "github", "current_salary", "target_salary",
        "job_title", "source_job", "full_time_agree", "contract_type",
    }
    
    for categoria, palavras_chave in FIELD_CATEGORIES.items():
        for kw in palavras_chave:
            if re.search(kw, texto):
                # Para categorias fixas: só aceita match se o label for curto (< 80 chars)
                # ou se a keyword aparecer nos primeiros 60 chars do texto
                if categoria in CATEGORIAS_FIXAS:
                    label_eh_curto = len(label_full.strip()) <= 80
                    kw_no_inicio = bool(re.search(kw, texto[:60]))
                    if not (label_eh_curto or kw_no_inicio):
                        continue  # Ignora: keyword está dentro de uma pergunta longa
                return categoria
    
    return "unknown"


# ---------------------------------------------------------------------------
# SANITIZAÇÃO DO PERFIL PARA A IA
# (baseado em sanitizar_perfil_freelance_para_ia do Wellfound)
# ---------------------------------------------------------------------------

def sanitizar_perfil_para_ia(profile: dict) -> dict:
    """Remove dados sensíveis do perfil antes de enviar à IA.
    
    A IA nunca recebe: email, telefone, URLs, dados pessoais exatos.
    Recebe apenas: nome, cargo, habilidades e contexto narrativo.
    """
    CAMPOS_BLOQUEADOS = {
        "email", "phone", "cv_file_path", "linkedin_url", "github_url",
        "vocaroo_url", "current_salary", "salary_expectation",
    }
    perfil_limpo = {}
    for k, v in profile.items():
        if k in CAMPOS_BLOQUEADOS:
            continue
        if isinstance(v, str):
            # Remove URLs
            v = re.sub(r"https?://\S+", "[URL_REMOVIDA]", v)
            # Remove emails
            v = re.sub(r"\b[\w.+-]+@[\w-]+\.\w+\b", "[EMAIL_REMOVIDO]", v)
            # Remove telefones
            v = re.sub(r"\+?\d[\d\s\-().]{7,}\d", "[TELEFONE_REMOVIDO]", v)
        perfil_limpo[k] = v
    return perfil_limpo


# ---------------------------------------------------------------------------
# CHAMADA À API (baseado em chamar_openrouter_benchmark do Wellfound)
# ---------------------------------------------------------------------------

def _obter_api_key() -> str:
    """Lê a chave da API do ambiente ou do .env local."""
    key = os.environ.get(OPENROUTER_API_KEY_ENV, "").strip()
    if not key:
        env_file = Path(__file__).parent / ".env"
        if env_file.exists():
            for linha in env_file.read_text(encoding="utf-8").splitlines():
                if linha.startswith(f"{OPENROUTER_API_KEY_ENV}="):
                    key = linha.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    return key


def _executar_request_ai(modelo: str, api_key: str, payload: dict, system_prompt: str) -> dict:
    """Executa HTTP POST bloqueante para o OpenRouter."""
    corpo = {
        "model": modelo,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        "temperature": AI_TEMPERATURE,
        "max_tokens": AI_MAX_TOKENS,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        OPENROUTER_API_URL,
        data=json.dumps(corpo).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-Title": "Sagan Auto Apply AI Engine",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=AI_SOCKET_TIMEOUT) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
        choices = dados.get("choices", [])
        if not choices:
            return {"raw": "", "error": "choices_missing"}
        conteudo = choices[0].get("message", {}).get("content", "")
        return {"raw": str(conteudo), "error": ""}
    except urllib.error.HTTPError as exc:
        try:
            detalhe = exc.read().decode("utf-8", errors="replace")[:200]
        except OSError:
            detalhe = ""
        return {"raw": "", "error": f"http_{exc.code}:{detalhe}"}
    except Exception as exc:
        return {"raw": "", "error": type(exc).__name__}


def chamar_ai(payload: dict, system_prompt: str) -> tuple[dict | None, str]:
    """Chama OpenRouter com timeout real via thread daemon + fallback entre modelos.
    
    Retorna (resposta_json, modelo_usado) ou (None, '') em caso de falha total.
    Arquitetura idêntica ao chamar_openrouter_benchmark do Wellfound.
    """
    api_key = _obter_api_key()
    if not api_key:
        return None, ""
    
    for modelo in AI_MODELS:
        fila: queue.Queue[dict] = queue.Queue(maxsize=1)
        
        def worker(m=modelo):
            resultado = _executar_request_ai(m, api_key, payload, system_prompt)
            try:
                fila.put_nowait(resultado)
            except queue.Full:
                pass
        
        t = threading.Thread(target=worker, daemon=True, name=f"sagan-ai-{modelo}")
        inicio = time.perf_counter()
        t.start()
        t.join(AI_TOTAL_TIMEOUT)
        latencia = round(time.perf_counter() - inicio, 2)
        
        if t.is_alive():
            print(f"  [AI] Timeout ({AI_TOTAL_TIMEOUT}s) em {modelo}, tentando fallback...")
            continue
        
        try:
            resultado = fila.get_nowait()
        except queue.Empty:
            continue
        
        if resultado.get("error"):
            print(f"  [AI] Erro em {modelo}: {resultado['error']}, tentando fallback...")
            continue
        
        # Extrair JSON da resposta
        resposta, erro_json = extrair_json_resposta(resultado.get("raw", ""))
        if resposta:
            print(f"  [AI] Resposta em {latencia}s via {modelo}")
            return resposta, modelo
        
        print(f"  [AI] JSON inválido de {modelo} ({erro_json}), tentando fallback...")
    
    return None, ""


def extrair_json_resposta(texto: str) -> tuple[dict | None, str]:
    """Extrai JSON da resposta da IA, lidando com cercas markdown.
    
    Idêntico ao extrair_json_resposta_modelo do Wellfound.
    """
    bruto = texto.strip()
    if not bruto:
        return None, "empty_response"
    
    candidatos = [bruto]
    # Remove cercas de código markdown
    if bruto.startswith("```"):
        sem_fence = re.sub(r"^```(?:json)?\s*", "", bruto, flags=re.IGNORECASE)
        sem_fence = re.sub(r"\s*```$", "", sem_fence).strip()
        candidatos.append(sem_fence)
    # Tenta extrair substring JSON
    inicio = bruto.find("{")
    fim = bruto.rfind("}")
    if inicio >= 0 and fim > inicio:
        candidatos.append(bruto[inicio:fim + 1])
    
    for c in candidatos:
        try:
            dados = json.loads(c)
            if isinstance(dados, dict):
                return dados, ""
        except json.JSONDecodeError:
            continue
    
    return None, "json_decode_error"


# ---------------------------------------------------------------------------
# GERADOR DE RESPOSTA PARA CAMPOS DINÂMICOS
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_SAGAN = (
    "You are the writing brain for a Sagan Recruitment application assistant.\n\n"
    "You do NOT control the browser.\n"
    "You do NOT click buttons.\n"
    "You do NOT submit applications.\n"
    "You ONLY write one concise, honest English answer for the specific form field question provided.\n\n"
    "Rules:\n"
    "1. Use only the sanitized job context and candidate profile provided.\n"
    "2. Personalize to the role and company when context is available.\n"
    "3. Do not include phone, email, salary, links, location, visa/work authorization, "
    "citizenship, referral names, degrees, certificates, or exact years of experience.\n"
    "4. Do not invent employment history, credentials, or technical skills not present in the profile.\n"
    "5. Keep it natural, direct and professional. Avoid generic flattery.\n"
    "6. Answer length: 80-400 characters unless field explicitly requires more.\n"
    "7. Return JSON only. No markdown. No commentary.\n\n"
    "Return exactly this schema:\n"
    '{"answer":"your answer here","confidence":0.9,"safe_to_fill":true,"risk_flags":[]}'
)


def gerar_resposta_campo_dinamico(
    field_label: str,
    job_title: str,
    job_url: str,
    perfil_sanitizado: dict,
) -> str:
    """Gera resposta para campo de pergunta aberta usando IA (Gemini Flash via OpenRouter).
    
    Retorna string vazia se a IA falhar ou a resposta não for segura.
    Python decide se usa; IA apenas sugere texto.
    """
    payload = {
        "task": "sagan_field_answer",
        "field_question": field_label[:300],
        "job": {
            "title": job_title,
            "url": job_url,
        },
        "candidate_profile": perfil_sanitizado,
        "constraints": {
            "language": "English",
            "max_chars": 400,
            "submit_application": False,
            "fill_only_this_field": True,
        },
        "blocked_output": [
            "phone", "email", "salary", "linkedin_url",
            "visa", "citizenship", "exact_years_experience",
            "degree_claims", "referral",
        ],
    }
    
    resposta, modelo = chamar_ai(payload, SYSTEM_PROMPT_SAGAN)
    
    if not resposta:
        return ""
    
    answer = str(resposta.get("answer", "")).strip()
    safe = resposta.get("safe_to_fill") is True
    risk_flags = resposta.get("risk_flags", [])
    confidence = float(resposta.get("confidence", 0))
    
    # Validação de segurança (mesma lógica do Wellfound)
    if not safe:
        print(f"  [AI] Resposta bloqueada: safe_to_fill=False")
        return ""
    if risk_flags:
        print(f"  [AI] Resposta bloqueada: risk_flags={risk_flags}")
        return ""
    if confidence < 0.5:
        print(f"  [AI] Confiança baixa ({confidence}), usando DEFAULT")
        return ""
    if not answer or len(answer) < 20:
        return ""
    
    # Remove dados pessoais que possam ter vazado
    answer = re.sub(r"https?://\S+", "", answer)
    answer = re.sub(r"\b[\w.+-]+@[\w-]+\.\w+\b", "", answer)
    answer = re.sub(r"\+?\d[\d\s\-().]{7,}\d", "", answer)
    
    return answer.strip()


# ---------------------------------------------------------------------------
# ENGINE PRINCIPAL DE DETECÇÃO E PREENCHIMENTO SEMÂNTICO
# ---------------------------------------------------------------------------

@dataclass
class SaganFieldEngine:
    """Motor de preenchimento semântico para formulários do Sagan Recruitment.
    
    Detecta campos pelo label/aria-label/placeholder (não por posição/índice),
    responde campos fixos com dados do profile, e chama IA para perguntas abertas.
    """
    page: object          # Playwright Page
    profile: dict         # candidate_profile.json já carregado como dict
    job_title: str = ""
    job_url: str = ""
    
    # Controle interno
    filled_fields: list = field(default_factory=list)
    failed_fields: list = field(default_factory=list)
    _perfil_sanitizado: dict = field(default_factory=dict, init=False)
    
    def __post_init__(self):
        self._perfil_sanitizado = sanitizar_perfil_para_ia(self.profile)
    
    def _get_field_label(self, elem) -> str:
        """Extrai o label visível de um campo de formulário via JavaScript."""
        try:
            return self.page.evaluate("""el => {
                // 1. aria-label
                if (el.getAttribute('aria-label')) return el.getAttribute('aria-label');
                // 2. placeholder
                if (el.placeholder) return el.placeholder;
                // 3. label[for=id]
                if (el.id) {
                    const lbl = document.querySelector('label[for="' + el.id + '"]');
                    if (lbl) return lbl.innerText.trim();
                }
                // 4. label mais próximo no DOM ascendente
                let p = el.parentElement;
                for (let i = 0; i < 5; i++) {
                    if (!p) break;
                    const lbl = p.querySelector('label');
                    if (lbl) return lbl.innerText.trim();
                    // Texto do container que não seja o input
                    const txt = p.innerText || '';
                    if (txt.length > 3 && txt.length < 300) return txt.trim();
                    p = p.parentElement;
                }
                return '';
            }""", elem)
        except Exception:
            return ""
    
    def _highlight(self, elem):
        """Destaque visual laranja antes de preencher."""
        try:
            self.page.evaluate("""el => {
                el.scrollIntoView({behavior:'smooth', block:'center'});
                el.style.outline = '3px solid #ff6600';
                el.style.outlineOffset = '2px';
                el.style.backgroundColor = '#fff3e0';
            }""", elem)
            time.sleep(0.8)
            self.page.evaluate("""el => {
                el.style.outline = '';
                el.style.outlineOffset = '';
                el.style.backgroundColor = '';
            }""", elem)
        except Exception:
            pass
    
    def _fill_input(self, elem, value: str, label: str) -> bool:
        """Preenche um input de texto verificando o valor após o preenchimento."""
        if not value:
            return False
        try:
            self._highlight(elem)
            elem.click(force=True)
            time.sleep(0.3)
            
            tag = elem.evaluate("el => el.tagName")
            if tag == "TEXTAREA":
                elem.evaluate("""(el, val) => {
                    const setter = Object.getOwnPropertyDescriptor(
                        window.HTMLTextAreaElement.prototype, 'value').set;
                    setter.call(el, val);
                    el.dispatchEvent(new Event('input', {bubbles:true}));
                    el.dispatchEvent(new Event('change', {bubbles:true}));
                }""", value)
            else:
                elem.fill(value, force=True)
            
            time.sleep(0.4)
            
            try:
                actual = elem.evaluate("el => el.value") if tag == "TEXTAREA" else elem.input_value()
            except Exception:
                actual = ""
            
            if actual and actual.strip():
                print(f"  ✓ [{label}]: {actual[:50]!r}")
                self.filled_fields.append(label)
                return True
            
            print(f"  ✗ Falhou [{label}]", flush=True)
            self.failed_fields.append(label)
            return False
        except Exception as e:
            print(f"  ✗ Erro [{label}]: {type(e).__name__}")
            self.failed_fields.append(label)
            return False
    
    def _resposta_para_categoria(self, categoria: str, field_label: str) -> str:
        """Retorna o valor do profile para campos fixos, ou chama IA para dinâmicos."""
        p = self.profile
        
        # Campos fixos: resposta direto do candidate_profile.json
        RESPOSTAS_FIXAS = {
            "full_name":      f"{p.get('first_name','')} {p.get('last_name','')}".strip(),
            "email":          p.get("email", ""),
            "country":        "Brazil",
            "phone":          p.get("phone", ""),
            "resume_text":    p.get("cover_letter", "I am a results-driven professional with strong technical skills."),
            "vocaroo":        p.get("vocaroo_url", ""),
            "linkedin":       p.get("linkedin_url", ""),
            "github":         p.get("github_url", p.get("linkedin_url", "")),
            "current_salary": str(p.get("current_salary", "")),
            "target_salary":  str(p.get("salary_expectation", "")),
            "job_title":      p.get("job_title", ""),
            "story":          p.get("story", "I am a dedicated professional with strong analytical and problem-solving skills."),
            "why_company":    p.get("why_company", "I am very interested in this role because it aligns with my background in technology and automation."),
            "experience_tech": p.get("exp_1", "I have extensive experience in technology and automation projects with proven results."),
            "experience_detail": p.get("exp_2", "I bring strong analytical skills and a track record of delivering quality work."),
        }
        
        if categoria in RESPOSTAS_FIXAS:
            val = RESPOSTAS_FIXAS[categoria]
            if val:
                return val
        
        # Campo dinâmico (categoria "unknown" ou sem resposta mapeada):
        # chama IA para gerar texto sob medida
        # Inclui background_full no perfil sanitizado para a IA ter contexto rico
        if categoria in ("unknown", "screening_question", "motivation_question", "skills_question"):
            print(f"  [AI] Campo dinâmico: '{field_label[:70]}' → chamando IA...")
            # Adiciona background_full ao contexto da IA se disponível
            perfil_com_contexto = dict(self._perfil_sanitizado)
            if p.get("background_full") and "background_full" not in perfil_com_contexto:
                # background_full não tem dados pessoais, pode ir para a IA
                perfil_com_contexto["background_full"] = p["background_full"][:2000]
            resposta_ai = gerar_resposta_campo_dinamico(
                field_label,
                self.job_title,
                self.job_url,
                perfil_com_contexto,
            )
            if resposta_ai:
                return resposta_ai
            print(f"  [AI] Sem resposta da IA, usando fallback do perfil")
        
        # Fallback: usa background_full se disponível, senão cover_letter
        bg = p.get("background_full", "")
        return bg[:400] if bg else p.get("cover_letter", "I am a results-driven professional with strong technical and communication skills.")
    
    def fill_all_fields(self) -> dict:
        """Detecta e preenche semanticamente todos os campos visíveis do formulário.
        
        Funciona independente da ordem dos campos na página — busca por label,
        não por posição. Campos como Vocaroo são detectados e preenchidos
        automaticamente quando presentes, sem deslocar os outros seletores.
        
        Retorna dict com {'filled': [...], 'failed': [...], 'skipped': [...]}
        """
        skipped = []
        
        # Coletar todos os inputs e textareas visíveis
        all_inputs = self.page.query_selector_all('input:not([type="hidden"]):not([type="file"]):not([type="submit"]):not([type="checkbox"]):not([type="radio"])')
        all_textareas = self.page.query_selector_all('textarea')
        
        elementos = [(e, "input") for e in all_inputs if e.is_visible()] + \
                    [(e, "textarea") for e in all_textareas if e.is_visible()]
        
        # Mapa de campos já preenchidos por categoria (evitar duplicatas)
        categorias_preenchidas: set[str] = set()
        
        for elem, elem_type in elementos:
            try:
                # Extrair label/aria-label/placeholder
                label_text = self._get_field_label(elem)
                aria = (elem.get_attribute("aria-label") or "").strip()
                placeholder = (elem.get_attribute("placeholder") or "").strip()
                
                # Detectar categoria semanticamente
                categoria = detectar_categoria_campo(label_text, placeholder, aria)
                
                # Nome para log
                display_label = aria or placeholder or label_text[:60] or f"campo_{elem_type}"
                
                # Pular react-select inputs (tratados separadamente)
                elem_id = (elem.get_attribute("id") or "")
                if "react-select" in elem_id:
                    skipped.append(f"{display_label} [react-select, tratado separado]")
                    continue
                
                # Pular se a categoria já foi preenchida (ex: 2 inputs de email)
                if categoria in categorias_preenchidas and categoria != "unknown":
                    skipped.append(f"{display_label} [categoria '{categoria}' já preenchida]")
                    continue
                
                # Obter valor (fixo do profile ou gerado por IA)
                valor = self._resposta_para_categoria(categoria, label_text or display_label)
                
                if not valor:
                    skipped.append(f"{display_label} [sem valor configurado]")
                    continue
                
                # Preencher
                if self._fill_input(elem, valor, f"{categoria}:{display_label[:40]}"):
                    categorias_preenchidas.add(categoria)
                
                time.sleep(0.5)
                
            except Exception as e:
                print(f"  [WARN] Erro ao processar campo: {type(e).__name__}: {str(e)[:80]}")
                continue
        
        return {
            "filled": self.filled_fields,
            "failed": self.failed_fields,
            "skipped": skipped,
        }
