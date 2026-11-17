"""Make the pinned, reproducible art archive without publishing."""
import argparse
import hashlib
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]

def release(output):
    files=[ROOT/"manifest.json",ROOT/"recipes.json",ROOT/"README.md",*sorted((ROOT/"encrypted").glob("*.enc"))]
    with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_STORED) as archive:
        for path in files:
            entry=zipfile.ZipInfo(path.relative_to(ROOT).as_posix(),(2026,11,17,0,0,0))
            entry.create_system=3
            entry.external_attr=0o100644<<16
            archive.writestr(entry,path.read_bytes())
    digest=hashlib.file_digest(Path(output).open("rb"),"sha256").hexdigest()
    Path(str(output)+".sha256").write_text(digest+"  "+Path(output).name+"\n")
    print(digest)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);a=p.parse_args();release(a.output)
