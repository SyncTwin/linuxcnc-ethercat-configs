#!/bin/bash
# Read CiA402 scaling objects from a drive: encoder resolution, gear, feed.
P=${1:-3}
for spec in "0x608F 1 uint32 encoder-increments" \
            "0x608F 2 uint32 motor-revolutions" \
            "0x6092 1 uint32 feed-constant" \
            "0x6092 2 uint32 shaft-revolutions" \
            "0x6091 1 uint32 gear-numerator" \
            "0x6091 2 uint32 gear-denominator" \
            "0x6064 0 int32 position-actual" \
            "0x6063 0 int32 position-internal" \
            "0x6061 0 int8 mode-display"; do
  set -- $spec
  printf '%-22s %s\n' "$4" "$(ethercat upload -p"$P" --type "$3" "$1" "$2" 2>&1)"
done
