# D11_H 4.28 RFID-bypass patch manifest

**WARNING:** Unofficial firmware. Flashing can brick the printer (recovery often needs SWD soldering).
D11_H will not accept a lower official version afterward. RFID reader hardware faults are not fixed by this patch.
Label geometry / remaining-count logic may misbehave with an unread tag. Flash only if you accept full brick risk.

## Files

| File | Role | SHA-256 |
|------|------|---------|
| `D11_H_4.28_original.bin` | Exact copy of `t_D11_H_4.28.bin` | `2b0ec265797f5b24bb67babc86daf3dec1d1ea5a1a95c49cef7861c45a6bcf03` |
| `D11_H_4.28_rfid-bypass.bin` | Patched flashable image | `da2e805b4f89b31638b2d2d81562c6ceddfdc11197c71f1469957fa10d8fae19` |
| Source used | `/workspace/d11h/t_D11_H_4.28.bin` | `2b0ec265797f5b24bb67babc86daf3dec1d1ea5a1a95c49cef7861c45a6bcf03` |

## Container identity (unchanged fields)

| Field | Value |
|-------|-------|
| Signature | `0x18` |
| Model ID | `528` (D11_H) |
| Version | `428` (4.28) — **not raised** |
| Payload length | `147924` (0x241d4) — unchanged |
| Nonce (bytes 1–3) | `471419` (preserved; treated as zero for header CRC) |

## Header CRC recomputation

Same rules as [printers.niim.blue/firmware](https://printers.niim.blue/firmware/) and pranavms13/niimbot-d110m-patched-firmware `patch_firmware.py`:

1. `payload_crc = zlib.crc32(payload)` → stored at offset `0x08`
2. Header CRC over bytes `0x00..0x17` with bytes `0x01..0x03` forced to `00 00 00` → stored at `0x18`

| CRC | Original | Patched |
|-----|----------|---------|
| Payload CRC32 | `0xbc6f0e6d` | `0x82681322` |
| Header CRC32 | `0xf9900c56` | `0x793a3b8a` |

Re-validation of patched file: **PASS** (`validate_container` length + both CRCs; model=528, version=428).

Payload SHA-256: `6fd673fcd924ed7a1ff2e3403e35f17c7869c22eac1554c8106d8f251065169b` → `2d216d88edda236c5c10d061913a7a824852c3f66caf73b38f51a81dfb6aead6`

## Code patches (Capstone Thumb-2 verified before/after)

Base VA `0x01010000`. File offset = app offset + 28.

### Patch A — force RFID poll success (primary)

| | |
|--|--|
| VA | `0x0101f1fa` |
| App offset | `0xf1fa` |
| File offset | `0xf216` (changed byte at `0xf217`) |
| Before | `1a d0` — `beq #0x0101f232` |
| After | `1a e0` — `b #0x0101f232` |
| Why | After `RFID_read`, always take SUCCESS: `bl #0x0101f158` sets OK flag at `[0x491c8+8]=1` and clears status bit19 (WriteRfidFail). |

### Patch D — neutralize Print error 20 in status decoder (correctness)

| | |
|--|--|
| VA | `0x0101e0de` |
| App offset | `0xe0de` |
| File offset | `0xe0fa` |
| Before | `14 20` — `movs r0, #0x14` |
| After | `00 20` — `movs r0, #0` |
| Why | If consumption/limit checks later re-OR bit19 with empty tag data, PrintStart’s `get_print_status` no longer maps bit19 → error 20. |

### Not applied (not required once A always takes SUCCESS)

| Candidate | Site | Reason skipped |
|-----------|------|----------------|
| B | `0x0101f220` `strb r5,[r1,#8]` | Fail epilogue unreachable after A |
| C | `0x0101f22c` `orrs r1,r2` (bit19) | Same |
| Consumption bit19 NOPs | `0x01027556` / `0x0102763a` | Covered for PrintStart by D; left intact |

## Byte-level change list

| File offset | Before | After | Patch |
|-------------|--------|-------|-------|
| `0xf217` | `d0` | `e0` | A (branch cond → uncond) |
| `0xe0fa` | `14` | `00` | D (imm8 of movs) |

Total payload bytes changed: **2**.

## Flash notes

- Keep `D11_H_4.28_original.bin`.
- Flash the patched `.bin` via NiimBlue / compatible updater over Web Bluetooth (Chrome), same as any official 0x18 image for model 528.
- If the RFID **reader hardware** is dead, print may still be wrong (length/gap) even though error 20 is bypassed.


## Follow-up: density (Patch E)

See `DENSITY_PATCH_MANIFEST.md` and `D11_H_4.28_rfid-bypass-density.bin` (SHA-256 `8da21d356be33ac7be778d25a7828f5d8a77c4daa912ff279181f0959521f1d4`). Forces no-tag heat-slot count 500 when RFID OK is faked with an empty tag.
