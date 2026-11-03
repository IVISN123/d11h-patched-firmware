# Niimbot D11_H firmware 4.28 — RFID / Print error 20 RE report

**Scope:** analysis only. No flashable image was built or proposed for install.  
**Target image:** `/workspace/d11h/t_D11_H_4.28.bin` (testing channel, version 4.28).  
**Device context:** D11_H, FW 4.28, HW 4.01, protocol 5, serial HA18013182; every roll reports “метка не прочитана”; PrintStart → `In_PrintError` with payload `0x14` (WriteRfidFail).

---

## 1. Firmware image format

Matches the NiimBlue / printers.niim.blue **0x18** update container (same family as the D110_M patched-firmware project):

| Offset | Field | 4.28 value |
|--------|--------|------------|
| 0x00 | Signature | `0x18` |
| 0x01–0x03 | Nonce (zeroed for header CRC) | `47 14 19` |
| 0x04 | Payload length | `0x000241d4` (147924) |
| 0x08 | CRC32(payload) | `0xbc6f0e6d` (verified) |
| 0x0C–0x13 | Reserved | zeros |
| 0x14 | Version (u16) | `428` → 4.28 |
| 0x16 | Model ID (u16) | `528` (D11_H) |
| 0x18 | CRC32(header w/ bytes 1–3 zero) | verified |
| 0x1C… | Application payload | raw ARM |

**Payload is not DEFLATE-compressed** (unlike B1 Pro-style images). It is a raw Cortex-M **Thumb-2** application:

- Initial SP: `0x00070000`
- Reset vector: `0x010100cd` → handler at `0x010100cc`
- **Load / code base: `0x01010000`**
- App file offset = `VA − 0x01010000`; container file offset = `28 + app offset`
- Payload SHA-256: `6fd673fcd924ed7a…`

This matches the D110_M reference project’s base address and header rebuild rules (length + both CRCs). That project’s patch only clears NFC *used-count history* on factory reset — it does **not** disable RFID authentication.

---

## 2. How Print error 20 is produced

### 2.1 Wire path (matches user packet log)

PrintStart handlers call `get_print_status` at **`0x0101e03c`**, which wraps **`0x0101e054`**:

1. Load status bitmask word from RAM **`[0x000207ec + 0x14]`** = `0x00020800`.
2. Map set bits → error codes 1…0x0F via successive `lsls` / `bpl` tests.
3. If **bit 19** of that word is set (`value & 0x00080000`), return **`0x14` (20)**.

Call sites that turn a non-{0,7} status into `In_PrintError` (`cmd 0xdb`, 1-byte payload = status):

- `0x010142c8` → `bl 0x0101e03c`
- `0x0101814e` → `bl 0x0101e03c`
- (also `0x010180ec`, `0x01018402`, `0x0101c6b4`, `0x01023bce`)

So the user’s `55 55 db 01 14 …` is exactly: PrintStart → status decode → bit19 set → error 20.

### 2.2 Who sets bit 19 (WriteRfidFail latch)

Three sites OR `1<<19` into `[0x207ec+0x14]`:

| VA | Role |
|----|------|
| **`0x0101f22a`** | **Primary RFID-read-failed path** (after 3 failed reads) |
| `0x01027556` | Label/consumption overflow vs RFID-stored limit (log code `0x300e`) |
| `0x0102763a` | Similar consumption check (log code `0x300d`) |

Symmetric **clear** of bit 19:

| VA | Role |
|----|------|
| **`0x01024b20`** | RFID state reset: `flag@+8 = 0`, clear bit19 |
| **`0x0101f158`** | RFID success apply: `flag@+8 = 1`, clear bit19, copy tag fields |

RFID “OK” flag byte: **`[0x000491c8 + 8]`** (0 = not read / fail, 1 = success). Test-menu strings `"rfid read failed"` / `"rfid read success"` branch on this same flag.

### 2.3 RFID poll / fail function (heart of error 20 for “метка не прочитана”)

