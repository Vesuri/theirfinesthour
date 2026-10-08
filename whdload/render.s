;*---------------------------------------------------------------------------
; CUSTOM2: render buffers in public memory (data/bob v1.1).
;
; The 3D view is drawn into packed 4-bit chunky buffers (8 pixels per longword)
; that the game allocates as MEMF_CHIP, only because the sky/ground fill at
; bob:29084 uses the blitter.  With this option they are MEMF_PUBLIC (fast RAM when
; there is any, chip otherwise) and the fill is done by the CPU.  Everything the
; display hardware reads (bitplanes, copper lists, sprites) stays in chip memory.
;
; The C2P (bob:283a0) is replaced by a merge-based one that writes the planes a
; longword at a time (c2p_merge).
;
; Ground detail 11196(a4) (Ctrl+G cycles it in flight): 0 draws the map scenery
; (bob:11138) and the ground polygons (bob:104b6, land and coastline), 1 the
; polygons only, 2 neither.  After the boot benchmark, bob:46 gave machines with
; T > 10 level 2: fast machines showed only sea.  They now get level 0; slower
; machines keep level 1.  68030/50 with CUSTOM2+3+4 at level 0: 30.9 fps, 30.6 with
; the merge C2P (another flight stretch), 50.0 with the data hunk in public memory.
;---------------------------------------------------------------------------

