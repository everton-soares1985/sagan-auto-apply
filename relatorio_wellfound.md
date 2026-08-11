# Relatório de Auditoria — Sistema Wellfound (GrowthTech AIOS)

> **Data:** 11 de Agosto de 2026
> **Autor:** Agente Autônomo GrowthTech (Codex CLI)
> **Método:** Auditoria read-only (inspeção estática). Nenhum script, navegador, clique, envio ou IA foi executado.
> **Escopo:** Sistema Wellfound dentro de `C:\PROGRAMACAO\Agencia_Growth_Tech`
> **Objetivo:** Documentar o funcionamento de IA, o benchmark, os subsistemas de apply e extrair um esqueleto de IA reaproveitável para montar em outra IA.
> **Base examinada:** arquivos `.py`, `.md`, `.json`, `.yaml`, `.bat` e logs `*.json` persistidos em `.agent/scripts/logs/`.

---

## 1. Resumo executivo

O sistema Wellfound é uma automação de candidatura a vagas dividida em dois módulos independentes: **SAVED** (garimpeiro que salva vagas) e **APPLY** (aplicador que preenche formulários e envia candidaturas sob supervisão). O núcleo de inteligência é uma arquitetura **híbrida** onde o **Python Controla** e a **IA apenas escreve texto**: Python lê o DOM via Chrome DevTools Protocol (CDP), sanitiza o contexto da vaga, envia um JSON seguro para um modelo de linguagem (OpenRouter), recebe a resposta em JSON estrito, valida o schema e digita humanizadamente. A IA nunca clica, navega ou submete — essas decisões ficam no lado Python.

Há dois pilares de IA:

1. **Benchmark de modelos** — compara 15 modelos textuais e 14 modelos vision no OpenRouter usando payload sintético sanitizado, sem browser, sem dados pessoais e sem submit. Avalia JSON válido, schema correto, latência, flags de alucinação e menções proibidas de ação.
2. **Career Core / Profile Narrative Router v2** — motor **determinístico** (sem LLM) que seleciona a melhor narrativa factual do candidato para cada vaga, escolhendo entre 4 lanes (AI Workflow, Growth Marketing, FinTech Trading, Technical Operations) com scoring baseado em afinidade funcional + tecnológica + de domínio. Os scripts narrativos do Wellfound consomem as decisões do router.

O sistema está **operacional sob supervisão**: o lote controlado envia candidaturas reais de formulário simples (`SIMPLE_INTEREST_FORM`) com limite diário persistente, checkpoint, lock e auditoria final em `Applied`. A operação autônoma agendada **não está aprovada**.

---

## 2. Mapa de arquivos encontrados

### 2.1 Documentação de status (raiz do projeto)

| Arquivo | Função |
|:---|:---|
| `WELLFOUND_APPLY.md` | Especificação operacional completa do APPLY v1 |
| `WELLFOUND_APPLY_V1_STATUS.md` | Status operacional, comandos, limites e travas |
| `WELLFOUND_SAVED_V1_STATUS.md` | Status final do SAVED v1 |
| `AUDITORIA_WELLFOUND_SAVED_v0.md` | Auditoria read-only anterior do SAVED (20/06/2026) |

### 2.2 Scripts Python (`.agent/scripts/`)

| Arquivo | Linhas | Função |
|:---|---:|:---|
| `spy_wellfound_aplicador.py` | 13.126 | Script principal do APPLY. Lote, IA, human typing, benchmark, operational store, profiles |
| `spy_wellfound_saver.py` | 1.570 | SAVED. Percorre abas Growth/Web3/Automation e salva vagas com limite e confirmação |
| `wellfound_apply_operational_store.py` | 1.047 | Fronteira SQLite: ledger, limite diário, checkpoint e lock do lote controlado |
| `wellfound_narrative_shadow.py` | 414 | Modo NARRATIVE_SHADOW_READONLY. Adaptador puro do Career Core para vaga Wellfound |
| `wellfound_narrative_answer_preview.py` | 892 | NARRATIVE_ANSWER_PREVIEW. Gera respostas factuais para revisão humana (máx. 3 vagas) |
| `wellfound_narrative_form_fill_preview.py` | 516 | NARRATIVE_FORM_FILL_PREVIEW. Seleção de campo e verificação para fill supervisionado |
| `start_wellfound_chrome_motor.bat` | — | Abre Chrome dedicado na porta 9224 com perfil isolado |

### 2.3 Career Core (motor de narrativa factual)

