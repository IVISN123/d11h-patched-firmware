# Niimbot D11_H 4.28 — private firmware patches

**Private / personal use only.** Unofficial modifications of Niimbot D11_H firmware 4.28 (model ID 528, hardware 4.01). Flashing can brick the printer; D11_H refuses downgrades. Not affiliated with Niimbot. Flash at your own risk.

Target device example: serial `HA18013182`, protocol 5, 300 DPI.

## What this fixes

Stock 4.28 (and related builds) can refuse or weakly print when the roll RFID check fails or the tag reports `usedPaper > allPaper`. These images keep version **4.28** and rebuild Niimbot `0x18` header CRCs so they flash via [NiimBlue](https://niim.blue/) (Chrome → gear → Firmware).

| File | Patches | Purpose |
|------|---------|---------|
| `firmware/patched/D11_H_4.28_rfid-bypass.bin` | A+D | Skip WriteRfidFail / error 20 when RFID read fails |
| `firmware/patched/D11_H_4.28_rfid-bypass-density.bin` | A+D+E | Also force no-tag heat-slot count (fixes near-blank prints) |
| `firmware/patched/D11_H_4.28_rfid-bypass-density-history-reset.bin` | A+D+E+F | Factory reset (cmd `0x28`) also clears remembered roll history |
| `firmware/patched/D11_H_4.28_rfid-bypass-density-history-reset-used-ignore.bin` | A+D+E+F+G | **Recommended.** Ignore `usedPaper > allPaper` so a readable but “overused” tag still prints |

Original / stock copies:

- `firmware/original/D11_H_4.28_original.bin` — exact testing 4.28 used as base
- `firmware/stock/` — official images retained for comparison (not recovery if brick)

Checksums: `firmware/SHA256SUMS.txt`.

## Docs

| Doc | Contents |
|-----|----------|
| `docs/RFID_RE_REPORT.md` | RE of error 20 / RFID poll / bit19 |
| `docs/PATCH_MANIFEST.md` | Patches A+D |
| `docs/DENSITY_PATCH_MANIFEST.md` | Patch E (density / heat slots) |
| `docs/HISTORY_RESET_PATCH_MANIFEST.md` | Patch F (history clear on reset) |
| `docs/USED_IGNORE_PATCH_MANIFEST.md` | Patch G (used>all ignore) |

## Flash (NiimBlue)

1. Close the official Niimbot app. Prefer USB power during flash.
2. Open https://niim.blue/ in Chrome/Edge, connect Bluetooth.
3. Gear → Firmware → select the patched `.bin`. Version stays **4.28**.
4. Wait for reboot. Print from Метка or NiimBlue; density max if needed.

## Notes

- Patch G does **not** rewrite the NFC sticker counter; it only stops the firmware treating an overused tag as invalid.
- Optional phone NFC counter zero (D110_M-style) is documented in the used-ignore manifest; verify pages before writing.
- Related web UI: https://github.com/IVISN123/metka

## License / IP

Niimbot original firmware remains third-party material. This repository keeps copies for the owner’s repair/research on their own hardware and does not claim ownership of Niimbot code.
