/* ARM EABI: divmod returns quotient in r0 and remainder in r1.
 * ARM926 has no hardware divide. Long division uses no libc or self-calls. */
.syntax unified
.arm
.text
.align 2
.global __aeabi_uidivmod
.type __aeabi_uidivmod,%function
__aeabi_uidivmod:
    cmp r1,#0
    moveq r1,r0
    moveq r0,#0
    bxeq lr
    mov r2,#0
    mov r3,#0
    mov ip,#32
1:
    lsls r0,r0,#1
    adc r3,r3,r3
    cmp r3,r1
    subcs r3,r3,r1
    adc r2,r2,r2
    subs ip,ip,#1
    bne 1b
    mov r0,r2
    mov r1,r3
    bx lr
.size __aeabi_uidivmod,.-__aeabi_uidivmod
.global __aeabi_idivmod
.type __aeabi_idivmod,%function
__aeabi_idivmod:
    push {r4,r5,r6,lr}
    eor r4,r0,r1
    mov r5,r0
    cmp r0,#0
    rsblt r0,r0,#0
    cmp r1,#0
    rsblt r1,r1,#0
    bl __aeabi_uidivmod
    cmp r4,#0
    rsblt r0,r0,#0
    cmp r5,#0
    rsblt r1,r1,#0
    pop {r4,r5,r6,pc}
.size __aeabi_idivmod,.-__aeabi_idivmod
