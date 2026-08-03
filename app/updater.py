"""GitHub 'latest' 롤링 릴리스와 비교해 exe 자동 업데이트."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = "qjqmf00331199-coder/B2Bchecker"
ASSET_NAME = "B2B_Inventory.exe"
API_URL = f"https://api.github.com/repos/{REPO}/releases/tags/latest"
TIMEOUT = 3


def _current_exe_path() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    return Path(sys.executable)


def cleanup_old_file() -> None:
    """이전 업데이트가 남긴 백업(.old) 파일 정리."""
    exe = _current_exe_path()
    if exe is None:
        return
    old = exe.with_suffix(exe.suffix + ".old")
    if old.exists():
        try:
            old.unlink()
        except OSError:
            pass


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def check_for_update() -> dict | None:
    """업데이트 있으면 {'download_url', 'size'} 반환, 없거나 실패 시 None."""
    exe = _current_exe_path()
    if exe is None:
        return None
    try:
        with urllib.request.urlopen(API_URL, timeout=TIMEOUT) as resp:
            release = json.loads(resp.read())
    except Exception:
        return None

    asset = next(
        (a for a in release.get("assets", []) if a.get("name") == ASSET_NAME), None
    )
    if asset is None:
        return None

    remote_digest = (asset.get("digest") or "").removeprefix("sha256:")
    if remote_digest:
        if remote_digest == _sha256(exe):
            return None
    # ponytail: digest 없는 오래된 릴리스 대비 크기 비교 폴백, 오탐 가능성 있음
    elif asset.get("size") == exe.stat().st_size:
        return None

    return {"download_url": asset["browser_download_url"], "size": asset.get("size")}


def download_and_apply(download_url: str) -> bool:
    """새 exe 다운로드 후 교체, 재실행. 성공 시 True (호출자는 즉시 종료해야 함)."""
    exe = _current_exe_path()
    if exe is None:
        return False

    tmp_path = exe.with_suffix(exe.suffix + ".new")
    try:
        urllib.request.urlretrieve(download_url, tmp_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        return False

    old_path = exe.with_suffix(exe.suffix + ".old")
    try:
        os.replace(exe, old_path)  # 실행 중이어도 rename은 허용됨
        shutil.move(str(tmp_path), str(exe))
    except OSError:
        return False

    # PyInstaller onefile 부모 프로세스는 _MEIPASS2/_PYI_* 환경변수로 "이미 압축 풀린
    # 곳"을 자식에게 물려준다. 그대로 상속하면 새 exe가 부모의 압축 폴더(구버전 payload)를
    # 써버려 재실행해도 업데이트가 적용 안 된 채 조용히 구버전으로 뜬다. 반드시 제거하고 실행.
    env = {
        k: v
        for k, v in os.environ.items()
        if k != "_MEIPASS2" and not k.startswith("_PYI")
    }
    try:
        subprocess.Popen([str(exe), *sys.argv[1:]], close_fds=True, env=env)
    except OSError:
        pass
    return True