| Arquivo | Função |
|:---|:---|
| `career_core/router_policy.yaml` | Thresholds, ênfases e allowlist factual do modo generalista |
| `career_core/router/profile_narrative_router.py` | Roteador v2: scoring, modo narrativo, gaps e fatos |
| `career_core/router/narrative_models.py` | `NarrativeScore` e `NarrativeDecision` (dataclasses imutáveis) |
| `career_core/router/narrative_policy.py` | Valida política, lanes, perfil e fatos generalistas |
| `career_core/router/config_loader.py` | Carrega YAMLs do Career Core |
| `career_core/router/models.py` | `JobContext` e modelos de domínio |
| `career_core/router/narrative_cli.py` | CLI offline para reprocessar fixtures |
| `career_core/allowed_facts.yaml` | Base de fatos autorizados (73 KB) |
| `career_core/prohibited_claims.yaml` | Claims proibidos (26 KB) |
| `career_core/profile_lanes.yaml` | Definição das 4 lanes e Application Profiles |
| `career_core/cv_catalog.yaml` | Catálogo de CVs narrativos |

### 2.4 Configuração e dados

| Arquivo | Função |
|:---|:---|
| `.agent/config/wellfound_apply_profiles.example.json` | Template versionado das regras de campo por categoria |
| `.agent/config/wellfound_apply_profiles.local.json` | Dados reais locais (fora do Git) |
| `.agent/data/wellfound_apply_operational.sqlite3` | Banco operacional (ledger, limite, lock) |

### 2.5 Workflows (`.agent/workflows/`)

| Workflow | Função |
|:---|:---|
| `wellfound-saved-antigravity.md` | Operação do SAVED via Antigravity |
| `wellfound-saved-batch-manual.md` | Lote manual do SAVED |
| `wellfound-apply-supervised-flow-v1.md` | Fluxo supervisionado do APPLY |
| `wellfound-apply-batch-manual.md` | Lote manual do APPLY |
| `wellfound-profile-narrative-shadow-v1.md` | Workflow do modo shadow narrativo |
| `wellfound-narrative-answer-preview-v1.md` | Workflow do preview de resposta narrativa |
| `wellfound-narrative-form-fill-preview-v1.md` | Workflow do fill preview narrativo |
| `wellfound-garimpar-saved.md` | Workflow antigo do garimpeiro |

### 2.6 Testes (`tests/wellfound/`)

| Teste | Cobre |
|:---|:---|
| `test_apply_one_supervised.py` | Submit unitário supervisionado |
| `test_batch_manual_workflows.py` | Workflows de lote manual |
| `test_narrative_answer_preview.py` | Preview de resposta narrativa |
| `test_narrative_form_fill_preview.py` | Fill preview narrativo |
| `test_narrative_shadow.py` | Modo shadow narrativo |
| `test_operational_controls.py` | Controles operacionais (limite, lock, ledger) |
| `test_operational_store.py` | Store operacional SQLite |

### 2.7 Logs de benchmark e execução (`.agent/scripts/logs/`)

Dezenas de arquivos JSON:
- `wellfound_apply_ai_benchmark_*.json` — benchmark texto (15 modelos)
- `wellfound_apply_ai_vision_benchmark_*.json` — benchmark vision (14 modelos)
- `wellfound_apply_ai_draft_*.json` — rascunhos de IA operacionais
- `wellfound_apply_fill_plan_safe_*.json` — planos de fill seguros
- `wellfound_apply_safe_base_*.json` — relatórios de execução read-only e self-check

---

## 3. Infraestrutura e browser

```text
Chrome Motor dedicado: http://127.0.0.1:9224
Perfil Chrome: C:\chrome_profiles\wellfound_debug_profile
Launcher: .agent/scripts/start_wellfound_chrome_motor.bat
Página inicial: https://wellfound.com/jobs
Lista de salvos: https://wellfound.com/jobs/starred
Sessão: Wellfound previamente autenticada manualmente nesse perfil
```

O Chrome Motor é dedicado ao Wellfound (porta 9224), separado do Chrome do LinkedIn (porta 9222). O perfil é isolado, persistente e ignorado pelo Git. A conexão é feita via Playwright/CDP ao primeiro contexto existente; nunca abre nova instância.

---

## 4. Funcionamento do sistema de IA

### 4.1 Princípio central: arquitetura híbrida Python-controla / IA-escreve

O desenho mais importante do sistema é a separação radical de responsabilidades:

