;*---------------------------------------------------------------------------
; VERIFY-only instruments for data/bob v1.1.  Never assembled into a normal build.
;
; Input tape (CUSTOM5=n, n>0): the game has no attract demo and FS-UAE playback
; cannot be used, so the slave feeds input as a physical mouse and keyboard would.
; The tape is indexed by the game's level-3 VERTB count since its handler was
; installed (tape_vbl).  Each entry holds from its field until the next entry:
;	dc.w	field
;	dc.b	dx, dy		; mouse counts added each field (JOY0DAT deltas)
;	dc.b	buttons		; bit 0 right mouse, bit 1 left mouse
;	dc.b	key		; decoded key byte (bit 7 = down) or 0 for the real CIA byte
; The tape ends with dc.w -1.  Capture with JOY0=none so nothing else moves the mouse.
;---------------------------------------------------------------------------

; < D7: seglist (BPTR), A2: resload; called after the version's own patch list
verify_patch	move.l	(_custom5,pc),d0
		beq.b	.done
		lea	(tapes,pc),a0
		subq.l	#1,d0
		cmp.l	#(tapes_end-tapes)/2,d0
		bhs.b	.done
		add.l	d0,d0
		add.w	(a0,d0.l),a0
		lea	(tape_next,pc),a1
		move.l	a0,(a1)
		lea	(_pl_tape,pc),a0
		move.l	d7,a1
		jsr	(resload_PatchSeg,a2)
.done		rts

_pl_tape	PL_START
		PL_PSS	$28dc4,tape_vertb,2	;bsr mouse deltas; move.w -4704(a4),d0
		PL_P	$29b44,tape_buttons	;menu button read (leaf)
		PL_PS	$29a96,tape_key_d0	;move.b $bfec01,d0
		PL_PS	$29ad6,tape_key_d5	;move.b $bfec01,d5
		PL_END

; replaces, inside the VERTB branch of bob:28d4c, "bsr.w $29bb2; move.w -4704(a4),d0"
tape_vertb	movem.l	d1/a0-a1,-(a7)
		move.l	(12,a7),a0			;bob+$28dca
		jsr	($29bb2-$28dca,a0)		;mouse deltas from JOY0DAT
		lea	(tape_vbl,pc),a0
		addq.w	#1,(a0)
		move.w	(a0),d1
		move.l	(tape_next,pc),a1
.next		cmp.w	(a1),d1
		blo.b	.apply
		lea	(tape_cur,pc),a0
		move.l	a1,(a0)
		addq.l	#6,a1
		lea	(tape_next,pc),a0
		move.l	a1,(a0)
		bra.b	.next
.apply		move.l	(tape_cur,pc),d1
		beq.b	.out
		move.l	d1,a1
		move.b	(2,a1),d1
		ext.w	d1
		add.w	d1,(-4704,a4)
		move.b	(3,a1),d1
		ext.w	d1
		add.w	d1,(-4702,a4)
		moveq	#3,d1
		and.b	(4,a1),d1			;bit 0 right, bit 1 left: as -8008(a4)
		or.w	d1,(-8008,a4)
.out		movem.l	(a7)+,d1/a0-a1
		move.w	(-4704,a4),d0
		rts

; replaces bob:29b44 (to its rts at 29b7c), then adds the tape's buttons
tape_buttons	clr.w	(11956,a4)
		btst	#10,$dff016
		bne.b	.1
		move.w	#1,(11956,a4)
.1		btst	#6,$bfe001
		bne.b	.2
		or.w	#2,(11956,a4)
.2		clr.w	(11950,a4)
		btst	#7,$bfe001
		bne.b	.3
		move.w	#1,(11950,a4)
.3		move.l	a0,-(a7)
		move.l	(tape_cur,pc),d0
		beq.b	.4
		move.l	d0,a0
		moveq	#3,d0
		and.b	(4,a0),d0
		or.w	d0,(11956,a4)
.4		move.l	(a7)+,a0
		rts

; the VERTB key poll reads the CIA-A serial byte and decodes it with neg.b/ror.b #1
tape_key_d0	move.b	$bfec01,d0
		move.l	a0,-(a7)
		move.l	(tape_cur,pc),a0
		cmp.w	#0,a0
		beq.b	.out
		tst.b	(5,a0)
		beq.b	.out
		move.b	(5,a0),d0
		rol.b	#1,d0
		neg.b	d0
.out		move.l	(a7)+,a0
		rts

tape_key_d5	exg	d0,d5
		bsr.b	tape_key_d0
		exg	d0,d5
		rts

tape_vbl	dc.w	0
tape_cur	dc.l	0
tape_next	dc.l	0

tapes		dc.w	tape_calibrate-tapes
		dc.w	tape_training-tapes
		dc.w	tape_bank-tapes
tapes_end

; 1: mouse calibration: from field 600, one count right and down every field
tape_calibrate	dc.w	1
		dc.b	0,0,0,0
		dc.w	600
		dc.b	1,1,0,0
		dc.w	-1

; 2: main menu (bounds set at field 2090, pointer at 160,40) -> Fly Training Flight (159,52)
; ... -> training flight 4 (bomber with escort) -> GO FLIGHT.  The flight loop starts at
; field 7603 on the 68030/50 (CUSTOM2+3+4) and 8244 on the A500-eq.
TO_FLIGHT	MACRO
		dc.w	1
		dc.b	0,0,0,0
		dc.w	2200
		dc.b	0,1,0,0
		dc.w	2212
		dc.b	-1,0,0,0
		dc.w	2213
		dc.b	0,0,0,0
		dc.w	2250
		dc.b	0,0,2,0
		dc.w	2256
		dc.b	0,0,0,0
; plane choice (up by field 4088) -> Spitfire (168,48)
		dc.w	4200
		dc.b	1,0,0,0
		dc.w	4209
		dc.b	0,-1,0,0
		dc.w	4213
		dc.b	0,0,0,0
		dc.w	4250
		dc.b	0,0,2,0
		dc.w	4256
		dc.b	0,0,0,0
; training flight choice (up by field 6288) -> 4, bomber with escort: box at (58,138)
		dc.w	6400
		dc.b	-10,10,0,0
		dc.w	6409
		dc.b	-20,0,0,0
		dc.w	6410
		dc.b	0,0,0,0
		dc.w	6450
		dc.b	0,0,2,0
		dc.w	6456
		dc.b	0,0,0,0
; briefing map (up by field 7353), the pointer is already on GO FLIGHT
		dc.w	7500
		dc.b	0,0,2,0
		dc.w	7506
		dc.b	0,0,0,0
		ENDM

tape_training	TO_FLIGHT
		dc.w	-1

; 3: tape 2, then in flight a roll to the right of about 30 degrees (roll 19198(a4) -5 500
; of 65 536): 7 mouse counts right per field for 100 fields
tape_bank	TO_FLIGHT
		dc.w	8600
		dc.b	7,0,0,0
		dc.w	8700
		dc.b	0,0,0,0
		dc.w	-1
	EVEN
