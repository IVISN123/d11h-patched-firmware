# D11_H 4.28 history-reset patch (on top of A+D+E)

**WARNING:** Unofficial firmware. Flashing can brick the printer. D11_H will not
accept a lower official version. Same risks as previous unofficial images.

## Honest applicability (read this first)

Diagnostics on this printer show **«Метка не прочитана» on every roll**, including
in the official Niimbot app. That means the RFID/NFC **reader is not returning tag
data at all**.

The [pranavms13/niimbot-d110m-patched-firmware](https://github.com/pranavms13/niimbot-d110m-patched-firmware)
project solves a **different** problem: the tag **is readable**, but the used-label
counter (on the sticker and/or in the printer’s remembered-roll history) is exhausted.
Their flow is: clear printer history (this patch) **and** rewrite the sticker counter
to zero with a phone NFC app.

**A used-count / history reset cannot restore printing if the tag is never read.**
It will not fix faint/blank prints after the RFID-bypass+density patches, and it will
not make a dead reader work. This image is provided because you asked for the D110_M-style
reset; expect **no change** to blank-print behavior while RFID stays unread.

Standalone options that also need a **readable** tag for a full refill:

| Method | Needs printer RFID reader? | Needs phone NFC? |
|--------|----------------------------|------------------|
| NiimBlue gear → Tests → Reset (stock) | No (factory settings only; **does not** clear roll history without this patch) | No |
| This patch + NiimBlue Reset | No for history clear | No |
| NFC Tools advanced write of counter pages (D110_M RESET.md) | No (phone talks to sticker) | **Yes** |
| Experimental BLE refill-reset (D110_M only) | **Yes** | No |

D11_H TEA keys / sticker layout are **not** verified here; do not blindly use the
D110_M NFC write batch on an unknown D11_H sticker.

## What this patch changes

Same design as D110_M r1: factory-reset command `0x28` still runs stock defaults, but
before settings save it clears **244 bytes** of remembered-roll history at
`settings+0x28`.

| | D110_M 4.31 | D11_H 4.28 |
|--|-------------|-----------|
| Settings RAM | `0x20928` | `0x20920` |
| History | `+0x28`, length `0xf4` | `+0x28`, length `0xf4` (same relative layout) |
| History RAM range | `0x20928..0x20a1b` | `0x20948..0x20a3b` |
| Settings flash | `0x010ff000` | `0x010ff000` |
| Defaults fn | `0x010225d8` | `0x01024afc` |
| Save fn | `0x01022e20` | `0x010253b4` |
| Memzero | `0x01010182` | `0x01010182` |
| Cmd 0x28 handler | `0x01017374` | `0x01017fe8` |
| Redirected call | app+`0x7388` | app+`0x8000` |

## Files

| File | Role | SHA-256 |
|------|------|---------|
| `D11_H_4.28_rfid-bypass-density.bin` | Parent (A+D+E) | `8da21d356be33ac7be778d25a7828f5d8a77c4daa912ff279181f0959521f1d4` |
| `D11_H_4.28_rfid-bypass-density-history-reset.bin` | A+D+E + history-reset (F) | `765ab690c34bad255e7138dd493c70dff278503e96427c393f83ff898015c4ad` |

## Container identity

| Field | Value |
|-------|-------|
| Signature | `0x18` |
| Model ID | `528` (D11_H) |
| Version | `428` (4.28) — **not raised** |
| Payload length | `147944` (was 147924; +20 wrapper) |
| Nonce (bytes 1–3) | preserved from parent; zeroed for header CRC |

## CRCs (recomputed)

| CRC | Value |
|-----|-------|
| Payload CRC32 @ `0x08` | `0xb9cb7eef` |
| Header CRC32 @ `0x18` | `0x4709739a` |

Patched app SHA-256: `64aea3d64d500c3c751aacb61cbae35dae07215dded099620c90159216573611`

Validation: length + both CRCs **PASS**; model=528, version=428.

## Code patch F — history clear on factory reset

### Redirected call

| | |
|--|--|
| VA | `0x01018000` |
| App offset | `0x8000` |
| File offset | `0x801c` (= app+28) |
| Before | `0df0d8f9` — `bl #0x010253b4` (settings save) |
| After | `1cf0e8f8` — `bl #0x010341d4` (wrapper) |

### Appended wrapper (20 bytes at app end)

| | |
|--|--|
| VA | `0x010341d4` |
| App offset | `0x241d4` |
| File offset | `0x241f0` |
| Bytes | `10b504462830f421dbf7d1ff2046f1f7e7f810bd` |

Capstone-verified:

```
010341d4: push {r4, lr}
010341d6: mov  r4, r0
010341d8: adds r0, #0x28
010341da: movs r1, #0xf4
010341dc: bl   #0x01010182          ; memzero history
010341e0: mov  r0, r4
010341e2: bl   #0x010253b4          ; original settings save
010341e6: pop  {r4, pc}
```

Stays inside the original last 256-byte flash page (44 bytes free; stub uses 20).

### Inherited patches (unchanged)

| Patch | App off | File off | Bytes | Role |
|-------|---------|----------|-------|------|
| A | `0xf1fa` | `0xf216` | `1a d0`→`1a e0` | Force RFID poll SUCCESS |
| D | `0xe0de` | `0xe0fa` | `14 20`→`00 20` | Neutralize error 20 |
| E | `0x11212` | `0x1122e` | `02 d0`→`00 bf` | Force no-tag heat slots 500 |

## How to use (only if a tag actually reads)

1. Flash `D11_H_4.28_rfid-bypass-density-history-reset.bin` via NiimBlue (Chrome); version still shows 4.28.
2. **Remove the roll**, connect, gear → Tests → Reset, wait, power-cycle.
3. Only if phone NFC can read the sticker: reset the counter with a **validated**
   batch (do not assume D110_M keys).
4. Reinsert a matching roll and check roll info shows used count advancing from 0.

If diagnostics still say «Метка не прочитана», this patch cannot help that failure mode.
