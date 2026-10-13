"""Run a build command while preserving its output and actual exit code."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("Provide the command after --")
    args.log.parent.mkdir(parents=True, exist_ok=True)
    with args.log.open("ab") as log:
        log.write(f"\n[{datetime.now(timezone.utc).isoformat()}] {subprocess.list2cmdline(command)}\n".encode("utf-8"))
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as process:
            for line in iter(process.stdout.readline, b""):
                log.write(line)
                log.flush()
                sys.stdout.buffer.write(line)
                sys.stdout.buffer.flush()
            code = process.wait()
        log.write(f"\nexit_code={code}\n".encode("ascii"))
    return code


if __name__ == "__main__":
    sys.exit(main())