;---------------------------------------------------------------------------
; Also with CUSTOM2: bob's data hunk in public memory.  Its hunk header asks for
; chip memory, so every d16(a4) global was a chip access on a fast machine (99.9%
; of the CPU's chip accesses in flight with the buffers above moved).  The display
; hardware reads only 40 bytes of it: the mouse pointer sprite (data:613C, 36
; bytes) and an empty sprite (data:6160), which the copper lists point at
; (immediates at bob:28b34/28b9a and 28b4e/28bb4) and whose control words are
; written through lea -7874(a4) (bob:28ef0, 29e8e).  Copper lists, bitplanes and
; samples are separate chip allocations.  While LoadSeg runs, exec AllocMem drops
; MEMF_CHIP; the 40 bytes are then copied to chip memory and those six references
; redirected.

DATA_SPRITE	= $613c		;offset in the data hunk
DATA_SPRITES	= 40		;pointer sprite and empty sprite
DATA_EMPTY	= $24		;the empty sprite, from the pointer

; around LoadSeg: install or remove the AllocMem filter
; < A2: resload
data_fast_on	move.l	(_custom2,pc),d0
		beq.b	data_fast_rts
		lea	(data_allocmem,pc),a0
		move.l	a0,d0
		bsr.b	data_setfunc
		lea	(data_oldalloc,pc),a0
		move.l	d0,(a0)
data_fast_rts	rts
data_fast_off	move.l	(data_oldalloc,pc),d0
		beq.b	data_fast_rts
		bsr.b	data_setfunc
		lea	(data_oldalloc,pc),a0
		clr.l	(a0)
		rts
; < D0: new AllocMem; > D0: the old one
data_setfunc	movem.l	d1/a0-a1/a6,-(a7)
		move.l	(4).w,a6
		move.l	a6,a1
		move.w	#_LVOAllocMem,a0
		jsr	(_LVOSetFunction,a6)
		jsr	(resload_FlushCache,a2)	;1.3's SetFunction does not
		movem.l	(a7)+,d1/a0-a1/a6
		rts
data_allocmem	bclr	#MEMB_CHIP,d1
		move.l	(data_oldalloc,pc),-(a7)
		rts

; after LoadSeg: the sprites to chip memory
; < A2: resload, D7: seglist (BPTR)
data_sprites	movem.l	d0-d2/a0-a1/a3/a6,-(a7)
		move.l	d7,a3
		add.l	a3,a3
		add.l	a3,a3			;hunk 0's segment
		move.l	(a3),d0
		lsl.l	#2,d0
		move.l	d0,a0
		lea	(4+DATA_SPRITE,a0),a0	;the sprites in the data hunk
		move.l	a0,d2
		add.l	#4+$28b34,a3		;the copper list immediates, from bob:28b34
		cmp.l	(a3),d2
		bne.b	.done
		cmp.l	($28b9a-$28b34,a3),d2
		bne.b	.done
		moveq	#DATA_SPRITES,d0
		moveq	#MEMF_CHIP,d1
		move.l	(4).w,a6
		jsr	(_LVOAllocMem,a6)
		tst.l	d0
		beq.b	.done
		move.l	d2,a0			;AllocMem trashed A0
		move.l	d0,a1
		moveq	#DATA_SPRITES/2-1,d1
.copy		move.w	(a0)+,(a1)+
		dbf	d1,.copy
		move.l	d0,(a3)
		move.l	d0,($28b9a-$28b34,a3)
		lea	(data_spr,pc),a0
		move.l	d0,(a0)
		add.l	#DATA_EMPTY,d0
		move.l	d0,($28b4e-$28b34,a3)
		move.l	d0,($28bb4-$28b34,a3)
		jsr	(resload_FlushCache,a2)
.done		movem.l	(a7)+,d0-d2/a0-a1/a3/a6
		rts

; replaces lea -7874(a4),a0; moveq #0,d1 (sprite control words)
data_spr_lea	move.l	(data_spr,pc),d1
		beq.b	.chip
		move.l	d1,a0
		moveq	#0,d1
		rts
.chip		lea	(-7874,a4),a0		;the data hunk was not moved
		rts				;D1 is 0

data_oldalloc	dc.l	0
data_spr	dc.l	0

;---------------------------------------------------------------------------

; < A2: resload, D7: seglist (BPTR)
render_patch	move.l	(_custom2,pc),d0
		beq.b	.done
		bsr	data_sprites
		move.l	d7,d0
		lsl.l	#2,d0
		add.l	#4+$283ae,d0		;hunk 0 starts after the BPTR link
		lea	(c2p_orig,pc),a0
		move.l	d0,(a0)
		lea	(_pl_render,pc),a0
		move.l	d7,a1
		jsr	(resload_PatchSeg,a2)
.done		rts

_pl_render	PL_START
		PL_W	$27d8,MEMF_PUBLIC	;chunky buffers 1 and 2: pea MEMF_CHIP
		PL_W	$2822,MEMF_PUBLIC	;chunky buffer 3 (double buffering)
		PL_P	$29084,cpu_fill		;blitter fill of chunky rows
		PL_W	$50,0			;move.b #2,11196(a4): fast machines, level 0
		PL_P	$283a6,c2p_merge	;C2P body, after its prologue
		PL_PS	$28ef0,data_spr_lea	;lea -7874(a4),a0; moveq #0,d1
		PL_PS	$29e8e,data_spr_lea
		PL_PS	$11454,clr_scenery	;clr.w -24(a5) and the byte loop to 1148e
		PL_END

; bob:1142c (map scenery, compiled C, 9 calls per frame) cleared three 20-byte
; frame arrays a byte at a time, its counter -24(a5) reloaded on every pass: 2.3%
; of the 68020's frame.  -498(a5) and -478(a5) are adjacent; all three are even.
; The loop left -24(a5) = 20; D0 and A0 are reloaded at bob:1148e.
clr_scenery	lea	(-498,a5),a0
		moveq	#0,d0
	REPT	10
		move.l	d0,(a0)+
	ENDR
		lea	(-298,a5),a0
	REPT	5
		move.l	d0,(a0)+
	ENDR
		move.w	#20,(-24,a5)
		add.l	#$1148e-$1145a,(a7)
		rts

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

; The C2P (bob:283a0) compares the new chunky frame with the one drawn two frames
; earlier, which the back buffer's planes still show, and converts each changed
; longword (8 pixels) with 64 add/addx into a byte of each plane, merged into the
; planes in chip memory through the window mask with and.b/or.b: 16 chip accesses
; per changed longword.  This one compares and converts 4 longwords (32 pixels)
; at a time with a merge network (Kalms' technique: 5 passes of bit-group swaps
; between register pairs) and writes each plane as a longword: one chip write per
; plane, plus one read where the window mask is partial.
; Chunky longword: pixel i (0 = left) in bits 31-4i..28-4i, plane 0 the lowest bit.
; Planes are 320x200, 40 bytes a row, C2P_PLANE bytes apart (bob:28c56, 28fd8).
; Window widths that are not a multiple of 32 pixels go to the original code.

C2P_PLANE	= 8000
C2P_ROW		= 40

; swap the bits of \1 whose position has bit log2(\3) set with the bits of \2
; whose position has it clear (the mask \4 selects the clear positions); D4 trashed
C2P_MERGE	MACRO
		move.l	\1,d4
		lsr.l	#\3,d4
		eor.l	\2,d4
		and.l	#\4,d4
		eor.l	d4,\2
		lsl.l	#\3,d4
		eor.l	d4,\1
		ENDM
; the same for a shift of 16: exchange the high word of \1 with the low word of \2
C2P_MERGE16	MACRO
		swap	\1
		eor.w	\1,\2
		eor.w	\2,\1
		eor.w	\1,\2
		swap	\1
		ENDM

; replaces bob:283a6 (the body, to its rts at 284f8), after the prologue
; move.l a5,-10352(a4); movea.l sp,a5 (or CUSTOM3's c2p_wait_swap)
; < A5: 4(a5) new chunky frame, 8(a5) the frame two before
c2p_merge	movem.l	d1-a3/a6,-(a7)
		move.w	(-7796,a4),d7		;longwords per row
		moveq	#3,d0
		and.w	d7,d0
		bne.b	.orig
		move.l	(25530,a4),a0		;plane 0
		move.l	(25534,a4),d0		;plane 1
		sub.l	a0,d0
		cmp.l	#C2P_PLANE,d0
		bne.b	.orig
		adda.w	(-7808,a4),a0		;window start
		move.l	a0,d0
		lsr.w	#1,d0
		bcs.b	.orig			;odd: no longword writes on a 68000
		move.l	(-9778,a4),a1		;window mask, a byte per 8 pixels
		move.l	a1,d0
		lsr.w	#1,d0
		bcs.b	.orig
		move.l	(4,a5),a6
		move.l	(8,a5),a5
		moveq	#C2P_ROW,d0
		sub.w	d7,d0
		move.w	d0,a3			;planes: to the next row
		lsr.w	#2,d7
		subq.w	#1,d7
		move.w	d7,a2			;groups of 4 longwords per row - 1
		move.w	(-7792,a4),d7		;rows
		subq.w	#1,d7
		bmi.b	.done
.row		move.w	a2,d6
.group		movem.l	(a6)+,d0-d3
		cmp.l	(a5)+,d0
		bne.b	.diff0
		cmp.l	(a5)+,d1
		bne.b	.diff1
		cmp.l	(a5)+,d2
		bne.b	.diff2
		cmp.l	(a5)+,d3
		bne.b	.convert
		addq.l	#4,a1
.next		addq.l	#4,a0
		dbf	d6,.group
		adda.w	a3,a0
		dbf	d7,.row
.done		movem.l	(a7)+,d1-a3/a6
		movea.l	(-10352,a4),a5
		rts
.orig		movea.l	(4,a5),a6		;as bob:283aa
		move.l	(c2p_orig,pc),-(a7)
		rts

.diff0		addq.l	#4,a5
.diff1		addq.l	#4,a5
.diff2		addq.l	#4,a5
.convert	C2P_MERGE16 d3,d1
		C2P_MERGE16 d2,d0
		C2P_MERGE d3,d2,8,$00ff00ff
		C2P_MERGE d1,d0,8,$00ff00ff
		C2P_MERGE d3,d1,4,$0f0f0f0f
		C2P_MERGE d2,d0,4,$0f0f0f0f
		C2P_MERGE d3,d2,2,$33333333
		C2P_MERGE d1,d0,2,$33333333
		C2P_MERGE d3,d1,1,$55555555
		C2P_MERGE d2,d0,1,$55555555
	;planes 0-3 are now in D3, D1, D2, D0
		move.l	(a1)+,d5
		beq	.next			;all cockpit
		not.l	d5
		bne.b	.partial
		move.l	d3,(a0)
		move.l	d1,(C2P_PLANE,a0)
		move.l	d2,(2*C2P_PLANE,a0)
		move.l	d0,(3*C2P_PLANE,a0)
		bra	.next
	;D5 = the pixels to keep: plane = ((plane ^ new) & keep) ^ new
.partial	move.l	(a0),d4
		eor.l	d3,d4
		and.l	d5,d4
		eor.l	d3,d4
		move.l	d4,(a0)
		move.l	(C2P_PLANE,a0),d4
		eor.l	d1,d4
		and.l	d5,d4
		eor.l	d1,d4
		move.l	d4,(C2P_PLANE,a0)
		move.l	(2*C2P_PLANE,a0),d4
		eor.l	d2,d4
		and.l	d5,d4
		eor.l	d2,d4
		move.l	d4,(2*C2P_PLANE,a0)
		move.l	(3*C2P_PLANE,a0),d4
		eor.l	d0,d4
		and.l	d5,d4
		eor.l	d0,d4
		move.l	d4,(3*C2P_PLANE,a0)
		bra	.next

c2p_orig	dc.l	0			;bob:283ae

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
