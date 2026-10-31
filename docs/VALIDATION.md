# Validation scope

## Existing product evidence

- Accepted AArch64 plugin SHA-256:
  `bab3b47378f314227e6be8f1736e68b86861df0dd3eacb1e90fd7c988499f80b`.
- Prior firmware407 ABI audit resolved 246 imports; 58-port ARM runtime checks
  covered legacy CV equivalence, six ×5 CV paths, unchanged audio/gates, quality
  modes, state and synthetic frozen-buffer restoration. These are inherited
  private-lab results, not a fresh public-kit hardware trial.
- Owner previously confirmed beta.5 with normal interface/audio on Hector.
- The beta.6 footer behavior was installed as a two-file correction and the owner
  confirms: “Looks good, the Back button and Bypass are both working.” Public
  source retains that behavior; the beta.6 label and complete Qt notice are new.

## Public package checks

Run `python3 -m unittest discover -s tests -v`. Filesystem tests use all selected
public stock407 UI source preimages and the real new UI files. The ELF in core
transaction fixtures is an inert stand-in, never executed. Cases cover exact
backup/restoration, metadata/xattrs, per-file interrupted publication/restoration,
changed-file refusal, symlinks/hardlinks, corrupted payload and journal tampering.
Device orchestration tests simulate hardware, services, mounts and reboot calls.
Native DSP checks build the actual portable source and use offline synthetic
signals; they do not open a soundcard. Export/archive checks verify the exact
file set, ELF architecture, complete corresponding source, checksums and exclusions.
The optional full Qt5 preview uses numeric backend fixtures.

## Trial on a pre-Mala 407 SD backup — October 30, 2026

The spare card was a full copy of the owner's October 13 SD backup, captured
before Mala installation. It was not freshly flashed from the vendor Beebo407
download. The SD image excludes Hector's separate internal NOR preset/settings
storage; the trial used that existing internal storage. Neither a factory-reset
preset baseline nor a complete firmware-tree match to the vendor download was
established. The public installer's required stock-file checks passed.

On that one Hector, the owner selected Hector mode through the vendor UI and
loaded Empty to obtain six inputs/eight outputs. The exact beta.6 public install
kit then ran from USB without SSH or network setup. One automatic restart
returned to the normal interface. The USB
report reads **INSTALLED AND VERIFIED**, the launcher log is empty, and all 231
USB package files still match the tested archive.

The owner confirmed the beta.6 editor, Back and Bypass, and audio through input 1
to a mixer; module controls were reported working. External MIDI/CV signals and
detailed frozen-buffer save/reload were not separately reported. An additional
boot with the install drive inserted returned normally without another restart;
the USB report remained **INSTALLED AND VERIFIED**.

The public rollback completed with one automatic restart. Its report reads
**ROLLBACK VERIFIED**; Mala was absent from the module menu and the launcher log
was empty. A further boot with the rollback drive inserted returned normally
without a second restart, and its report still confirmed no repeat rollback.
The owner reconfirmed six inputs/eight outputs and normal stock Input1-to-Output1
audio without distortion, crackling or dropouts. These are owner observations
and onboard verification reports, not an independent SSH or instrumented audit.
The public USB reports contain no per-boot identifiers.

## Completed checks and remaining coverage

| Check | Evidence |
| --- | --- |
| FAT32 USB installation without SSH/network setup | Passed on the recorded one-unit407 backup-card baseline |
| Automatic restart and installed-file verification | INSTALLED AND VERIFIED; owner opened beta.6 |
| Basic audio, Back, Bypass and editor controls | Owner-confirmed working |
| Additional startup with install drive left inserted | Normal startup without a second restart; success report retained |
| Public USB rollback and restored-file verification | ROLLBACK VERIFIED; Mala absent from browser |
| Normal stock screen, six inputs/eight outputs and audio after removal | Owner-confirmed working |
| Additional startup with rollback drive left inserted | Normal startup without a second restart; rollback report retained |
| Incompatible preflight refusal and interrupted transactions | Host fixtures; not a deliberate incompatible-device or power-cut trial |
| External MIDI/CV and detailed Freeze save/reload on this public kit | Not separately repeated; earlier private/software evidence only |
| Fresh vendor-download card, long-run reliability and physical power-loss recovery | Not qualified by this trial |

Publish these limits with any beta download. Do not describe the results as a
fresh vendor-download, factory-reset or broad hardware qualification. Additional
tester reports can expand coverage without changing the recorded scope of this
trial. Firmware-changing or deliberately incompatible fixtures are not required
on an owner's working unit to repeat host refusal tests.

The hardware trial used these original kit checksums:

- Install ZIP: `f5ca2fa6e8d61d60966aab7502d19fba065a0a562920f8a60fc4054ae11fcf8a`.
- Rollback ZIP: `21fea97e83e55f6ea3024b2b63965d45c794c985690a147fb3e0ec4698e1c24d`.

The publication candidate refreshes documentation after that trial. Archive
comparison must confirm its launcher, installer, transaction code, manifest and
all34 installed payload files remain identical to the tested kits. Release
SHA256SUMS identify the final download bytes; the above hashes identify the
historical hardware-tested archives.

Record actual observations and limitations. Physical power interruption, card
failure and offline recovery remain separate, unvalidated scenarios. The owner's
working SD and Mala/Link software were kept separate and unchanged during this trial.

The extra boots with an already installed or already rolled-back kit are
**release-validation checks for a drive accidentally left inserted**. They are
not additional installation/removal steps for ordinary users. Public instructions
say to keep USB connected through the automatic reboot, then remove it after
startup and leave it disconnected during normal use.
