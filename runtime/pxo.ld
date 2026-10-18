ENTRY(pxo_entry)
SECTIONS {
  . = 0x20;
  .text : { KEEP(*(.text.pxo_entry)) KEEP(*(.text.pxo_init)) *(.text*) }
  .rodata : ALIGN(4) { *(.rodata*) }
  .data : ALIGN(4) { *(.data*) }
  .bss : ALIGN(4) { *(.bss*) *(COMMON) }
  /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment) *(.note*) }
}
