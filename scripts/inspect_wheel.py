"""Fail-closed release-candidate archive inspection."""

from __future__ import annotations

import email
import re
import sys
import zipfile
from pathlib import Path


def main(path: str) -> None:
    wheel = Path(path)
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        forbidden = [name for name in names if any(part in name.lower() for part in (".env", "wallet", "mnemonic", "receipt-token"))]
        if forbidden:
            raise SystemExit(f"forbidden archive member: {forbidden[0]}")
        metadata_name = next(name for name in names if name.endswith(".dist-info/METADATA"))
        entry_name = next(name for name in names if name.endswith(".dist-info/entry_points.txt"))
        metadata = email.message_from_bytes(archive.read(metadata_name))
        if metadata["Name"] != "hermes-plugin-onchain-router" or metadata["Version"] != "0.2.0":
            raise SystemExit("wheel identity drifted")
        if metadata["License-Expression"] != "MIT":
            raise SystemExit("wheel license drifted")
        encoded_description = metadata.get_payload(decode=True)
        if not isinstance(encoded_description, bytes):
            raise SystemExit("wheel long description encoding is invalid")
        description = encoded_description.decode(metadata.get_content_charset() or "utf-8")
        source_readme = Path("README.md").read_text(encoding="utf-8")
        if description.strip() != source_readme.strip():
            raise SystemExit("wheel long description differs from README")
        entry_points = archive.read(entry_name).decode("utf-8")
        if "onchain-router = onchain_router_hermes" not in entry_points:
            raise SystemExit("Hermes entry point is missing")
        combined = b"\n".join(archive.read(name) for name in names if name.endswith((".py", ".md", ".yaml", ".txt")))
        if re.search(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", combined):
            raise SystemExit("private key material found in wheel")
        if b"@blockrun" in combined.lower() or b"clawrouter" in combined.lower():
            raise SystemExit("competitor branding found in wheel")
    print("hermes_wheel_inspection_ok")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: inspect_wheel.py <wheel>")
    main(sys.argv[1])
