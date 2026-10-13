"""Publish versioned installers through GitHub Releases, with verified assets.

Credentials stay in memory: GH_TOKEN/GITHUB_TOKEN or the existing Git helper.
Create a draft first and publish only after every asset's size and hash match.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

import requests


ROOT = Path(__file__).resolve().parents[1]


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def credentials() -> str:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    result = subprocess.run(
        ["git", "credential", "fill"], cwd=ROOT,
        input="protocol=https\nhost=github.com\n\n", capture_output=True, text=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "Never"},
    )
    values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    if result.returncode != 0 or not values.get("password"):
        raise RuntimeError("没有可用的 GitHub 凭据；请先配置 Git 登录或 GH_TOKEN。")
    return values["password"]


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="Read existing releases only")
    parser.add_argument("--tag")
    parser.add_argument("--notes", type=Path)
    parser.add_argument("--assets", nargs="+", type=Path)
    parser.add_argument("--prerelease", action="store_true")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    remote = git("remote", "get-url", "origin")
    match = re.fullmatch(r"https://github[.]com/([\w.-]+/[\w.-]+?)(?:[.]git)?", remote)
    if not match:
        raise RuntimeError("origin 必须是 GitHub HTTPS 仓库地址。")
    repo = match.group(1)
    api = f"https://api.github.com/repos/{repo}"
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {credentials()}",
        "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
    })

    def request(method: str, url: str, **kwargs):
        response = session.request(method, url, timeout=(15, 600), **kwargs)
        if not response.ok:
            raise RuntimeError(f"GitHub API 返回 HTTP {response.status_code}；未发布完整 Release。")
        return response.json()

    releases = request("GET", f"{api}/releases", params={"per_page": 100})
    if args.list:
        print(json.dumps([{"tag": r["tag_name"], "url": r["html_url"],
                           "draft": r["draft"], "prerelease": r["prerelease"],
                           "assets": [a["name"] for a in r["assets"]]} for r in releases], ensure_ascii=False))
        return
    if not args.tag or not args.notes or not args.assets:
        parser.error("发布时必须提供 --tag、--notes 和 --assets。")
    if git("status", "--porcelain"):
        raise RuntimeError("发布前必须提交并同步源码，工作树应保持干净。")
    sha = git("rev-parse", "HEAD")
    if git("rev-parse", f"{args.tag}^{{commit}}") != sha:
        raise RuntimeError("发布标签必须指向当前提交。")
    ref = request("GET", f"{api}/git/ref/tags/{args.tag}")["object"]
    if ref["type"] == "tag":
        ref = request("GET", f"{api}/git/tags/{ref['sha']}")["object"]
    if ref["sha"] != sha:
        raise RuntimeError("远程标签与本地提交不一致。")
    local_assets = []
    for path in args.assets:
        if not path.is_file():
            raise FileNotFoundError(path)
        local_assets.append({"path": path, "name": path.name,
                             "size": path.stat().st_size, "sha256": checksum(path)})
    if len({asset["name"] for asset in local_assets}) != len(local_assets):
        raise RuntimeError("附件名称不能重复。")
    release = next((r for r in releases if r["tag_name"] == args.tag), None)
    if release and not release["draft"]:
        raise RuntimeError("该版本已发布；请创建新版本，不覆盖已发布安装包。")
    payload = {"tag_name": args.tag, "target_commitish": sha,
               "name": f"Quant Lab CN/HK {args.tag}",
               "body": args.notes.read_text(encoding="utf-8-sig"),
               "draft": True, "prerelease": args.prerelease}
    if release:
        release = request("PATCH", release["url"], json=payload)
    else:
        release = request("POST", f"{api}/releases", json=payload)
    uploaded = []
    for asset in local_assets:
        existing = next((a for a in release["assets"] if a["name"] == asset["name"]), None)
        if existing:
            remote_asset = existing
        else:
            print(json.dumps({"phase": "upload", "asset": asset["name"]}), flush=True)
            with asset["path"].open("rb") as stream:
                remote_asset = request(
                    "POST", release["upload_url"].split("{", 1)[0],
                    params={"name": asset["name"]}, data=stream,
                    headers={"Content-Type": "application/octet-stream"},
                )
        if remote_asset["size"] != asset["size"] or remote_asset.get("digest") != f"sha256:{asset['sha256']}":
            raise RuntimeError("远程附件大小或 SHA-256 不一致；Release 保持草稿。")
        uploaded.append({"name": asset["name"], "size": asset["size"],
                         "sha256": asset["sha256"], "url": remote_asset["browser_download_url"]})
    release = request("PATCH", release["url"], json={"draft": False})
    receipt = {"tag": args.tag, "commit": sha, "url": release["html_url"],
               "prerelease": release["prerelease"], "assets": uploaded,
               "verified_at_utc": datetime.now(timezone.utc).isoformat()}
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
