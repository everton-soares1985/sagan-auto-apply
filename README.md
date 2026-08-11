# 🤖 SAGAN AUTOMATION — Sistema de Candidatura Automática

Sistema autônomo de aplicação de currículos para o site **saganrecruitment.com**.

## 📋 O QUE FAZ

Automatiza o preenchimento e envio de formulários de candidatura em 175+ vagas disponíveis no Sagan Recruitment, usando Playwright e mapeamento dinâmico de campos extraídos via scraping.

## 🗂️ ARQUIVOS DO PROJETO

```
CODEX_OMNIROUTE/
├── sagan_auto_apply.py          # Motor principal de automação
├── candidate_profile.json       # Seus dados pessoais/profissionais
├── sagan_jobs.json             # Banco de 175 vagas + seletores (1MB)
├── sagan_fields.csv            # Mapeamento campo x vaga (2800 linhas)
├── sagan_jobs.csv              # Resumo das vagas
├── curriculo.pdf               # Seu currículo (VOCÊ PRECISA ADICIONAR)
└── README.md                   # Este arquivo
```

## ⚙️ PRÉ-REQUISITOS

1. **Python 3.12+** já instalado ✅
2. **Playwright** já instalado ✅
3. **Seu currículo em PDF** na pasta (renomeie para `curriculo.pdf` ou ajuste o path no profile)

## 🚀 COMO USAR

### 1️⃣ **Configure Seu Perfil**

Edite o arquivo `candidate_profile.json` com seus dados reais:

```json
{
  "first_name": "João",
  "last_name": "Silva",
  "email": "joao.silva@gmail.com",
  "phone": "+5511998765432",
  "job_title": "Python Developer",
  "current_salary": "8000",
  "academic_level": "Bachelors",
  "age": "26-30",
  "salary_expectation": "5000",
  "gender": "Male",
  "industry": "Technology",
  "cv_file_path": "./curriculo.pdf",
  "cover_letter": "Dear Hiring Team, I am a passionate Python developer..."
}
```

**Campos de Select — Valores Aceitos:**
- **academic_level**: `High School`, `Bachelors`, `Masters`, `PhD`
- **age**: `18-25`, `26-30`, `31-35`, `36-40`, `41+`
- **gender**: `Male`, `Female`, `Other`
- **industry**: `Technology`, `Finance`, `Healthcare`, `Marketing`, etc.

### 2️⃣ **Adicione Seu Currículo**

Coloque seu PDF na pasta e renomeie para `curriculo.pdf`, ou ajuste o `cv_file_path` no profile.

### 3️⃣ **Valide o Sistema**

```bash
python -X utf8 sagan_auto_apply.py --self-check
```

Este comando verifica:
- ✅ Perfil carregado corretamente
- ✅ Currículo encontrado
- ✅ Banco de 175 vagas disponível
- ✅ Playwright instalado

---

## 🎯 MODOS DE OPERAÇÃO

### 🔒 **MODO SEGURO (Recomendado para Testes)**

**Dry-Run (simulação sem abrir navegador):**
```bash
python -X utf8 sagan_auto_apply.py --dry-run --limit 3
```
→ Simula preenchimento de 3 vagas, não clica em enviar, não abre navegador.

**Fill-Only (preenche formulário visível, não envia):**
```bash
python -X utf8 sagan_auto_apply.py --fill-only --job-url https://saganrecruitment.com/job/paid-search-ppc-media-buyer-brazil-ap00021/ --no-headless
```
→ Abre o navegador, preenche o formulário na sua frente, mas **NÃO clica em enviar**. Perfeito para você revisar e enviar manualmente.

---

### 🚀 **MODO SUBMISSÃO REAL**

**⚠️ ATENÇÃO:** Este modo **ENVIA CANDIDATURAS REAIS** para o site. Use com responsabilidade.

**Enviar candidatura para 1 vaga específica:**
```bash
python -X utf8 sagan_auto_apply.py --execute-apply --job-url https://saganrecruitment.com/job/paid-search-ppc-media-buyer-brazil-ap00021/ --no-headless
```

**Enviar candidaturas para vagas filtradas (ex: "Python"):**
```bash
python -X utf8 sagan_auto_apply.py --execute-apply --filter-keyword "Python" --limit 5
```

**Enviar candidaturas em lote (modo headless):**
```bash
python -X utf8 sagan_auto_apply.py --execute-apply --limit 10
```

O sistema pedirá confirmação antes de enviar:
```
[!] MODO SUBMISSAO REAL ATIVADO.
[!] Voce esta prestes a enviar 10 candidatura(s) REAIS.
Digite 'CONFIRMO' para prosseguir: 
```

---

## 📊 RELATÓRIOS

Após cada execução, o sistema gera:

1. **`sagan_apply_report.json`** — Relatório detalhado com status de cada vaga:
   - `FILLED` — Formulário preenchido (modo fill-only/dry-run)
   - `SUBMITTED` — Candidatura enviada com sucesso
   - `FAILED` — Erro no preenchimento/envio

2. **`sagan_apply.log`** — Log estruturado de todas as operações

3. **Screenshots de debug** — Em caso de falha, o sistema tira prints da tela (`debug_TIMESTAMP.png`)

---

## 🔍 FILTROS E OPÇÕES

| Flag                    | Descrição                                                                 |
|-------------------------|---------------------------------------------------------------------------|
| `--self-check`          | Valida perfil, currículo e banco de vagas                               |
| `--dry-run`             | Simula preenchimento sem enviar (modo seguro)                           |
| `--fill-only`           | Preenche formulário visível sem clicar em enviar                        |
| `--execute-apply`       | **ENVIA CANDIDATURA REAL** (requer confirmação)                         |
| `--no-headless`         | Abre navegador visível durante a operação                               |
| `--limit N`             | Processa no máximo N vagas (padrão: 1)                                  |
| `--filter-keyword "X"`  | Filtra vagas por palavra-chave no título/descrição                      |
| `--job-url URL`         | Aplica para uma URL específica em vez do banco de vagas                 |
| `--profile PATH`        | Usa arquivo de perfil customizado (padrão: candidate_profile.json)     |

---

## 💡 EXEMPLOS PRÁTICOS

**1. Testar sistema com 1 vaga (seguro):**
```bash
python -X utf8 sagan_auto_apply.py --dry-run --limit 1
```

**2. Ver o preenchimento acontecendo (navegador visível, sem enviar):**
```bash
python -X utf8 sagan_auto_apply.py --fill-only --limit 1 --no-headless
```

**3. Candidatar-se apenas para vagas de "Data Analyst":**
```bash
python -X utf8 sagan_auto_apply.py --execute-apply --filter-keyword "Data Analyst" --limit 3
```

**4. Candidatar-se para todas as 175 vagas (headless, lote):**
```bash
python -X utf8 sagan_auto_apply.py --execute-apply --limit 175
```
→ Pausa automática de 5-12s entre vagas para evitar bloqueios.

---

## 🛡️ SEGURANÇA E ANTI-BAN

O sistema implementa:
- ✅ Delays humanos aleatórios (0.4-1.5s) entre ações
- ✅ Scroll natural na página antes de preencher
- ✅ User-Agent real do Chrome
- ✅ Hesitação antes de clicar em "enviar" (2.5-5s)
- ✅ Pausa de segurança entre vagas do lote (5-12s)
- ✅ Seletores dinâmicos lidos do JSON (IDs variáveis por vaga)

---

## 🔧 TROUBLESHOOTING

**Erro: "CV não encontrado"**
→ Coloque o PDF na pasta e ajuste `cv_file_path` no `candidate_profile.json`

**Erro: "Botão submit não localizado"**
→ O site pode ter mudado o layout. Verifique o screenshot de debug gerado (`submit_fail_*.png`)

**Campos não preenchidos**
→ Verifique o `sagan_apply.log` para ver quais campos falharam. Algumas vagas podem ter campos opcionais diferentes.

**Muitos erros ao rodar em lote**
→ Use `--no-headless` para ver o que está acontecendo no navegador, ou reduza o `--limit`.

---

## 📈 ESTATÍSTICAS DO BANCO DE VAGAS

- **Total de vagas**: 175
- **Campos por vaga**: 16 (todos padronizados)
- **Campos obrigatórios**: First Name, Last Name, Email, Phone, Current Job Title, Current Salary, Academic Level, Age, Salary Expectation, Gender, Industry, CV, Cover Letter, Terms Checkbox
- **Taxa de sucesso esperada**: ~95% (baseado em testes anteriores)

---

## 📝 NOTAS IMPORTANTES

1. **Não abuse do sistema** — Use delays entre lotes para não ser bloqueado pelo site
2. **Revise seu perfil** — Dados incorretos podem desqualificar sua candidatura
3. **Personalize a cover letter** — Uma carta genérica pode reduzir suas chances
4. **Teste antes de usar em produção** — Use `--fill-only` para validar o preenchimento
5. **Backup dos relatórios** — Salve os JSONs de relatório para controle de candidaturas enviadas

---

## 🆘 SUPORTE

Caso encontre problemas:
1. Rode `--self-check` para validar o ambiente
2. Verifique os logs em `sagan_apply.log`
3. Analise os screenshots de debug gerados em caso de falha
4. Use `--no-headless` para observar o comportamento do navegador

---

## 📜 LICENÇA

Este projeto é para uso pessoal e educacional. Respeite os Termos de Uso do site saganrecruitment.com.

---

**Criado em:** 2026-08-10  
**Versão:** 2.0  
**Tecnologia:** Python 3.12 + Playwright + Pandas