```text
Python/CDP lê DOM e controla navegação
  -> contexto da vaga é sanitizado
  -> IA gera somente o texto personalizado (JSON estrito)
  -> Python valida o formulário, o botão e o schema da resposta
  -> Python digita por teclado com pausas humanizadas
  -> submit exige modo controlado e flag explícita
  -> sucesso é confirmado na interface
  -> AI Interview é compartilhada
  -> modal é fechado
  -> lote continua
  -> Applied é auditado uma vez ao final
```

A IA **não** recebe liberdade para: escolher elementos da página, clicar em botões, navegar, decidir submit, contornar CAPTCHA/challenge/login, ou inventar dados do candidato.

### 4.2 Camada de IA — OpenRouter

```text
Endpoint: https://openrouter.ai/api/v1/chat/completions
Chave: OPENROUTER_API_KEY (lida do .env ou ambiente, nunca hardcoded)
Formato: JSON object estrito (response_format = {"type": "json_object"})
Temperatura: 0.2 (baixa variação para consistência)
Max output tokens: 5000
Timeout por modelo: 90 segundos
Header X-Title: "GrowthTech Wellfound Apply AI Benchmark"
```

A camada usa `urllib.request` puro (sem SDK do OpenRouter), com timeout de socket e timeout total controlados por thread daemon com `join(timeout)`.

### 4.3 Modelos operacionais aprovados

```text
Primário: google/gemini-2.5-flash-lite
Fallback 1: minimax/minimax-m2.7
Fallback 2: qwen/qwen3-235b-a22b-2507
```

Os fallbacks são de **fornecedores diferentes** do primário (regra de diversidade: `extrair_fornecedor_modelo` evita fallback redundante da mesma família). A seleção do primário preferido usa o modelo operacional se ele passou no benchmark; senão usa o melhor técnico por score/latência.

### 4.4 Prompts de sistema (fixos)

Há três prompts fixos bem delimitados:

**Benchmark AI (texto):** define a IA como "AI decision and drafting brain" que não controla browser, não clica, não submete. Pede decisão APPLY/SKIP/REVIEW, confidence, fit_score, cover_note, field_answers com answer_status, sensitive_fields_blocked e hallucination_risk. Retorna schema JSON exato.

**Benchmark Vision:** define a IA como "passive visual safety auditor" que inspeciona screenshot e JSON sanitizado. Retorna visual_readable, form_or_modal_detected, visible_fields, visible_buttons com risk (safe/submit/unknown), submit_or_apply_visible, manual_review_required e no_action_confirmed.

**AI Draft operacional:** adiciona automation_eligibility (eligible/blocked/uncertain), blocked_fields e autonomous_apply_allowed por campo. Mantém as mesmas proibições factuais (sem phone, email, salary, visa, degree, years, referral).

### 4.5 Payload sanitizado

A função `montar_payload_ai_draft` monta o JSON enviado à IA com:

- `task`: identificador do modo
- `job`: título, empresa, descrição visível (cortada), fatos laterais, skills, mercados
- `form_summary`: campos detectados a partir do relatório safe-base
- `fields`: lista de answer_items com field_key, label, category, required, answer_mode
- `candidate_profile`: perfil sanitizado (contato e dados sensíveis removidos)
- `draft_rules`: regras de segurança (somente JSON, nunca preencher/submit)
- `future_autonomy_policy`: política de autonomia futura

O perfil do candidato passa por `sanitizar_perfil_freelance_para_ia` que remove: e-mails, telefones, URLs, anos exatos de experiência, períodos "present", e linhas com "contact:", "whatsapp:", "e-mail".

### 4.6 Validação da resposta da IA

O sistema valida a resposta em múltiplas camadas:

1. **JSON válido** — `extrair_json_resposta_modelo` tenta JSON estrito, depois remove cercas markdown e extrai substring entre `{` e `}`.
2. **Schema válido** — verifica decision, confidence (0-1), fit_score (0-1), field_answers, etc.
3. **Hallucination flags** — `detectar_hallucination_flags` procura alegações de anos de experiência, salário, telefone, degree, certificação, cidadania/visa, referral, histórico de emprego — com contexto Bloqueado (do not, never, blocked, redacted, etc.) que suprime o flag.
4. **Forbidden action mentions** — `detectar_forbidden_action_mentions` procura "click submit", "submit application", "fill automatically now", "bypass captcha", "fake experience", "invent referral" — com checagem de negação anterior.
5. **Sensitive field errors** — campos sensíveis (phone, salary, location, profile_link, resume, source_tracking) não podem ter respostas preenchidas.
6. **Manual review compliance** — verifica respeita às regras de revisão manual.

