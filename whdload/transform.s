;*---------------------------------------------------------------------------
; CUSTOM2: point transform and projection (data/bob v1.1).
;
; bob:2f4ae rotates a point into view space: (D0,D1,D2) minus the camera
; (4154/4158/4162(a4), longs), each difference as sign and 32-bit magnitude,
; times 8 matrix words held as magnitudes (4114..4128) and signs (4130..4144).
; Each term is floor(magnitude * m / 65536), computed as two mulu.w halves, and
; negated where the signs differ (or, for three terms, agree).  Results:
; 4236 = x*4122 + y*4128 + z*4120, 4228 = x*4114 + y*4116,
; 4232 = x*4124 + y*4126 + z*4118 (longs).  It kept the differences, their
; signs and every partial sum in data-hunk globals: ~60 memory accesses per call,
; ~83 calls per frame (68020, level 0: 11% of the frame).  Every other user of
; those globals (4246..4262) writes them before reading, so this version keeps
; them in registers, with the same arithmetic and therefore the same results.
; On a 68020 or better each term is one mulu.l (the 64-bit product's bits 16-47
; equal the two halves' sum, which cannot carry out of 32 bits).
; Out: as the original, D0-D2 are trashed.
;
; bob:2f160 projects a view-space point; with 4290(a4) set it takes the 32-bit
; path at bob:2f28a: from the magnitudes 4282/4286 (signs: the high words
; 4316/4318) it forms 4268 = X*m4148 + Y*m4146 + -7802 and
; 4272 = (X*m4146 + Y*m4148) * $e8ba - 4312 + -7788, each product
; floor((magnitude * m + $8000) / 65536) from two mulu.w, in globals: 5.1% of the
; 68020's frame.  This version keeps them in registers; on a 68020 each product
; is one mulu.l (the rounding add is carried into the high long).  Its callers
; (bob:2f134, 30246, 30478) use only D0 before restoring D1-A3/A6, so only D0
; (4282's high word, low word 0) is reproduced.
;
; bob:2f374 (called by bob:2f160) divides D0.w by 4244(a4) as two divu.w (32-bit
; quotient q) and scales it: floor((q * 4264(a4) + $8000) / 65536), negated with
; D0.w.  On a 68020 it is one divu.l and one mulu.l (3.8% of the frame).  Its
; caller uses D0 and D2 (the magnitude).
;
; bob:3041c, the C entry of the projection (x, y, z longs on the stack; ~27
; calls per frame, most from the map scenery bob:1142c): x and y as magnitudes,
; their values in 8860/8856, all three shifted right together until x | y | z
; fits in 15 bits, x and y given their signs back, into the words 4240/4242/4244,
; then bob:2f160.  It shifted one bit per pass (~12 passes) and saved D1-A3/A6:
; 5.4% of the 68020's frame.  This version shifts once by the count the passes
; reach (bfffo on a 68020) and saves D1-D7 (the registers bob:2f160 and its
; callees use) and A0.  As the original it sets -10352(a4) to A5 and returns D0.
;---------------------------------------------------------------------------

; < A2: resload, D7: seglist (BPTR)
xform_patch	move.l	(_custom2,pc),d0
		beq.b	.done
		move.l	d7,d0
		lsl.l	#2,d0
		add.l	#4+$2f160,d0		;hunk 0 starts after the BPTR link
		lea	(xp_2f160,pc),a0
		move.l	d0,(a0)
		lea	(_pl_xform,pc),a0
		move.l	(4).w,a1
		btst	#AFB_68020,(AttnFlags+1,a1)
		beq.b	.patch
		lea	(_pl_xform20,pc),a0
.patch		move.l	d7,a1
		jsr	(resload_PatchSeg,a2)
.done		rts

_pl_xform	PL_START
		PL_P	$2f4ae,xform
		PL_P	$2f28a,xproj
		PL_P	$3041c,xpnorm
		PL_END

_pl_xform20	PL_START
		PL_P	$2f4ae,xform20
		PL_P	$2f28a,xproj20
		PL_P	$2f374,xdiv20
		PL_P	$3041c,xpnorm20
		PL_END

; < D0/D1/D2 point; > 4236/4228/4232(a4).  D5-D7: the differences' signs (0 or
; $8000, as the original's 4258/4260/4262), A0: the sum.
XF_DIFF	MACRO	;point register, camera offset, sign register
		moveq	#0,\3
		sub.l	(\2,a4),\1
		bpl.b	.p\@
		neg.l	\1
		move.w	#$8000,\3
.p\@
	ENDM

; magnitude register, matrix word, sign register, matrix sign, bcc that skips
; the negation, movea.l (first term) or adda.l
XF_TERM	MACRO
		move.w	\1,d3
		mulu.w	(\2,a4),d3
		clr.w	d3
		swap	d3
		move.l	\1,d4
		swap	d4
		mulu.w	(\2,a4),d4
		add.l	d3,d4
		move.w	(\4,a4),d3
		eor.w	\3,d3
		\5.b	.n\@
		neg.l	d4
.n\@		\6	d4,a0
	ENDM

	MACHINE	68020
XF_TERM20	MACRO
		moveq	#0,d3
		move.w	(\2,a4),d3
		mulu.l	\1,d4:d3
		swap	d3
		swap	d4
		move.w	d3,d4
		move.w	(\4,a4),d3
		eor.w	\3,d3
		\5.b	.n\@
		neg.l	d4
.n\@		\6	d4,a0
	ENDM
	MACHINE	68000

XF_BODY	MACRO	;term macro
		movem.l	d3-d7/a0,-(a7)
		XF_DIFF	d0,4154,d5
		XF_DIFF	d1,4158,d6
		XF_DIFF	d2,4162,d7
		\1	d0,4122,d5,4138,beq,movea.l
		\1	d1,4128,d6,4144,beq,adda.l
		\1	d2,4120,d7,4136,beq,adda.l
		move.l	a0,(4236,a4)
		\1	d0,4114,d5,4130,beq,movea.l
		\1	d1,4116,d6,4132,bne,adda.l
		move.l	a0,(4228,a4)
		\1	d0,4124,d5,4140,bne,movea.l
		\1	d1,4126,d6,4142,bne,adda.l
		\1	d2,4118,d7,4134,beq,adda.l
		move.l	a0,(4232,a4)
		movem.l	(a7)+,d3-d7/a0
		rts
	ENDM

xform		XF_BODY	XF_TERM

	MACHINE	68020
xform20		XF_BODY	XF_TERM20
	MACHINE	68000

; magnitude register, multiplier operand; > D2 = floor((mag * m + $8000) / 65536)
; (D3 trashed)
XP_MUL	MACRO
		move.w	\1,d2
		mulu.w	\2,d2
		add.l	#$8000,d2
		clr.w	d2
		swap	d2
		move.l	\1,d3
		swap	d3
		mulu.w	\2,d3
		add.l	d3,d2
	ENDM

	MACHINE	68020
XP_MUL20	MACRO
		moveq	#0,d3
		move.w	\2,d3
		mulu.l	\1,d2:d3
		add.l	#$8000,d3
		bcc.b	.c\@
		addq.l	#1,d2
.c\@		swap	d3
		swap	d2
		move.w	d3,d2
	ENDM
	MACHINE	68000

; product macro, magnitude, matrix word, sign register, matrix sign, bcc that
; skips the negation; > D2
XP_TERM	MACRO
		\1	\2,(\3,a4)
		move.w	(\5,a4),d3
		eor.w	\4,d3
		\6.b	.n\@
		neg.l	d2
.n\@
	ENDM

; replaces bob:2f28a to its rts at 2f372.  D0/D1: X/Y magnitudes, D6/D7: their
; signs (bit 15), D5: the sum
XP_BODY	MACRO	;product macro
		move.l	(4282,a4),d0
		move.l	(4286,a4),d1
		move.w	(4316,a4),d6
		move.w	(4318,a4),d7
		XP_TERM	\1,d0,4148,d6,4152,bpl
		move.l	d2,d5
		XP_TERM	\1,d1,4146,d7,4150,bmi
		add.l	d2,d5
		moveq	#0,d4
		move.w	(-7802,a4),d4
		add.l	d4,d5
		move.l	d5,(4268,a4)
		XP_TERM	\1,d0,4146,d6,4150,bpl
		move.l	d2,d5
		XP_TERM	\1,d1,4148,d7,4152,bpl
		add.l	d2,d5
		move.l	d5,d1
		bpl.b	.abs
		neg.l	d1
.abs		\1	d1,#$e8ba
		tst.l	d5
		bpl.b	.pos
		neg.l	d2
.pos		sub.l	(4312,a4),d2
		moveq	#0,d4
		move.w	(-7788,a4),d4
		add.l	d4,d2
		move.l	d2,(4272,a4)
		clr.w	d0
		rts
	ENDM

xproj		XP_BODY	XP_MUL

	MACHINE	68020
xproj20		XP_BODY	XP_MUL20
	MACHINE	68000

; replaces bob:3041c to its rts at 30484.  D3: x | y | z, then the shift count
XP_NORM	MACRO	;shift count macro
		move.l	a5,(-10352,a4)
		movem.l	d1-d7/a0,-(a7)
		movem.l	(36,a7),d0-d2
		move.l	d0,(8860,a4)
		bpl.b	.x
		neg.l	d0
.x		move.l	d1,(8856,a4)
		bpl.b	.y
		neg.l	d1
.y		move.l	d0,d3
		or.l	d1,d3
		or.l	d2,d3
		\1
		lsr.l	d3,d0
		lsr.l	d3,d1
		lsr.l	d3,d2
.s		tst.l	(8860,a4)
		bpl.b	.sx
		neg.w	d0
.sx		tst.l	(8856,a4)
		bpl.b	.sy
		neg.w	d1
.sy		move.w	d0,(4240,a4)
		move.w	d1,(4242,a4)
		move.w	d2,(4244,a4)
		move.l	(xp_2f160,pc),a0
		jsr	(a0)
		movem.l	(a7)+,d1-d7/a0
		rts
	ENDM

; > D3 = the passes' count: 0 below $8000 (to .s), else 8 at a time while above
; $7fffff, then one at a time
XP_COUNT	MACRO
		moveq	#0,d4
		cmp.l	#$7fffff,d3
		bls.b	.b
		lsr.l	#8,d3
		addq.w	#8,d4
		cmp.l	#$7fffff,d3
		bls.b	.b
		lsr.l	#8,d3
		addq.w	#8,d4
.b		cmp.l	#$7fff,d3
		bls.b	.c
		lsr.l	#1,d3
		addq.w	#1,d4
		bra.b	.b
.c		move.l	d4,d3
		beq.b	.s
	ENDM

; the same from the highest set bit: 17 - its bfffo offset
XP_COUNT20	MACRO
		bfffo	d3{0:32},d4
		moveq	#17,d3
		sub.l	d4,d3
		ble.b	.s
	ENDM

xpnorm		XP_NORM	XP_COUNT

	MACHINE	68020
xpnorm20	XP_NORM	XP_COUNT20
	MACHINE	68000

xp_2f160	dc.l	0			;bob:2f160

	MACHINE	68020

; replaces bob:2f374.  < D0.w; > D0 (signed), D2 (magnitude), D1.w = D0.w in
xdiv20		move.w	d0,d1
		bpl.b	.p
		neg.w	d0
.p		andi.l	#$ffff,d0
		swap	d0			;the dividend: |D0.w| << 16
		moveq	#0,d2
		move.w	(4244,a4),d2
		beq.b	.m			;no divisor: the original's q is the same
		divu.l	d2,d0			;q fits: |D0.w| / divisor < 65536
.m		move.l	d3,-(a7)
		moveq	#0,d3
		move.w	(4264,a4),d3
		mulu.l	d0,d2:d3
		add.l	#$8000,d3
		bcc.b	.c
		addq.l	#1,d2
.c		swap	d3
		swap	d2
		move.w	d3,d2
		move.l	(a7)+,d3
		move.l	d2,d0
		tst.w	d1
		bpl.b	.r
		neg.l	d0
.r		rts
	MACHINE	68000
