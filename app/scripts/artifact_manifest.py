"""Generate or verify the release's data/model hashes, without loading models."""
from pathlib import Path
import argparse, hashlib, json

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--write',action='store_true')
    args=parser.parse_args()
    path=ROOT/'artifact_manifest.json'
    if args.write:
        files={}
        for folder in ('data','models'):
            for file in sorted((ROOT/folder).rglob('*')):
                if file.is_file() and '__pycache__' not in file.parts:
                    files[file.relative_to(ROOT).as_posix()]=hashlib.sha256(file.read_bytes()).hexdigest()
        path.write_text(json.dumps({'app_version':'0.9.0','source_base_commit':'6460d7f5f572bfb678b066737dfc2f8006f180e0','files':files},indent=2),encoding='utf-8')
    manifest=json.loads(path.read_text(encoding='utf-8'))
    problems=[]
    for rel,digest in manifest['files'].items():
        file=(ROOT/rel).resolve()
        if not file.is_relative_to(ROOT.resolve()):raise ValueError('Invalid manifest path')
        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=digest:
            problems.append(rel)
    if problems:raise SystemExit('Missing or altered release artifacts: '+', '.join(problems))
    print(f"Verified {len(manifest['files'])} release artifacts.")


if __name__=='__main__':main()
