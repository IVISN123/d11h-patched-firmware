# D11_H 4.28 used>all ignore patch (on top of A+D+E+F)

**WARNING:** Unofficial firmware. Flashing can brick the printer. D11_H will not
accept a lower official version. Same risks as previous unofficial images.

## Why this exists

Live diagnostics (serial HA18013182) show the RFID reader **works**:
`tagPresent=true`, `paperRfidSuccess=true`, uuid `881d9baa45121080`,
`allPaper=186`, `usedPaper=201`, `paperInfo.valid=false`.

History-reset (patch F) clears the printer's 244-byte roll cache only. It does
**not** rewrite the encrypted used-counter on the NFC sticker, so `usedPaper`
stays at 201 and the firmware still marks the roll invalid (`used > all`).

## What this patch changes

Smallest reliable fix: **stop treating used>all as invalid / WriteRfidFail**.
Does not rewrite the sticker; the on-tag counter may keep growing. Printing
should proceed with this exhausted roll.

| Site | VA | Change |
|------|-----|--------|
| G1 | `0x0101467a` | `bhi` → `nop` so `paperInfo.valid` stays success |
| G2 | `0x0101809c` | `bls` → `b` skip secondary fail flag |
| G3 | `0x0102754e` | `bls` → `b` skip bit19 OR (consumption path 1) |
| G4 | `0x01027632` | `bls` → `b` skip bit19 OR (consumption path 2) |

## Files

| File | Role | SHA-256 |
|------|------|---------|
| `D11_H_4.28_rfid-bypass-density-history-reset.bin` | Parent (A+D+E+F) | `765ab690c34bad255e7138dd493c70dff278503e96427c393f83ff898015c4ad` |
| `D11_H_4.28_rfid-bypass-density-history-reset-used-ignore.bin` | A+D+E+F + used-ignore (G) | `11850eebd07d5e17730019faaebc11c7cd8e7731652ba78535d4aeb4a732dc61` |

## Container identity

| Field | Value |
|-------|-------|
| Signature | `0x18` |
| Model ID | `528` (D11_H) |
| Version | `428` (4.28) — **not raised** |
| Payload length | `147944` |
| Nonce (bytes 1–3) | preserved from parent; zeroed for header CRC |

## CRCs (recomputed)

| CRC | Value |
|-----|-------|
| Payload CRC32 @ `0x08` | `0xc1939bd7` |
| Header CRC32 @ `0x18` | `0x5333bba3` |

Patched app SHA-256: `7c585cd32a571b49d790c9f497257edec637db2eda5d18d8b219df18249b71a0`

Validation: length + both CRCs **PASS**; model=528, version=428.

## Capstone-verified byte changes

| Name | VA | App | File | Before | After | ASM |
|------|-----|-----|------|--------|-------|-----|
| G1 paperInfo.valid | `0x101467a` | `0x467a` | `0x4696` | `01d8` | `00bf` | `bhi #0x1014680` → `nop ` |
| G2 secondary used>all flag | `0x101809c` | `0x809c` | `0x80b8` | `00d9` | `00e0` | `bls #0x10180a0` → `b #0x10180a0` |
| G3 consumption bit19 site1 | `0x102754e` | `0x1754e` | `0x1756a` | `0ad9` | `0ae0` | `bls #0x1027566` → `b #0x1027566` |
| G4 consumption bit19 site2 | `0x1027632` | `0x17632` | `0x1764e` | `0ad9` | `0ae0` | `bls #0x102764a` → `b #0x102764a` |

## NFC (phone) alternative / complement

D11_H firmware embeds the same NTAG password `12 34 56 78` (auth cmd `1B`, expect `55 55`)
and the same TEA key halfwords `CCA1 72B7 6758 65C9` (RAM key table at `0x207a8`,
TEA at `0x01018c40`/`0x01018ca0`). Confidence keys match D110_M: **high (~85%)**,
but not proven against a dump of this exact sticker's pages 5–6.

Counter layout (pages 5–6): `uint16 reserved`, `uint16 used`, `uint32 crc32(first4)` then 32-round TEA.

### NFC Tools Advanced → custom commands batch (assumes reserved=0)

```
1B:12:34:56:78,A2:05:74:2F:C7:63,A2:06:E0:17:DB:F9,30:05
```

Expected readback of pages 5–6: `74 2F C7 63 E0 17 DB F9`

If reserved is not 0, dump pages 5–6 first and run:
`python niimbot_tag.py --counter-hex <8bytes> --used 0`
from the pranavms13 repo (preserves reserved).

**After NFC zeroing**, still run NiimBlue Reset on the history-reset firmware so the
printer cache cannot restore 201.

## Preferred method

1. **Flash this image** (fixes `paperInfo.valid` without phone) — preferred for this printer state.
2. Optionally also NFC-zero the sticker so official apps / future stock firmware see used≤all.
3. Confidence firmware fix unblocks print: **high (~90%)** for the used>all gate;
   residual risk if another unread check remains (existing A+D already force RFID OK / no err 20).
4. Confidence NFC batch alone with reserved=0: **medium-high (~75%)** without a dump verify.
