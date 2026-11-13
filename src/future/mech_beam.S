.syntax unified
.arm
.fpu vfpv3
.text
.global iris_draw_mech_beam
.type iris_draw_mech_beam, %function

// r0: mech, r1: board graphics, r2/r3: beam endpoints in board coordinates.
iris_draw_mech_beam:
    push {r4-r8, lr}
    vpush {d8-d11}
    sub sp, sp, #16
    mov r4, r0
    mov r5, r1

    // Center the original PAM between the two endpoints.
    vldr s0, [r2]
    vldr s2, [r3]
    vldr s4, [r2, #4]
    vldr s6, [r3, #4]
    vldr s8, [r2, #8]
    vldr s10, [r3, #8]
    vmov.f32 s16, #0.5
    vadd.f32 s18, s0, s2
    vadd.f32 s20, s4, s6
    vadd.f32 s22, s8, s10
    vmul.f32 s18, s18, s16
    vmul.f32 s20, s20, s16
    vmul.f32 s22, s22, s16
    vstr s18, [sp]
    vstr s20, [sp, #4]
    vstr s22, [sp, #8]

    // The board projects a point as (x, y - z). The effect angle uses -dy.
    vsub.f32 s18, s2, s0
    vsub.f32 s20, s6, s4
    vsub.f32 s22, s10, s8
    vsub.f32 s20, s22, s20
    vmul.f32 s0, s18, s18
    vmla.f32 s0, s20, s20
    vsqrt.f32 s22, s0
    vcmpe.f32 s22, #0
    vmrs APSR_nzcv, FPSCR
    beq .Lreturn
    vmov r0, s20
    vmov r1, s18
    bl iris_atan2f
    mov r8, r0

    add r0, r4, #0x198
    bl iris_lock_beam_effect
    mov r7, r0
    bl iris_get_pop_anim
    ldr r0, [r0, #0x14]
    ldr r1, [r0, #0x78]
    cmp r1, #0
    beq .Lreturn
    vmov s0, r1
    vcvt.f32.s32 s0, s0
    vldr s2, [r0, #0x4c]
    vmul.f32 s0, s0, s2
    ldr r0, .Lapp_got
.Lapp_pc:
    add r0, pc, r0
    ldr r0, [r0]
    ldr r0, [r0]
    add r0, r0, #0x6a0
    vldr s2, [r0]
    vmul.f32 s22, s22, s2
    vdiv.f32 s22, s22, s0

    // Set the beam effect's scale, rotation and centering before its
    // normal position setter rebuilds the PopAnim transform.
    vstr s22, [r7, #0x90]
    mov r0, #0x3f800000
    str r0, [r7, #0x94]
    str r8, [r7, #0x98]
    mov r0, #1
    strb r0, [r7, #0x8c]
    mov r0, r7
    mov r1, sp
    mvn r2, #0
    bl iris_set_effect_world_position

    mov r0, r7
    mov r1, #1
    bl iris_set_effect_visible
    mov r0, r7
    mov r1, r5
    bl iris_draw_effect
    mov r0, r7
    mov r1, #0
    bl iris_set_effect_visible
.Lreturn:
    add sp, sp, #16
    vpop {d8-d11}
    pop {r4-r8, pc}

.Lapp_got:
    .word 0xd00880 - (0x63fc3c + .Lapp_pc - iris_draw_mech_beam + 8)
.size iris_draw_mech_beam, . - iris_draw_mech_beam

.org 0x1c0
    .asciz "laser_beam"
    .asciz "laser_hit"
