/* Minimal layout for QEMU mps2-an386 (Cortex-M4): code at 0, data in SSRAM2. */
MEMORY { FLASH (rx) : ORIGIN = 0x00000000, LENGTH = 4M
         RAM (rwx)  : ORIGIN = 0x20000000, LENGTH = 4M }
ENTRY(reset)
SECTIONS {
    .text : { KEEP(*(.vectors)) *(.text*) *(.rodata*)
              KEEP(*(.init)) KEEP(*(.fini)) . = ALIGN(4); } > FLASH
    .ARM.exidx : { *(.ARM.exidx*) } > FLASH
    __etext = .;
    .data : AT(__etext) { __data_start__ = .; *(.data*) . = ALIGN(4); __data_end__ = .; } > RAM
    .bss (NOLOAD) : { __bss_start__ = .; *(.bss*) *(COMMON) . = ALIGN(4); __bss_end__ = .; } > RAM
    end = .;
    __stack = ORIGIN(RAM) + LENGTH(RAM);
}
