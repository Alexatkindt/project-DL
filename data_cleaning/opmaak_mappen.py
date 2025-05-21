# ─── Cell 1: imports & windows‐longpath helper ─────────────────────────────
import os, sys, shutil
from pathlib import Path

def win_longpath(p: Path) -> str:
    """Prefix with \\?\\ on Windows to bypass MAX_PATH limits."""
    s = str(p.resolve())
    if os.name == 'nt' and not s.startswith('\\\\?\\'):
        s = '\\\\?\\' + s
    return s


# ─── Cell 2: locate your top‐level schilderijen/ directory ─────────────────────────
def find_schilderijen_dir() -> Path:
    """
    Zoek naar een submap 'schilderijen/' in deze folder of hogerop.
    """
    here = Path().resolve()
    for ancestor in (here, *here.parents):
        candidate = ancestor / 'schilderijen'
        if candidate.is_dir():
            return candidate
    print("❌ Couldn't find a 'schilderijen/' folder in this path or its parents.", file=sys.stderr)
    sys.exit(1)


data_dir      = find_schilderijen_dir()
clean_base    = data_dir / '2_cleaned' / 'cleaned_dataset'
processed_root = data_dir / '3_processed'

# sanity checks
if not clean_base.is_dir():
    raise FileNotFoundError(f"Cleaned folder not found at: {clean_base}")
processed_root.mkdir(parents=True, exist_ok=True)

print(f"✔ Using schilderijen/    : {data_dir}")
print(f"✔ Cleaned data   : {clean_base}")
print(f"✔ Processed root : {processed_root}")

# ─── Cell 3: map numeric labels to painter names ─────────────────────────
label_map = {
    '1': 'Mondriaan',
    '2': 'Picasso',
    '3': 'Rembrandt',
    '4': 'Rubens'
}

# ─── Cell 4: function to build one dataset ───────────────────────────────
def prepare_dataset(num_painters: int):
    """
    Copy all images whose filenames start with labels '1_'..'{num_painters}_'
    from clean_base into subfolders under processed_root/dataset_{N}Painters.
    """
    dst_root = processed_root / f'dataset_{num_painters}Painters'
    dst_root.mkdir(parents=True, exist_ok=True)
    
    # pick the first N painters from the mapping
    selected = list(label_map.items())[:num_painters]
    for label, painter in selected:
        out_dir = dst_root / painter
        out_dir.mkdir(exist_ok=True)
        
        for src_path in clean_base.rglob("*"):
            if not src_path.is_file():
                continue
            if src_path.name.startswith(f"{label}_"):
                dst_path = out_dir / src_path.name
                shutil.copy2(win_longpath(src_path), win_longpath(dst_path))
    
    painters = ", ".join(p for _, p in selected)
    print(f"→ Created dataset_{num_painters}Painters with: {painters}")

# ─── Cell 5: build all three splits ───────────────────────────────────────
for n in (2, 3, 4):
    prepare_dataset(n)
