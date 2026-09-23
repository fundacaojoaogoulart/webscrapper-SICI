#!/usr/bin/env python3
"""Etapa B — atualização seletiva da documentação via agente (OpenCode).

Orquestra: triagem → (opcional) análise da IA → verificação de escopo → validação.

Fluxo sempre manual: nada é acionado por hook de Git. Execute::

  python scripts/docs-update.py
  python scripts/docs-update.py --model "provedor/modelo"
  python scripts/docs-update.py --dry-run
  python scripts/docs-update.py --allow-review

Códigos de saída (ver ``aiAction.status`` gravado em ``.docs-impact/impact.json``):

  ======================  =====  ============================================
  status                  código significado
  ======================  =====  ============================================
  not-needed              0      sem impacto; IA não acionada
  human-review-required   2      triagem exige revisão humana
  dry-run                 0      somente preparação; IA não acionada
  not-run (opencode-miss) 3      impacto, mas CLI opencode ausente
  failed                  4      execução da IA falhou
  out-of-scope            5      IA alterou arquivos fora do escopo
  validation-failed       6      validação documental reprovada
  completed               0      atualização concluída e validada
  ======================  =====  ============================================
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
IMPACT_DIR = ROOT / ".docs-impact"
IMPACT_FILE = IMPACT_DIR / "impact.json"

ALLOWED_EXTRA = {"scripts/docs-dependencies.json"}

PROMPT = (
    "Leia o arquivo `.docs-impact/context.md` e siga exatamente as instruções "
    "nele contidas. Atualize apenas os documentos afetados e, se necessário, "
    "`scripts/docs-dependencies.json`. Se a documentação já estiver correta, "
    "não altere nada. Não modifique nenhum outro arquivo."
)


def run(cmd, **kw):
    return subprocess.run(cmd, cwd=str(ROOT), text=True, encoding="utf-8",
                          errors="replace", stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)


def run_triage():
    return run([sys.executable, str(SCRIPT_DIR / "docs-impact.py")])


def read_impact():
    if not IMPACT_FILE.exists():
        raise SystemExit("impact.json ausente — execute a triagem primeiro.")
    return json.loads(IMPACT_FILE.read_text(encoding="utf-8"))


def write_ai_action(ai_action):
    impact = read_impact()
    impact["aiAction"] = ai_action
    IMPACT_DIR.mkdir(parents=True, exist_ok=True)
    IMPACT_FILE.write_text(json.dumps(impact, ensure_ascii=False, indent=2), encoding="utf-8")


def snapshot():
    paths = []
    docs = ROOT / "docs"
    if docs.exists():
        for p in docs.rglob("*"):
            if p.is_file():
                paths.append(p.relative_to(ROOT))
    for rel in ("scripts/docs-dependencies.json", "mkdocs.yml"):
        p = ROOT / rel
        if p.exists():
            paths.append(Path(rel))
    out = {}
    for rel in paths:
        try:
            out[rel.as_posix()] = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        except OSError:
            pass
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Atualização seletiva da documentação via agente.")
    parser.add_argument("--model", help="modelo no formato provider/model (opcional)")
    parser.add_argument("--allow-review", action="store_true",
                        help="permite a IA documentar fatos comprovados mesmo com revisão humana pendente")
    parser.add_argument("--dry-run", action="store_true",
                        help="prepara e inspeciona o contexto sem chamar o modelo")
    args = parser.parse_args(argv)

    triage_res = run_triage()
    impact = read_impact()

    if not impact.get("needsAgent"):
        write_ai_action({"status": "not-needed", "reason": None})
        print("Sem impacto na documentação. Nada a fazer.")
        return 0

    if impact.get("requiresHumanReview") and not args.allow_review:
        write_ai_action({"status": "human-review-required",
                         "reason": "triagem marcou revisão humana (binário/schema/módulo desconhecido)"})
        print("A triagem exige revisão humana antes de registrar um novo comportamento como confirmado.")
        print("Revise `.docs-impact/context.md` e, se for seguro, execute com `--allow-review`.")
        return 2

    if args.dry_run:
        write_ai_action({"status": "dry-run", "reason": None})
        print("dry-run: contexto preparado em `.docs-impact/context.md`; IA não acionada.")
        return 0

    opencode = shutil.which("opencode")
    if not opencode:
        reason = "opencode-missing"
        write_ai_action({"status": "not-run", "reason": reason})
        docs = ", ".join(impact.get("candidateDocs", []) or ["(nenhum)"])
        print("IA não acionada para ajustes na documentação por falta de 'opencode' no PATH")
        print(f"Documentos afetados: {docs}")
        print("O pacote de contexto permanece em `.docs-impact/context.md`.")
        return 3

    before = snapshot()
    cmd = [opencode, "run", "--auto"]
    if args.model:
        cmd += ["--model", args.model]
    cmd += [PROMPT]

    print("Acionando o agente de documentação...")
    res = run(cmd)
    if res.returncode != 0:
        write_ai_action({"status": "failed", "reason": f"exit {res.returncode}"})
        print(res.stdout)
        print(res.stderr, file=sys.stderr)
        print("A execução da IA falhou.")
        return 4

    after = snapshot()
    changed = {p for p in after if p not in before or before[p] != after[p]}
    allowed = set(impact.get("candidateDocs", [])) | ALLOWED_EXTRA
    out_of_scope = sorted(changed - allowed)

    if out_of_scope:
        write_ai_action({"status": "out-of-scope", "reason": None,
                         "outOfScope": out_of_scope})
        print("A IA alterou arquivos fora do escopo (preservados, não revertidos):")
        for p in out_of_scope:
            print(f"  - {p}")
        print("Revise manualmente antes de prosseguir.")
        return 5

    val = run([sys.executable, str(SCRIPT_DIR / "docs-validate.py")])
    print(val.stdout)
    if val.returncode != 0:
        write_ai_action({"status": "validation-failed", "reason": None})
        print(val.stderr, file=sys.stderr)
        print("Validação documental reprovada.")
        return 6

    write_ai_action({"status": "completed", "reason": None,
                     "model": args.model, "changedFiles": sorted(changed)})
    print("Documentação atualizada e validada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
