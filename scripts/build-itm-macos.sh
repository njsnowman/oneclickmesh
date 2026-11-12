#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
itm_source="${1:?Usage: build-itm-macos.sh PATH_TO_NTIA_ITM_SOURCE}"
temp_dir="$(mktemp -d)"
trap 'rm -rf "$temp_dir"' EXIT

cp -R "$itm_source/include" "$temp_dir/include"
cp -R "$itm_source/src" "$temp_dir/src"

python3 - "$temp_dir" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
for path in [*root.joinpath('src').glob('*.cpp'), *root.joinpath('include').glob('*.h')]:
    source = path.read_text(encoding='utf-8')
    source = source.replace('\\', '/')
    source = source.replace(
        '#define DLLEXPORT extern "C" __declspec(dllexport)',
        '#define DLLEXPORT extern "C" __attribute__((visibility("default")))',
    )
    path.write_text(source, encoding='utf-8')
PY

clang++ -std=c++11 -O3 -fPIC -dynamiclib \
  -I"$temp_dir/include" "$temp_dir"/src/*.cpp \
  -o "$repo_root/app/libitm.dylib"

echo "Built $repo_root/app/libitm.dylib from NTIA ITM v1.4 source."
