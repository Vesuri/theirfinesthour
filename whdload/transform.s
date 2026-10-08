;*---------------------------------------------------------------------------
; CUSTOM2: point transform (data/bob v1.1).
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
;---------------------------------------------------------------------------

; < A2: resload, D7: seglist (BPTR)
xform_patch	move.l	(_custom2,pc),d0
		beq.b	.done
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
		PL_END

_pl_xform20	PL_START
		PL_P	$2f4ae,xform20
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
