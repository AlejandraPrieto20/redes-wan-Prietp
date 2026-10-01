"""
git_utils.py
Funciones simples para ejecutar comandos Git locales usando subprocess.
"""

import subprocess
from typing import List, Optional, Tuple

class GitError(RuntimeError):
    pass

def _run_git(args: List[str], cwd: Optional[str] = None) -> Tuple[int, str, str]:
    cmd = ["git"] + args
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        raise GitError("Git no está instalado o no está en PATH del sistema.")
    except Exception as e:
        raise GitError(f"Error al ejecutar git: {e}")

def is_git_repo(path: str) -> bool:
    code, out, err = _run_git(["rev-parse", "--is-inside-work-tree"], cwd=path)
    return code == 0 and out.strip() == "true"

def git_init(path: str) -> str:
    if is_git_repo(path):
        return "Repositorio Git ya inicializado en este directorio."
    code, out, err = _run_git(["init"], cwd=path)
    if code != 0:
        raise GitError(f"git init falló: {err or out}")
    return out or "Repositorio inicializado."

def git_status(path: str) -> str:
    code, out, err = _run_git(["status", "--porcelain", "-b"], cwd=path)
    if code != 0:
        raise GitError(f"git status falló: {err or out}")
    return out

def git_add_and_commit(path: str, message: str, files: Optional[List[str]] = None) -> str:
    add_args = ["add", "."] if not files else ["add"] + files
    code, out_add, err_add = _run_git(add_args, cwd=path)
    if code != 0:
        raise GitError(f"git add falló: {err_add or out_add}")

    code, out_commit, err_commit = _run_git(["commit", "-m", message], cwd=path)
    if code != 0:
        combined = err_commit or out_commit
        if "nothing to commit" in combined.lower():
            return "Nada que commitear."
        raise GitError(f"git commit falló: {combined}")
    return out_commit or "Commit realizado."

def git_log(path: str, max_entries: int = 20) -> str:
    code, out, err = _run_git(["log", f"--oneline", f"-n{max_entries}"], cwd=path)
    if code != 0:
        raise GitError(f"git log falló: {err or out}")
    return out

def git_create_branch(path: str, branch_name: str) -> str:
    code, out, err = _run_git(["branch", branch_name], cwd=path)
    if code != 0:
        raise GitError(f"Creación de rama falló: {err or out}")
    return f"Rama '{branch_name}' creada."

def git_checkout(path: str, branch_name: str) -> str:
    code, out, err = _run_git(["checkout", branch_name], cwd=path)
    if code != 0:
        code2, out2, err2 = _run_git(["checkout", "-b", branch_name], cwd=path)
        if code2 != 0:
            raise GitError(f"git checkout falló: {err2 or out2}")
        return out2 or f"Cambiado y creado rama {branch_name}"
    return out or f"Cambiado a rama {branch_name}"

def git_create_tag(path: str, tag_name: str, message: Optional[str] = None) -> str:
    args = ["tag"]
    if message:
        args += ["-a", tag_name, "-m", message]
    else:
        args += [tag_name]
    code, out, err = _run_git(args, cwd=path)
    if code != 0:
        raise GitError(f"git tag falló: {err or out}")
    return f"Tag '{tag_name}' creado."

def git_show_file_at_commit(path: str, commit: str, file_path: str) -> str:
    code, out, err = _run_git(["show", f"{commit}:{file_path}"], cwd=path)
    if code != 0:
        raise GitError(f"git show falló: {err or out}")
    return out
