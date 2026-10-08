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

;---------------------------------------------------------------------------
; CUSTOM3: frame pacing.  At the end of a frame (bob:12f2c) the game sets the buffer
; to show (-7964), raises the swap request (-7962 = 1) and flips the draw buffer
; without waiting; the VBL handler (bob:28d4c) loads that buffer's copper list and
; clears the request.  On a fast CPU the next frame reached the C2P, which writes the
; back buffer's bitplanes, before that VBL: it drew into the buffer on screen and
; requests were lost.  The C2P now first waits for the pending request to be taken.
; Simulation and the chunky drawing still overlap the wait.
;
; The handler writes only COP1LC, which the copper loads at the next vertical
; blank: the new buffer was shown one field after the request was cleared, and a
; C2P that started on the clear drew into the buffer on screen (tearing, and a
; mix of the new frame with an older one: the view jumped back for a field).  With
; this option the handler also strobes COPJMP1 while the beam is above the display
; window (DIWSTRT line 41), so the buffer is shown in this field.  If the handler
; runs later it leaves the request pending; the copper takes COP1LC at the next
; vertical blank and the handler clears the request then.

; < A2: resload, D7: seglist (BPTR)
pacing_patch	move.l	(_custom3,pc),d0
		beq.b	.done
		lea	(_pl_pacing,pc),a0
		move.l	d7,a1
		jsr	(resload_PatchSeg,a2)
.done		rts

_pl_pacing	PL_START
		PL_PS	$283a0,c2p_wait_swap	;move.l a5,-10352(a4); movea.l sp,a5
		PL_PS	$28d86,vbl_swap		;clr.w -7962(a4); addq.w #1,-8010(a4)
		PL_NOP	$28d8c,2
		PL_END

PACE_LASTLINE	= 36		;last line to restart the copper on (display from 41)

; in the VERTB branch of bob:28d4c, after COP1LC is set from -7964(a4); all
; registers are saved by the handler
vbl_swap	tst.w	(-7962,a4)
		beq.b	.count
		move.w	($dff004),d0		;VPOSR: bit 0 = line bit 8
		btst	#0,d0
		bne.b	.count
		move.b	($dff006),d0		;VHPOSR: line bits 7-0
		cmp.b	#PACE_LASTLINE,d0
		bhi.b	.count
		move.w	d0,($dff088)		;COPJMP1: show it now
		clr.w	(-7962,a4)
.count		addq.w	#1,(-8010,a4)
		rts

c2p_wait_swap
.wait		tst.w	(-7962,a4)
		bne.b	.wait
		move.l	a5,(-10352,a4)
		lea	(4,a7),a5			;the caller's SP, as movea.l sp,a5 saw it
		rts