A pontuação (`calcular_score_ai_draft`) combina essas verificações em um score técnico usado para ordenar candidatos no benchmark.

---

## 5. Sistema de benchmark

### 5.1 Objetivo

Comparar múltiplos modelos do OpenRouter de forma **offline** (sem browser, sem submit, sem dados pessoais) para escolher o primário e os fallbacks operacionais. O benchmark não deve ser repetido sem necessidade operacional.

### 5.2 Benchmark texto (JSON-only)

```text
15 modelos candidatos:
openai/gpt-oss-120b:free, google/gemini-2.5-flash-lite, deepseek/deepseek-v4-flash,
qwen/qwen3.7-plus, qwen/qwen3-235b-a22b-2507, moonshotai/kimi-k2.5,
google/gemini-3.1-flash-lite, xiaomi/mimo-v2.5, minimax/minimax-m3,
tencent/hy3-preview, deepseek/deepseek-v4-pro, poolside/laguna-m.1:free,
xiaomi/mimo-v2.5-pro, minimax/minimax-m2.7, qwen/qwen3.5-flash-02-23
```

Para cada modelo, o benchmark registra:
- `success`, `json_valid`, `schema_valid`
- `decision` (APPLY/SKIP/REVIEW), `decision_valid`
- `confidence` (0.0-1.0), `fit_score` (0.0-1.0), validade de cada um
- `cover_note_present`, `field_answers_count`
- `sensitive_field_errors`, `hallucination_flags`, `forbidden_action_mentions`
- `manual_review_compliance`
- `latency_seconds`, `timed_out`, `error`
- `score` (0-100, composto)

Ordenação por: `-score, latency, :free preference, model name`.

### 5.3 Benchmark vision (screenshot)

```text
14 candidatos vision (modelos VL):
qwen/qwen3-vl-30b-a3b-instruct, qwen/qwen2.5-vl-72b-instruct,
qwen/qwen-2.5-vl-7b-instruct, qwen/qwen3-235b-a22b-2507,
google/gemini-2.5-flash-lite, google/gemini-3.1-flash-lite,
deepseek/deepseek-v4-flash, deepseek/deepseek-v4-pro,
qwen/qwen3.5-flash-02-23, minimax/minimax-m3, minimax/minimax-m2.7,
tencent/hy3-preview, xiaomi/mimo-v2.5, xiaomi/mimo-v2.5-pro
```

Carrega screenshot local como `data:image/...;base64,...` (máx. 5 MB, sufixos png/jpg/jpeg/webp). Envia junto com payload textual sanitizado. Registra: `visual_readable`, `form_or_modal_detected`, `visible_fields_count`, `visible_buttons_count`, `manual_review_required`, `no_action_confirmed`, `forbidden_action_mentions`.

Modelos que não suportam imagem retornam `http_404: No endpoints found that support image input`.

### 5.4 Seleção automática pós-benchmark

Após o benchmark, funções determinísticas escolhem:

- `selecionar_modelo_preferido`: usa o primário operacional se ele passou; senão o melhor técnico.
- `selecionar_fallbacks_preferidos`: até 2 fallbacks, evitando o mesmo fornecedor do primário. Primeiro tenta os preferidos configurados; senão itera os ordenados; senão aceita qualquer um diferente do primário.

Comandos:
```powershell
python -X utf8 .agent\scripts\spy_wellfound_aplicador.py --benchmark-ai --latest-report
python -X utf8 .agent\scripts\spy_wellfound_aplicador.py --benchmark-ai-vision --screenshot CAMINHO.png --latest-report
```

### 5.5 Resultado observado (log de 06/07/2026)

Benchmark texto: o vencedor foi `google/gemini-3.1-flash-lite` (score 100), mas o primário operacional aprovado permanece `google/gemini-2.5-flash-lite` (também score 100, latência 8.4s). Modelos como `tencent/hy3-preview` e `xiaomi/mimo-v2.5-pro` falharam no JSON (`json_decode_error`).

Benchmark vision: `google/gemini-2.5-flash-lite` e `google/gemini-3.1-flash-lite` passaram com score 100 e latência ~3s. Modelos text-only (qwen3-235b, deepseek, minimax-m2.7, tencent, xiaomi-pro) retornaram 404 por não suportar imagem.

---

## 6. Career Core — Profile Narrative Router v2

### 6.1 Objetivo

Responder a uma pergunta única: **qual a melhor forma factual de apresentar o candidato para esta vaga?** Não decide se deve aplicar — apenas seleciona narrativa, lanes, application profile, fatos autorizados, claims bloqueados, ênfases e gaps.

