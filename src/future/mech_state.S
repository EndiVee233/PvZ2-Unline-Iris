.syntax unified
.arm
.text
.global iris_mech_laser_start

// Branch table used by the three original call sites.
iris_mech_laser_start:
    b .Lbegin
    b .Lwalk
    b .Ltick
    b .Linit
    b .Lscorch
    b .Lbind_scorch
    b .Lleave_walk
    b .Ldestroy

.Lbegin:
    push {r4, lr}
    mov r4, r0
    bl iris_find_laser_target
    ldr r0, [r4, #0x1a4]
    cmp r0, #1
    popne {r4, pc}
    mov r0, r4
    bl iris_stop_walking
    mov r0, r4
    adr r1, .Lstart
    bl .Lplay
    mov r0, #1
    strb r0, [r4, #0x1f0]
    mov r0, r4
    ldr r1, .Lstart_sound_offset
.Lstart_sound_pc:
    add r1, pc, r1
    bl .Lpost_sound
    pop {r4, pc}
.Lstart_sound_offset:
    .word .Llaser_sound - (.Lstart_sound_pc + 8)

.Lwalk:
    // Keep the ordinary walk callback available after an interrupted shot.
    ldr r1, [r0, #0x1a4]
    cmp r1, #0
    bxne lr
    ldrb r1, [r0, #0x1a8]
    cmp r1, #0
    beq iris_update_walking
    ldrb r2, [r0, #0xa8]
    tst r2, #1
    bne iris_update_walking
    push {r4, lr}
    mov r4, r0
    bl iris_start_walking
    mov r0, r4
    pop {r4, lr}
    b iris_update_walking

.Ltick:
    push {r4-r8, lr}
    mov r4, r0
    mov r5, r1
    sub r6, r4, #0x1a0
    ldr r7, [r4, #4]
    ldrb r8, [r4, #8]
    cmp r8, #0
    beq .Lwait_for_pose
    mov r0, r6
    bl .Lstop
    b .Ladvance
.Lwait_for_pose:
    // The authored wind-up and recovery both terminate on a stop frame.
    cmp r7, #1
    cmpne r7, #3
    bne .Ladvance
    add r0, r6, #0x40
    bl iris_get_zombie_rig
    ldr r1, [r6, #0x188]
    bl iris_rig_animation_finished
    cmp r0, #0
    popeq {r4-r8, pc}
.Ladvance:
    mov r0, r4
    mov r1, r5
    bl iris_update_laser
    ldr r0, [r4, #4]
    cmp r0, r7
    popeq {r4-r8, pc}
    cmp r8, #0
    popne {r4-r8, pc}
    cmp r0, #0
    beq .Lresume
    cmp r0, #2
    beq .Lsweep
    mov r0, r6
    bl .Lstop
    adr r1, .Lend
    b .Lnext_pose
.Lsweep:
    adr r1, .Lidle
.Lnext_pose:
    mov r0, r6
    bl .Lplay
    pop {r4-r8, pc}
.Lresume:
    mov r0, r6
    bl iris_start_walking
    pop {r4-r8, pc}

.Lstart: .asciz "laser_start"
.Lidle: .asciz "laser_idle"
.Lend: .asciz "laser_end"
.Llaser_sound: .asciz "Play_Zomb_Future_Gargantuar_Mvmt_Attack_DeathRay"
.Lend_sound: .asciz "Play_Zomb_Future_Gargantuar_Mvmt_Attack_DeathRay_End"
.align 2

.Lplay:
    // Match the engine's one-shot animation call used for eating and
    // gargantuar attacks. Its returned handle lets the phase wait for the rig.
    push {r4-r8, lr}
    sub sp, sp, #0x48
    mov r4, r0
    mov r5, r1
    add r0, r4, #0x40
    bl iris_get_zombie_rig
    mov r8, r0
    add r0, sp, #0x40
    mov r1, r5
    add r2, sp, #0x38
    bl iris_make_string
    ldr r6, .Lplay_base
.Lplay_pc:
    add r6, pc, r6
    ldr r0, =iris_state_patch_base
    sub r6, r6, r0
    mov r2, #0
    str r2, [sp, #0x0c]
    str r2, [sp, #0x10]
    str r2, [sp, #0x14]
    str r2, [sp, #0x18]
    str r2, [sp, #0x24]
    str r2, [sp, #0x28]
    str r2, [sp, #0x2c]
    str r2, [sp, #0x30]
    ldr r0, =0xccbf98
    add r0, r6, r0
    str r0, [sp, #0x20]
    ldr r0, =0xccc108
    add r0, r6, r0
    str r0, [sp, #8]
    add r0, sp, #8
    str r0, [sp]
    mov r0, r8
    add r1, sp, #0x40
    add r3, sp, #0x20
    ldr r8, [r8]
    ldr r8, [r8, #0x98]
    blx r8
    str r0, [r4, #0x188]

    add r0, sp, #0x40
    add r1, sp, #0x38
    bl .Lrelease_string
    add sp, sp, #0x48
    pop {r4-r8, pc}
.Lplay_base:
    .word iris_mech_laser_start - (.Lplay_pc + 8)

.Linit:
    // The allocator and reflected class size reserve this transient tail.
    str r0, [r4, #0x1e4]
    str r0, [r4, #0x1e8]
    str r0, [r4, #0x1ec]
    str r0, [r4, #0x1f0]
    b iris_after_mech_init

.Lscorch:
    // The damage tick already computed the current impact point on its stack.
    add r0, r4, #0x1e8
    bl iris_lock_scorch_effect
    cmp r0, #0
    beq .Lnew_scorch
    add r1, sp, #0x60
    mvn r2, #0
    bl iris_set_scorch_position
    b iris_after_scorch
.Lnew_scorch:
    str r4, [sp, #0x54]
    b iris_spawn_scorch

.Lbind_scorch:
    ldr ip, [sp, #0x54]
    push {r4, r5, r6, lr}
    mov r4, r0
    mov r5, ip
    // Aster plays the hit animation at half speed for the whole sweep.
    mov r2, #0x3f000000
    bl iris_play_scorch
    add r0, r5, #0x1e8
    ldr r2, [r4, #8]
    ldr r3, [r4, #0xc]
    bl iris_assign_weak
    pop {r4, r5, r6, pc}

.Lleave_walk:
    push {r0, lr}
    bl .Lstop
    pop {r0, lr}
    push {fp, lr}
    b iris_after_walk_exit_prologue

.Ldestroy:
    push {r0, lr}
    bl .Lstop
    pop {r0, lr}
    b iris_destroy_zombie_base

.Lstop:
    push {r4, lr}
    mov r4, r0
    ldrb r1, [r4, #0x1f0]
    cmp r1, #0
    beq .Lhide_scorch
    mov r1, #0
    strb r1, [r4, #0x1f0]
    ldr r1, .Lend_sound_offset
.Lsound_pc:
    add r1, pc, r1
    bl .Lpost_sound
.Lhide_scorch:
    add r0, r4, #0x1e8
    ldr r2, [r0]
    ldr r3, [r0, #4]
    orrs r2, r2, r3
    popeq {r4, pc}
    bl iris_lock_scorch_effect
    cmp r0, #0
    movne r1, #0
    blne iris_hide_scorch
    add r0, r4, #0x1e8
    mov r2, #0
    mov r3, #0
    bl iris_assign_weak
    pop {r4, pc}
.Lend_sound_offset:
    .word .Lend_sound - (.Lsound_pc + 8)

.Lpost_sound:
    push {r4, lr}
    sub sp, sp, #8
    mov r4, r0
    mov r0, sp
    add r2, sp, #4
    bl iris_make_string
    mov r0, r4
    mov r1, sp
    mov r2, #0
    bl iris_post_zombie_sound
    mov r0, sp
    add r1, sp, #4
    bl .Lrelease_string
    add sp, sp, #8
    pop {r4, pc}

.Lrelease_string:
    push {r4, r5, r6, lr}
    mov r4, r1
    ldr r5, [r0]
    ldr r6, .Lstring_base
.Lstring_pc:
    add r6, pc, r6
    ldr r0, =iris_state_patch_base
    sub r6, r6, r0
    ldr r0, =0xd0048c
    ldr r0, [r6, r0]
    sub r6, r5, #0xc
    cmp r6, r0
    popeq {r4, r5, r6, pc}
    sub r0, r5, #4
    mvn r1, #0
    bl iris_string_release
    cmp r0, #0
    popgt {r4, r5, r6, pc}
    mov r0, r6
    mov r1, r4
    bl iris_string_destroy
    pop {r4, r5, r6, pc}
.Lstring_base:
    .word iris_mech_laser_start - (.Lstring_pc + 8)

.ltorg
