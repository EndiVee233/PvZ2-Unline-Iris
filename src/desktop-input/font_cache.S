.syntax unified
.arm
.text
.global iris_build_glyph_mesh
// PrimeGlyphMesh::Build already allocated the vertex buffer. On atlas
// exhaustion, invalidate cached meshes through PrimeFontManager's generation
// counter, discard this partial batch and retry once with the existing buffer.
iris_build_glyph_mesh:
    push {r4-r8, lr}
    mov r4, r0
    mov r5, r1
    mov r6, r2
    mov r7, r3
    bl iris_build_glyph_part
    cmp r0, #1
    popeq {r4-r8, pc}
    bl iris_get_font_manager
    bl iris_clear_glyph_cache
    ldr r0, [r4, #0x34]
    str r0, [r4, #0x38]
    mov r0, #0
    str r0, [r4, #0x30]
    mov r0, r4
    mov r1, r5
    mov r2, r6
    mov r3, r7
    bl iris_build_glyph_part
    cmp r0, #1
    beq 1f
    // A glyph larger than the atlas must not leave a partially valid mesh.
    ldr r0, [r4, #0x34]
    str r0, [r4, #0x38]
    mov r0, #0
    str r0, [r4, #0x30]
1:
    mov r8, r0
    mov r0, #4
    adr r1, tag
    adr r2, message
    bl iris_log_write
    mov r0, r8
    pop {r4-r8, pc}
tag: .asciz "IrisGlyphCache"
message: .asciz "Atlas full: invalidated cached meshes and retried text layout"
.balign 4