### 6.2 Contrato v2 (sem LLM)

Diferente do v1 (que usava MATCH/REVIEW/REJECT), o v2 retorna apenas:

- **SPECIALIZED**: uma lane tem afinidade clara
- **HYBRID**: duas lanes oferecem contexto material (requer secondary_lane)
- **GENERALIST**: nenhuma lane tem sinal forte — usa lane default e allowlist transversal

Toda entrada válida retorna uma narrativa e um application profile. Senioridade, liderança, stack e experiência ausentes são **gaps**, nunca bloqueios.

### 6.3 Scoring de três componentes

```text
functional_score  -> função exercida e responsabilidades observáveis (prioritário)
technology_score  -> tecnologias, métodos e skills utilizadas
domain_score      -> setor da empresa ou do produto
```

A função prevalece sobre o domínio. Termos isolados como "Web3", "crypto", "FinTech" ou "AI" não criam narrativa especializada sem evidência funcional.

### 6.4 Quatro lanes e quatro application profiles

```text
1. ai_workflow_automation            -> cv_ai_workflow_automation
2. growth_marketing_automation        -> cv_growth_marketing_automation
3. fintech_trading_market_systems     -> cv_fintech_trading_market_systems
4. technical_operations_integrations  -> cv_technical_operations_integrations
```

Não existe quinta lane nem quinto perfil. Os IDs `cv_` são perfis narrativos internos, não arquivos PDF/DOCX.

### 6.5 NarrativeScore (explicável)

Cada lane recebe score decomposto, com:
- `positive_signals`, `negative_signals`
- `matched_skills`, `missing_skills`
- `domain_signals`, `responsibility_signals`

Sinais negativos não impedem a seleção narrativa — são indicação de gap.

### 6.6 NarrativeDecision (saída)

```text
narrative_mode: SPECIALIZED | HYBRID | GENERALIST
primary_lane, secondary_lane (só se HYBRID)
application_profile_id
narrative_confidence: 0.0-1.0 (claridade da seleção, não probabilidade)
context_quality: RICH | PARTIAL | SPARSE
reasons, emphasis_topics, allowed_fact_ids, blocked_claim_ids
seniority_gap, leadership_gap, stack_gaps, experience_gaps
manual_review_recommended
router_version
narrative_scores: detalhe de todas as lanes
```

### 6.7 Segurança factual

Todas as modalidades retornam somente fatos com status autorizado e `human_validation_required: false`. Exclui: fatos pendentes, conflitantes, inferidos sem autorização, proibidos, claims bloqueados, senioridade/métricas/certificações/resultados não comprovados.

### 6.8 Scripts narrativos do Wellfound (adaptadores do Career Core)

```text
wellfound_narrative_shadow.py
  -> NARRATIVE_SHADOW_READONLY: adaptador puro, sem IA, sem decisões
  -> mapeia vaga Wellfound para JobContext e roda ProfileNarrativeRouter
  -> máx. 5 vagas, output JSON local

wellfound_narrative_answer_preview.py
  -> NARRATIVE_ANSWER_PREVIEW: gera respostas factuais para revisão
  -> consome ShadowRouterBundle e ProfileNarrativeRouter
  -> máx. 3 vagas, pergunta default e estilo default
  -> sem form fill, sem submit, sem application decisions

wellfound_narrative_form_fill_preview.py
  -> NARRATIVE_FORM_FILL_PREVIEW: seleção de campo supervisionada
  -> hard char limit 650, safe categories (motivation/skills/recruiter_note)
  -> bloqueia campos não-narrativos via NON_NARRATIVE_LABEL_PATTERN
  -> sem submit, sem operational writes
```

---

## 7. Subsistemas de apply (visão geral)

### 7.1 SAVED v1 (garimpeiro)

```text
Operacional. Sem IA.
Abre https://wellfound.com/jobs
Percorre abas internas: Growth, Web3, Automation
DRY_RUN é padrão (sem cliques)
Save real exige --execute-saves + limites baixos
Limites: 200 saves total / 20 por aba (tetos rígidos)
Confirmacao pós-clique: Save -> Saved/Remove (8s timeout, 500ms polling)
Scroll: 800px, máximo 4 ciclos por aba, 90s teto de observação
Relatório JSON sanitizado
```

O SAVED **não** chama APPLY, não usa IA, não acessa WhatsApp/CRM/pipeline. Worker separado.

### 7.2 APPLY v1 (aplicador)

