"""Download official inputs and verify the recorded SHA-256 hashes."""
from pathlib import Path
import json,urllib.request,hashlib
root=Path(__file__).resolve().parent
manifest=json.loads((root/'reports/source_manifest.json').read_text())
(root/'data').mkdir(exist_ok=True)
for item in manifest['files']:
    path=root/'data'/item['file']
    if not path.exists():
        print('Downloading',item['file'],flush=True)
        urllib.request.urlretrieve(item['url'],path)
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''): h.update(chunk)
    if h.hexdigest()!=item['sha256']:
        raise ValueError(f"Source changed: {path.name}. Preserve the file and investigate before reproducing published results.")
    print('Verified',path.name)
