#ifndef U310_NATIVE_H
#define U310_NATIVE_H
#include <stdint.h>
#include "u310.h"
/* Experimental native escape hatch. Offsets are BYTES, not slot numbers.
 * Zero means outside catalog bounds, a stub or a non-code candidate.
 * A nonzero pointer does NOT validate the C prototype, ownership or task context.
 * Consult sdk/api/catalog.json and disassembly before calling it. */
uintptr_t u310_native_method(uint32_t group_offset, uint32_t method_offset);
/* Experimental diagnostics: raw live table, no inferred bounds. */
uintptr_t u310_native_exports(void);
/* Experimental filesystem exports, inferred from U310 FileSys disassembly.
 * U880 signatures still require hardware validation. Creates/truncates path. */
u310_file u310_file_create(const uint16_t *path);
/* Mode 0: existing file, read/write; does not create or truncate. */
u310_file u310_file_open_update(const uint16_t *path);
int32_t u310_file_write(u310_file file, const void *buffer, uint32_t size);
#define U310_NATIVE_GRAPHICS 0x18u
#define U310_NATIVE_FILESYSTEM 0x38u
#define U310_NATIVE_UI 0x48u
#define U310_NATIVE_SYSTEM 0x50u
#define U310_NATIVE_UTF16 0x68u
#endif
