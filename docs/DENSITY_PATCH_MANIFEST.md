# D11_H 4.28 RFID-bypass + density patch manifest

**WARNING:** Unofficial firmware. Flashing can brick the printer. Built on top of
`D11_H_4.28_rfid-bypass.bin` (patches A+D). Same brick / no-downgrade risks.

## Symptom addressed

After RFID error-20 bypass alone, normal prints were almost blank / extremely faint
while the built-in test print looked fine. Matches NiimBlue FAQ: without a valid
RFID tag the firmware effectively prints at ~zero heat energy. Test print uses a
different path.

## Root cause (Capstone-verified)

At VA `0x0102120c` the print path reads RFID OK flag `[0x491c8+8]`:

- flag ≠ 1 → `r1 = 500` (0x1f4), then `bl #0x0101fc94` inits that many 0x14-byte heat slots
- flag == 1 → `r1 = 12 * tag[+0x67] * tag[+0x6e]`

Patches A+D force flag=1 with an empty/unread tag buffer. Success-apply at
`0x0101f158` defaults tag bytes `+0x60+0xc/0xd/0xe` to 1 when zero, but **does not**
default `+0x60+7` (`+0x67`). Product becomes `12 * 0 * 1 = 0` → **zero heat slots**
→ near-blank print. No-tag path’s 500 is the intended fallback.

Geometry gates at `0x0101fede` / `0x0102026a` / `0x010225c2` already fall back to
default length `0x12c0` when the tag product is 0; they are not the faint-print cause.

B1 float heat-multiplier patches do **not** apply to D11_H (integer/PWM-style).

## Files

| File | Role | SHA-256 |
|------|------|---------|
| `D11_H_4.28_rfid-bypass.bin` | Parent (A+D only) | `da2e805b4f89b31638b2d2d81562c6ceddfdc11197c71f1469957fa10d8fae19` |
| `D11_H_4.28_rfid-bypass-density.bin` | A+D+E flashable | `8da21d356be33ac7be778d25a7828f5d8a77c4daa912ff279181f0959521f1d4` |

## Container (unchanged identity)

| Field | Value |
|-------|-------|
| Signature | `0x18` |
| Model ID | `528` (D11_H) at file `0x16` |
| Version | `428` (4.28) at file `0x14` — **not raised** |
| Payload length | `147924` (0x241d4) |
| Nonce (bytes 1–3) | `471419` (preserved; zeroed for header CRC) |

## CRCs (recomputed)

| CRC | rfid-bypass (A+D) | rfid-bypass-density (A+D+E) |
|-----|-------------------|------------------------------|
| Payload CRC32 @ `0x08` | `0x82681322` | `0xa39c8657` |
| Header CRC32 @ `0x18` | `0x793a3b8a` | `0xfb3fc536` |

Payload SHA-256: `2d216d88…` → `cc750783ed8c15a47fbf5f82fb1038242cc4decb7da5b5be6536fbc156133257`

Validation: length + both CRCs **PASS**.

## Patch E — force no-tag heat-slot count (density/energy)

| | |
|--|--|
| VA | `0x01021212` |
| App offset | `0x11212` |
| File offset | `0x1122e` |
| Before | `02 d0` — `beq #0x0102121a` (take tagged `12*w*h` path) |
| After | `00 bf` — `nop` (fall through to `r1=500`) |
| Why | Always use the firmware’s own no-tag heat count (500) so `0x0101fc94` initializes slots even when OK flag is forced with empty tag fields. Tagged product path becomes unreachable (dead). |

Capstone after:

```
0x0102120c  ldr   r0, [pc, #0x130]   ; =0x491c8
0x0102120e  ldrb  r0, [r0, #8]
0x01021210  cmp   r0, #1
0x01021212  nop                      ; was beq tagged
0x01021214  movs  r1, #0xff
0x01021216  adds  r1, #0xf5          ; r1 = 0x1f4 = 500
0x01021218  b     #0x01021230
0x01021230  movs  r0, #0
0x01021232  bl    #0x0101fc94
```

## Inherited patches (unchanged)

| Patch | File off | Bytes | Role |
|-------|----------|-------|------|
| A | `0xf217` | `d0`→`e0` | Force RFID poll SUCCESS |
| D | `0xe0fa` | `14`→`00` | Neutralize error 20 (`movs r0,#0x14`→`#0`) |

## Byte-level change list vs original 4.28

| File offset | Before | After | Patch |
|-------------|--------|-------|-------|
| `0xf217` | `d0` | `e0` | A |
| `0xe0fa` | `14` | `00` | D |
| `0x1122e` | `02` | `00` | E |
| `0x1122f` | `d0` | `bf` | E |

Plus header payload/header CRC fields at `0x08` and `0x18`.

Total payload code bytes changed vs original: **4** (A+D+E).

## Confidence

**High** for Patch E fixing the near-blank normal print after A+D:
- Unique site computing heat-slot count from RFID flag vs tag product
- Empty-tag + forced flag → product 0 is exact match for ~zero energy
- 500 is the firmware’s own documented no-tag constant at this site
- Geometry already defaults when product is 0

Residual risk: label length/gap may still be approximate without a real tag;
density UI must still be set high enough (see below).

## How to test after flash

1. Flash `D11_H_4.28_rfid-bypass-density.bin` via NiimBlue (Chrome) like any model-528 image.
2. In Метка / niim.blue set print **density to maximum (5)**.
3. Print a normal label (not only the built-in test).
4. If still light, try density 5 again after power-cycle; if still blank, report diagnostics (firmware still shows 4.28).