**`0x0101f1d8`** — periodic / driven RFID poll:

```
retries = 0
loop up to 3:
  call RFID_read (0x01024c30) with channel 0
  if return == 0: goto SUCCESS (0x0101f232)  // applies 0x0101f158
  retries++
FAIL epilogue (0x0101f21c..0x0101f22e):
  [0x491c8+8] = 0          // flag clear (r5 is 0)
  OR bit19 into status word // latch WriteRfidFail
  return
```

Callers of the poll:

- `0x01023d5c` — thin wrapper: `bl 0x01024b20` (clear) then `bl 0x0101f1d8` (poll)
- `0x01024dda` — RFID task state machine when a request bit is set

**`0x01024c30`** — low-level RFID/NFC read into object `0x491c8` (or `+0x84` for channel 1): talks to tag via `0x01015d18` / `0x01015df8`, copies pages, verifies checksums (`0x0101c5d0`). Non-zero return = hard read failure (feeds the 3-strike loop above).

**Conclusion for the user’s symptom:** the printer never successfully reads the roll tag → poll fails → bit19 latched → every PrintStart reports error 20. This matches diagnostics (“RFID рулона: Метка не прочитана”) and the official app behaving the same.

---

## 3. Candidate binary patches (not built)

All offsets for **t_D11_H_4.28.bin** only. Verify bytes before any future edit; rebuild header length + both CRC32s like the D110_M project.

### Candidate A — force success branch (smallest)

| | |
|--|--|
| VA | `0x0101f1fa` |
| App offset | `0xf1fa` |
| File offset | `0xf216` |
| Before | `1a d0` (`beq` → success @ `0x0101f232`) |
| After | `1a e0` (`b` unconditional to same target) |
| Size | **1 byte** (high byte `d0`→`e0` at file `0xf217`) |

Effect: after any RFID_read attempt, always take the SUCCESS path (call `0x0101f158`: set flag=1, clear bit19, copy whatever tag buffer contents exist).  
Risk: if the read left garbage/zeros, label geometry and remaining-count logic still consume those fields (`0x27556` / `0x2763a` can still set bit19 later).

### Candidate B+C — rewrite fail epilogue

| | B | C |
|--|--|--|
| VA | `0x0101f220` | `0x0101f22c` |
| File | `0xf23c` | `0xf248` |
| Before | `0d 72` `strb r5,[r1,#8]` (stores 0) | `11 43` `orrs r1,r2` |
| After | `0a 72` `strb r2,[r1,#8]` (stores 1; r2 already 1) | `00 bf` `nop` |
| Size | 2 + 2 bytes | |

Effect: the “failed after retries” path pretends success for the flag and does not latch bit19. Does not by itself populate tag metadata.

### Candidate D — neutralize status decoder

| | |
|--|--|
| VA | `0x0101e0de` |
| File | `0xe0fa` |
| Before | `14 20` `movs r0,#0x14` |
| After | `00 20` `movs r0,#0` |
| Size | 2 bytes |

Effect: even if bit19 is set, PrintStart’s status check returns OK. Other code that reads the bit or `flag@+8` directly is unaffected; consumption OR-sites can still run.

### Practical patch sets

1. **Minimal experiment:** A alone (1 byte).  
2. **More defensive:** A + D, or B+C + D.  
3. **Still required after any of these:** header rebuild (length if size changes; always payload CRC32 + header CRC32). Model ID `528` and version should stay `428` unless deliberately spoofing the update channel.

---

## 4. Version comparison (why “before the update it printed without a tag” fits)

| Image | Model | Ver | Payload | bit19-OR sites | `movs r0,#0x14; bx lr` (status→20) |
|-------|-------|-----|---------|----------------|-------------------------------------|
| s_4.18 / t_4.19 | 528 | 418/419 | ~145584 | **0** | **0** |
| t_4.20 … t_4.28 | 528 | 420–428 | 146688–147924 | **3** | **1** |
| s_4.23 / s_4.27 | 528 | 423/427 | … | 3 | 1 |

