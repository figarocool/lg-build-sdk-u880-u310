# LG Build SDK — U880 / U310

[Documentazione italiana](README.md)

A C SDK for native PXO applications on **LG U310 and LG U880**. Compile the same source with `--target u310` or `--target u880`; the resulting binaries are specific to their model and firmware.

Reference firmware: **U310 H3G V10a (12 October 2006)** and **U880 H3G Italy V10b (8 February 2006)**. Other versions require API and container validation. Included: PXO packaging tools, C headers, runtime, Hello World and colorbars examples. No firmware, original Calculator, keys, unlock applications or unlock tests are distributed.

## Linux installation

Ubuntu/Debian:

```bash
sudo apt update
sudo apt install git python3 python3-venv clang lld fonts-dejavu-core
git clone https://github.com/figarocool/lg-build-sdk-u880-u310.git
cd lg-build-sdk-u880-u310
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python u310sdk.py doctor
```

`doctor` checks Clang, LLD and Python dependencies and reports missing templates. Missing templates are expected on a fresh installation. Clang generates ARM926EJ-S Thumb code directly; ARM GCC is unnecessary.

## Windows installation

Install **WSL2 with Ubuntu** from an administrator PowerShell:

```powershell
wsl --install -d Ubuntu
```

Restart if requested, finish Ubuntu user setup, then run the Linux instructions inside Ubuntu. Keep the checkout in the Linux home directory, such as `~/lg-build-sdk-u880-u310`. Native CMD/PowerShell builds are not configured. Linux builds were verified; the WSL procedure was not executed on a Windows PC for this publication.

## Import your original template

Obtain your own **original Calculator.pxo** from `MODULE/UPLOAD/Pxo/Calculator.pxo` in compatible firmware. A Calculator already replaced by homebrew cannot serve as the template. SHA-256 verification rejects different templates. The SDK does not download or decrypt firmware.

Import either or both models:

```bash
python u310sdk.py import-template /path/to/u310/Calculator.pxo --target u310
python u310sdk.py import-template /path/to/u880/Calculator.pxo --target u880
python u310sdk.py doctor
```

Private copies stay in Git-ignored `templates/`. For larger applications, also import the original Version file using `--version /path/to/Version`.

## Build Hello World

For U310:

```bash
python u310sdk.py build examples/hello --target u310
python u310sdk.py inspect examples/hello/build/Calculator.pxo
```

For U880:

```bash
python u310sdk.py build examples/hello --target u880
python u310sdk.py inspect examples/hello/build/Calculator.pxo
```

Output: `examples/hello/build/Calculator.pxo`. Each build replaces the previous output; save separate copies when targeting both models. The JSON report identifies the target, size and relocations.

The example source is:

```c
#include "u310.h"
#include "hello_bitmap.h"

void app_draw(void) {
    u310_clear(0);
    u310_draw_bitmap(0, 90, hello_bitmap);
    u310_present();
}
```

`app.json` lists sources and text; Pillow generates `hello_bitmap.h` at build time. The historical header name `u310.h` also applies to U880: target selection adapts the runtime. The screen is 176×220, and the runtime handles the Back key.

Start a project with:

```bash
python u310sdk.py new my_app
python u310sdk.py build my_app --target u880
```

## Run on your phone

The example occupies the **Calculator slot**. Back up your original Calculator.pxo, then replace the phone's `UPLOAD/Pxo/Calculator.pxo` through your existing working PXO transfer method, using the binary for the correct model. Restart and open **Accessories → Calculator**. Hello World appears; Back closes the application. Restore the original file to restore Calculator.

Copying a PXO onto the SD card does not install it, and renaming a PXO does not add a menu entry. This SDK includes no USB uploader and never modifies the phone automatically. For simulation, use the separate [LG Mobile Emulator](https://github.com/figarocool/lg-mobile-emulator) with your own firmware. The old local `run`/`emulate` commands are not included in this standalone SDK.

Default builds preserve the original Calculator's size and additive checksum (42,034 bytes on U310; 42,030 on U880), so Hello World needs no replacement Version file. Advanced `build --size 0x20000` also generates `build/Version` when an original Version was imported. Both files must then be transferred, and Version must match the other installed PXOs. Begin with the default example.

## Limits and validation

This is freestanding C without POSIX, SDL or a complete libc. Available APIs are declared in `include/`; not every internal firmware API has been validated on both phones. The examples do not alter CODE, radio settings or SIM state. Hello World and colorbars were built for both targets using original templates for this publication; size, checksum and target selection were checked. These checks do not establish compatibility with other firmware versions.

Source-available, noncommercial hobby license: see [LICENSE](LICENSE), including its English summary. Firmware and trademarks belong to their respective owners.
