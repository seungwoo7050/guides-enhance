#!/bin/sh
set -eu

base_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
install -d -m 0700 "$base_dir/secrets"

for name in db_root_password db_password; do
    target="$base_dir/secrets/$name.txt"
    example="$target.example"
    if [ ! -f "$target" ]; then
        install -m 0600 "$example" "$target"
    fi
done