The dedicated **status bit19 → Print error 20** path appears starting at **testing 4.20 / stable lineage from ~4.23**. 4.18 still has test-menu RFID strings and some `0x14` stores, but not this PrintStart gate.

4.27t → 4.28t: payload **+216 bytes**; RFID fail / bit19 machinery still present in both (addresses shifted; e.g. bit19-OR at `0x101f242` in 4.27 vs `0x101f22a` in 4.28). So 4.28 did not invent the check — it continues it. Moving from a pre-4.20 build to 4.28 would explain a sudden hard RFID requirement.

D11_H refuses downgrades below the installed version, so returning to 4.18/4.19 via the normal updater is not available.

---

## 5. Feasibility and risk verdict

| Question | Assessment |
|----------|------------|
| Located RFID-failed → error 20 path? | **Yes**, with high confidence (status bit19 ↔ `0x14`; poll `0x101f1d8`; read `0x1024c30`; PrintStart via `0x101e03c`). |
| Small reliable patch possible in principle? | **Yes** — on the order of **1–6 bytes** at well-identified sites, plus header CRC rebuild. |
| Confidence patch alone restores printing | **Medium for “software-only refuse”**, **Low–medium if the RFID reader HW is dead**. User sees unread tag on *every* roll including in the official app → strongly suggests reader/antenna/firmware policy, not a single bad sticker. A patch can skip the *policy* gate; it cannot fix a dead reader if print/feed still needs tag-derived geometry. |
| Side effects | Flag and RFID fields feed **remaining-label / length checks** (`0x27556`, `0x2763a`). Forcing “success” with empty tag data may later re-raise error 20 as “over limit”, or print wrong label length. Density / task D110M_V4 may still assume RFID write during printStart9b-style flows. |
| Brick risk | **Real.** Wrong image, bad CRCs, or a patch that corrupts adjacent Thumb instructions can soft-brick; community recovery for Niimbot often needs SWD/probe soldering. D11_H also **will not accept lower version** official images. Analysis-only recommendation: do **not** flash until (1) a known-good original 4.28 is kept, (2) patch bytes are re-verified on the exact file hash, (3) user accepts brick risk, preferably with hardware backup plan. |
| Relation to D110_M “patched firmware” repo | **Different problem.** That repo resets NFC used-count history; it does not bypass read/auth. A D11_H “print without tag” patch would be a new, more invasive change. |

**Verdict:** A localized bypass of the WriteRfidFail latch is **technically identified and looks patchable in a few bytes**, but it is **not a safe or guaranteed fix** for this unit: the failure mode is “tag never read,” which may be hardware. Prefer warranty / Niimbot support (FW 4.28 testing build, SN HA18013182, HW 4.01, unread RFID on all rolls) before any flash experiment. If a patch is ever attempted, start with candidate **A** on a disposable test unit or with SWD recovery ready — **not produced in this pass.**

---

## 6. Key addresses cheat-sheet (VA, base `0x01010000`)

| Symbol | VA |
|--------|-----|
| App base / vectors | `0x01010000` |
| get_print_status | `0x0101e03c` / decode `0x0101e054` |
| Error 20 return (`movs r0,#0x14`) | `0x0101e0de` |
| RFID poll (3 strikes → fail) | `0x0101f1d8` |
| Force-success branch site | `0x0101f1fa` |
| Fail epilogue bit19 OR | `0x0101f22a` |
| Success apply (flag=1, clear bit19) | `0x0101f158` |
| RFID clear (flag=0, clear bit19) | `0x01024b20` |
| RFID_read | `0x01024c30` |
| Status RAM object | `0x000207ec` (+0x14 = bitflags) |
| RFID object / flag | `0x000491c8` (+8 = OK flag) |
| In_PrintError builder helper | `0x01016034` (r0 = code) |

---

*Generated from Capstone 5.x disassembly of official images under `/workspace/d11h/`. No modified firmware artifact was written.*