```text
Operacional sob supervisão.
Abre https://wellfound.com/jobs/starred (lista de salvos)
Scroll limitado (15 ciclos, 800px) para acumular URLs únicas
Pula vagas já em Applied
Extrai contexto rico sanitizado (descrição, skills, fatos laterais)
Identifica SIMPLE_INTEREST_FORM por estrutura do DOM
Usa IA (Gemini 2.5 Flash-Lite + fallbacks) para gerar resposta textual
Digita humanizadamente (ritmo 78-165ms, 2.5% erro corrigido)
Submit exige --apply-saved-batch-controlled --execute-apply
Confirma candidatura na interface
Compartilha AI Interview pós-submit
Fecha modal e continua lote
Audita Applied uma vez ao final
```

### 7.3 Formulários suportados

**SIMPLE_INTEREST_FORM**: modal com um único campo editável (textarea/textbox) e um único botão final permitido dentro do contêiner correto. Pergunta típica: "What interests you about working for this company?". O aviso "Improve your odds" é informativo e não bloqueia.

**COMPLEX_OR_UNSUPPORTED_FORM**: formulários com múltiplos campos, estrutura ambígua ou campo simples não inequívoco. **Bloqueado** — nenhum preenchimento ou submit. Suporte dinâmico é melhoria futura.

### 7.4 Vagas externas e inelegíveis

- **Apply externo**: botão "Apply on website" nunca é clicado. Sistema remove a vaga dos salvos com flag explícita `--remove-external-apply-safe`.
- **Inelegíveis**: restrições definitivas de sponsorship/localização cancelam e removem a vaga quando confirmadas.

### 7.5 Operational Store (SQLite)

Módulo `wellfound_apply_operational_store.py` — fronteira SQLite mínima:

```text
Banco: .agent/data/wellfound_apply_operational.sqlite3
Limite diário: 100 candidaturas confirmadas (WELLFOUND_APPLY_DAILY_LIMIT)
Ledger por URL: SUBMIT_ATTEMPTED -> APPLIED_CONFIRMED / SUBMIT_UNCONFIRMED / etc.
Checkpoint: RUNNING / COMPLETED / INTERRUPTED / FAILED_SAFE
Lock: TTL 15 minutos, impede lotes concorrentes
Reserva atômica pré-submit: SubmitReservation (allowed, reason, remaining_today)
Statuses de bloqueio automático: APPLIED_CONFIRMED, ALREADY_APPLIED, etc.
Sanitização de segredos: _SECRET_PATTERNS remove chaves, bearer, emails, telefones
```

### 7.6 Limites operacionais

```text
Alvo padrão do lote controlado: 30 candidaturas confirmadas
Teto da CLI e workflow: 50 candidaturas confirmadas
Máximo de vagas escaneadas: 50
Limite diário operacional padrão: 100 candidaturas confirmadas
Intervalo entre vagas: 30-85 segundos
Delay antes do Apply click: 7-20 segundos
Delay antes do submit: 12-32 segundos
Timeout de confirmação do submit: 28 segundos
```

### 7.7 Digitação humanizada

```text
WELLFOUND_HUMAN_TYPING_BASE_DELAY_MS: (78, 165)  -> ritmo por caractere
WELLFOUND_HUMAN_TYPING_ERROR_RATE: 0.025           -> 2.5% erro corrigido
Pausa após focar campo: 900-1900ms
Pausa entre parágrafos: 650-1600ms
Pausa em palavras longas: 320-1100ms
Pausa após frase: 850-1900ms
Pausa após vírgula: 280-760ms
Backspace simulado: 120-280ms
Conferência final: 900-1800ms
Mapa de teclas adjacentes QWERTY (para erros realistas)
```

### 7.8 Travas de segurança

```text
SUBMIT_HABILITADO = False: submit genérico bloqueado
Submit real só no SIMPLE_INTEREST_FORM controlado
Preenchimento genérico bloqueado
"Apply on website" bloqueado
CAPTCHA/challenge/login/domínio inesperado/layout desconhecido -> parada segura
Modal/CTA/campo ambíguo não autorizam clique por aproximação
Sem repetição agressiva de cliques
Formulários complexos não preenchidos
Sem bypass de CAPTCHA/proxy/rotação de IP/stealth
Não acessa WhatsApp AIOS, CRM, dashboard ou pipeline
Nunca persiste chaves/tokens/HTML integral/credenciais
```

---

## 8. Esqueleto de IA reaproveitável

> Esta seção extrai o padrão arquitetural puro, pronto para transplantar para outra IA/outro projeto.

