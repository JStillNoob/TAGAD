import hashlib
import json
from pathlib import Path


class ArtifactVerificationError(ValueError):
    pass


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as artifact:
        for chunk in iter(lambda: artifact.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def verify_artifacts(model_dir, manifest_path):
    model_dir = Path(model_dir)
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    failures = []
    for expected in manifest['artifacts']:
        path = model_dir / expected['file']
        if not path.is_file():
            failures.append(f'{expected["file"]}: missing')
            continue
        if path.stat().st_size != expected['bytes']:
            failures.append(f'{expected["file"]}: size mismatch')
            continue
        if sha256(path).lower() != expected['sha256'].lower():
            failures.append(f'{expected["file"]}: checksum mismatch')
    if failures:
        raise ArtifactVerificationError('; '.join(failures))
    return manifest
