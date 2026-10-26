"""Redaction for user-visible text and stored study content; no secret persistence."""

import re


def redact(text: str, secrets=()) -> str:
    result = str(text)
    for secret in secrets:
        if secret:
            result = result.replace(secret, "[密钥已隐藏]")
    return re.sub(r"\bsk-[A-Za-z0-9_-]{6,}", "[密钥已隐藏]", result)


class StreamRedactor:
    def __init__(self, secrets=()):
        self.secrets = tuple(secrets)
        self.buffer = ""
        self.keep = max(256, *(len(s) for s in self.secrets), 1)

    def feed(self, text: str, final: bool = False) -> str:
        self.buffer = redact(self.buffer + text, self.secrets)
        cut = len(self.buffer) if final else max(0, len(self.buffer) - self.keep)
        output, self.buffer = self.buffer[:cut], self.buffer[cut:]
        return output
