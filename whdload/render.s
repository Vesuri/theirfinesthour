;*---------------------------------------------------------------------------
; CUSTOM2: render buffers in public memory (data/bob v1.1).
;
; The 3D view is drawn into packed 4-bit chunky buffers (8 pixels per longword)
; that the game allocates as MEMF_CHIP, only because the sky/ground fill at
; bob:29084 uses the blitter.  With this option they are MEMF_PUBLIC (fast RAM when
; there is any, chip otherwise) and the fill is done by the CPU.  Everything the
; display hardware reads (bitplanes, copper lists, sprites) stays in chip memory.
;---------------------------------------------------------------------------

; < A2: resload, D7: seglist (BPTR)
render_patch	move.l	(_custom2,pc),d0
		beq.b	.done
		lea	(_pl_render,pc),a0
		move.l	d7,a1
		jsr	(resload_PatchSeg,a2)
.done		rts

_pl_render	PL_START
		PL_W	$27d8,MEMF_PUBLIC	;chunky buffers 1 and 2: pea MEMF_CHIP
		PL_W	$2822,MEMF_PUBLIC	;chunky buffer 3 (double buffering)
		PL_P	$29084,cpu_fill		;blitter fill of chunky rows
		PL_END

; replaces bob:29084 (to its rts at 290e6): the blitter filled D = BLTCDAT, modulo 0,
; BLTSIZE = (D1 rol 7) + W words, i.e. D1 rows of W longwords, contiguous, from
; -7812(a4) + D0 * -7800(a4).  W = -7796(a4) is the longwords per chunky row.
; < D0.w first row, D1.w rows, D2.w fill pattern (4-bit colour in every nibble)
cpu_fill	move.l	(-7812,a4),a2
		mulu.w	(-7800,a4),d0
		add.l	d0,a2
		mulu.w	(-7796,a4),d1
		move.w	d2,d0
		swap	d0
		move.w	d2,d0
		moveq	#15,d2			;D2 is free after the pattern is in D0
		and.w	d1,d2
		lsr.w	#4,d1
		bra.b	.in16
.fill16
	REPT	16
		move.l	d0,(a2)+
	ENDR
.in16		dbf	d1,.fill16
		bra.b	.in
.fill		move.l	d0,(a2)+
.in		dbf	d2,.fill
		rts