### 8.1 Diagrama do esqueleto

```text
[Browser/DOM real]
      |
      v
[1. Adapter DOM -> JobContext sanitizado]
      |  (Python lê, corta, sanitiza; remove campos sensíveis)
      v
[2. Narrative Router determinístico]  <-- sem LLM, scoring por configuração
      |  (seleciona lane, perfil, fatos, ênfases, gaps)
      v
[3. Payload builder]
      |  (monta JSON: job + form_summary + fields + candidate_profile + rules)
      v
[4. LLM Gateway -> OpenRouter]
      |  (urllib, system prompt fixo, JSON response_format, timeout por thread)
      v
[5. Response validator]
      |  (JSON parse -> schema check -> hallucination flags -> forbidden actions)
      v
[6. Human executor]
      |  (digita humanizado, espera, verifica estado pós-ação)
      v
[7. Operational controls -> SQLite]
      |  (ledger, limite diário atômico, checkpoint, lock)
      v
[8. Audit & report JSON sanitizado]
```

### 8.2 Componentes portáveis

**A. LLM Gateway (`executar_openrouter_benchmark_request`)**
- Chamada HTTP pura via `urllib.request`
- System prompt fixo, user content = JSON sanitizado
- `response_format = {"type": "json_object"}` para texto
- Multimodal: image_url como data URL para vision
- Timeout de thread com `thread.join(timeout)` e fila de resultado
- Tratamento de HTTPError (sanitiza detalhe), TimeoutError, URLError, JSONDecodeError

**B. JSON extractor (`extrair_json_resposta_modelo`)**
- Tenta JSON estrito
- Remove cercas ```json
- Extrai substring entre primeiro `{` e último `}`
- Diagnóstico: `empty_response` / `json_decode_error`

**C. Hallucination detector (`detectar_hallucination_flags`)**
- Regex para anos, salário, telefone, degree, cert, cidadania, referral, histórico
- Contexto de negação (do not, never, blocked, redacted, manual, unknown) suprime flags
- Cada flag é registrada uma vez por padrão

**D. Forbidden action detector (`detectar_forbidden_action_mentions`)**
- Regex para "click submit", "submit application", "fill automatically", "bypass captcha"
- Checa negação anterior (do not, don't, never) para suprimir

**E. Profile sanitizer (`sanitizar_perfil_freelance_para_ia`)**
- Remove linhas com contact/whatsapp/email
- Regex de email -> `[email_redacted]`
- Regex de número -> `[phone_or_long_number_redacted]`
- Regex de "X years" -> `multi-year`
- Regex de "YYYY-present" -> `multi-year period`
- Regex de URL -> `[url_redacted]`
- Corte final por limite de caracteres

**F. Fallback selector (`selecionar_fallbacks_preferidos`)**
- Limite de 2 fallbacks
- Evita mesmo fornecedor do primário
- 3 passos: preferidos aprovados -> ordenados por score -> qualquer aprovado

**G. Profile Narrative Router (determinístico, sem LLM)**
- Scoring por keyword affinity (pesos configurados)
- 3 componentes: functional + technology + domain
- 3 modos: SPECIALIZED / HYBRID / GENERALIST
- Saída imutável (frozen dataclass)
- Fontes: YAML de fatos autorizados + claims proibidos + lanes + policy

**H. Operational Store (SQLite)**
- Ledger por URL com reservação atômica pré-submit
- Limite diário persistente
- Checkpoint de lote (RUNNING/COMPLETED/INTERRUPTED/FAILED_SAFE)
- Lock exclusivo com TTL e recuperação de lock expirado
- Sanitização de segredos em logs

### 8.3 Contrato de prompt reutilizável

Para transplantar, o prompt de sistema deve ter a estrutura:

```text
You are the AI [role] brain for a [domain] automation system.

You do not control the browser.
You do not click buttons.
You do not fill fields.
You do not submit applications.
You only analyze a sanitized JSON payload and produce structured JSON drafts.

Your job:
1. Decide [APPLY|SKIP|REVIEW]
2. Generate [cover note / answer]
3. Draft answers only from the provided profile
4. Mark sensitive/uncertain fields as manual_review_required
5. Never invent [experience, credentials, salary, phone, ...]
6. Return JSON only. No markdown. No commentary.

Return this schema exactly:
{"decision":"...","confidence":0.0,"fit_score":0.0,
 "fit_summary":"...","red_flags":[],
 "cover_note":"...","field_answers":[...],
 "sensitive_fields_blocked":[],
 "hallucination_risk":"low","model_self_notes":"..."}
