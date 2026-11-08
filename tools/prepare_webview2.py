"""Acquire and verify the pinned Microsoft Fixed Version x64 package."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def prepare(download=False):
    manifest = json.loads((ROOT / "installer/webview2-runtime.json").read_text(encoding="utf-8"))
    base = ROOT / ".tools/webview2"
    cab = base / f"runtime-{manifest['version']}-x64.cab"
    runtime = base / ("extracted-" + manifest["version"]) / manifest["directory"]
    if not cab.exists() and download:
        base.mkdir(parents=True, exist_ok=True)
        temporary = cab.with_suffix(".download")
        urllib.request.urlretrieve(manifest["url"], temporary)
        if sha(temporary) != manifest["cab_sha256"]:
            raise ValueError("WebView2下载SHA-256不匹配。")
        temporary.replace(cab)
    if not cab.is_file() or sha(cab) != manifest["cab_sha256"]:
        raise ValueError("缺少经过校验的WebView2 CAB；运行python tools/prepare_webview2.py --download。")
    if not runtime.exists():
        runtime.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["expand.exe", str(cab), "-F:*", str(runtime.parent)], stdout=subprocess.DEVNULL, check=True)
    executable = runtime / "msedgewebview2.exe"
    if not executable.is_file() or sha(executable) != manifest["exe_sha256"]:
        raise ValueError("WebView2可执行文件校验失败。")
    # Compare every extracted file with the pinned official CAB's content hashes.
    files = [path for path in runtime.rglob("*") if path.is_file()]
    if len(files) != manifest["file_count"] or sum(path.stat().st_size for path in files) != manifest["unpacked_bytes"]:
        raise ValueError("WebView2运行时文件不完整。")
    if {path.relative_to(runtime).as_posix(): sha(path) for path in files} != manifest["files"]:
        raise ValueError("WebView2运行时文件SHA-256不匹配。")
    command = "Import-Module ($PSHOME+'\\Modules\\Microsoft.PowerShell.Security\\Microsoft.PowerShell.Security.psd1') -ErrorAction Stop; $s=Get-AuthenticodeSignature -LiteralPath '" + str(executable).replace("'", "''") + "'; if($s.Status -ne 'Valid' -or $s.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation'){exit 2}"
    environment = dict(os.environ)
    environment.pop("PSModulePath", None)  # A PowerShell 7 host path breaks Windows PowerShell module discovery.
    subprocess.run(["powershell.exe", "-NoProfile", "-Command", command], env=environment, check=True, capture_output=True)
    return runtime, manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    runtime, manifest = prepare(parser.parse_args().download)
    print(json.dumps({"runtime": str(runtime), "version": manifest["version"], "signature": "Microsoft Corporation / Valid"}))