```

### 8.4 Variáveis de ambiente necessárias

```text
OPENROUTER_API_KEY          -> chave do OpenRouter (nunca hardcoded)
WELLFOUND_APPLY_DAILY_LIMIT -> limite diário (default 100)
WELLFOUND_APPLY_PHONE       -> telefone (opcional, só se safe_to_autofill=true)
WELLFOUND_APPLY_PROFILE_URL -> URL do perfil (opcional)
WELLFOUND_APPLY_MIN_SALARY_USD_YEARLY -> salário mínimo (opcional)
```

### 8.5 Checklist para transplantar o esqueleto

1. Definir role do LLM (decision/drafting/audit) e dominio
2. Escrever system prompt fixo com proibições explícitas
3. Definir schema JSON de saída e validá-lo
4. Implementar sanitização de perfil (remover dados sensíveis)
5. Implementar detector de alucinação e ações proibidas
6. Montar payload sanitizado (job + form + profile + rules)
7. Usar LLM Gateway com timeout, fallback diversificado e response_format JSON
8. Implementar executor humano (digitação, pausas, verificação)
9. Adicionar operational controls (ledger, limite, checkpoint, lock)
10. Gerar relatório JSON sanitizado em pasta ignorada pelo Git

---

## 9. Estado atual e defeitos conhecidos

### 9.1 Estado operacional

```text
SAVED v1:                             OPERACIONAL
APPLY formulário simples:              OPERACIONAL SOB SUPERVISÃO
APPLY lote controlado:                 OPERACIONAL SOB SUPERVISÃO
Operational Controls v1:               VALIDADOS
Benchmark texto (15 modelos):         EXECUTADO
Benchmark vision (14 modelos):        EXECUTADO
Career Core / Narrative Router v2:    IMPLEMENTADO
Scripts narrativos (shadow/preview):   IMPLEMENTADOS
Formulários complexos:                 BLOQUEADOS
Operação autônoma agendada:            NÃO APROVADA
```

### 9.2 Defeitos comprovados

1. **Truncamento em 650 caracteres**: uma resposta do fallback MiniMax atingiu exatamente 650 caracteres e terminou no meio de uma palavra ("automated r"). Foi digitada e enviada. Defeito de acabamento no limite de tamanho — não corrigido.
2. **Confirmação pós-Remove falhou 3 vezes**: três vagas externas tiveram clique em "Remove", mas o estado final não foi confirmado (`remove_click_not_confirmed`). Sistema não abriu website externo e não contabilizou como sucesso. Estado real das três vagas é desconhecido.

### 9.3 Validações reais auditadas

**15/07/2026:**
```text
83 vagas vistas, 17 processadas, 10 candidaturas confirmadas
10 AI Interviews compartilhadas, 10 modais fechados
1 inelegível removida, 3 complexos bloqueados
3 remoções externas sem confirmação
0 Apply on website, 0 fail-safe stops
```

**17/07/2026 (Operational Controls v1):**
```text
1 unitária + 3 em lote = 4 confirmadas de 5
Ledger: 4 APPLIED_CONFIRMED + 1 FORM_COMPLEX_BLOCKED
Checkpoint: COMPLETED
Lock: inativo após execução
Duplicidade: bloqueada
```

---

## 10. Conclusão

O sistema Wellfound é uma automação madura de candidatura a vagas com arquitetura híbrida bem desenhada: Python controla toda a navegação e decisão, a IA apenas gera texto em JSON estrito, e um motor determinístico (Career Core) seleciona a narrativa factual. O benchmark sistemático de 15+14 modelos garante escolha informada de primário e fallbacks diversificados. Os controles operacionais (SQLite com ledger, limite diário, checkpoint e lock) tornam o lote controlado seguro e resumível.

O **esqueleto de IA** extraído é diretamente portável: gateway LLM com `urllib`, extrator de JSON, detectores de alucinação/ação proibida, sanitizador de perfil, seletor de fallback e router narrativo determinístico. Para montar em outra IA, basta adaptar o system prompt ao novo domínio, definir o schema JSON de saída e conectar um executor humano (digitação + verificação).

```text
Estado geral: MADURO / OPERACIONAL SOB SUPERVISÃO
Pronto para reaproveitamento do esqueleto de IA: SIM
Recomendação para nova IA: transplantar LLM Gateway + validadores + Career Core
```

---

*Fim do relatório. Documento gerado por auditoria read-only em 11/08/2026.*
