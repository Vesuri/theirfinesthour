;*---------------------------------------------------------------------------
; CUSTOM4: real-time simulation (data/bob v1.1).
;
; Each pass of the flight loop (bob:1294e) is one simulation step of 1/T seconds,
; with T = 11698(a4) from a rendering benchmark at boot.  Game speed was therefore
; fps/T: right only at the frame rate the benchmark predicted.  With this option T
; is set every frame from the PAL fields the previous frame took (-8010(a4), the
; game's VERTB count): T = 50 / fields, as an integer whose rounding error is
; carried to the next frame, so game time follows real time.  T stays within
; 4..50 (the benchmark's minimum; one frame per field).  A frame of more than
; DT_STALL fields (a pause or a disk load) advances no extra time.  Above 50 fps,
; i.e. without CUSTOM3, the game runs faster than real time.
;
; Derived values follow T: 11700 (the step divisor; T/3, minimum 2, while the T
; key accelerates time) and 11702 = 11700/8+1.  Countdowns the game sets as
; multiples of T are set from the T of the moment.  The boot T is restored at
; each flight's start (bob:ad66); the detail level chosen from it at boot stays.
;
; Mouse and joystick counts are summed per field by the VERTB handler, so a
; frame's input grows with the frame's duration, and the stick code then divides
; it by T again.  They are scaled by T/DT_STICK_T, which makes stick response
; independent of the frame rate and equal to the original's at T = DT_STICK_T
; (about the A500's frame rate).  The keyboard sets the deflection directly and
; needs no scaling.
;
; The VERTB handler reads the mouse as the change of JOY0DAT's 8-bit counters
; since the last field (bob:29bb2), so more than 127 counts in a field read as a
; move the other way.  Host mice under emulation reach that when moved fast; at
; 50 fps one such field is a whole frame, and the plane rolls back for a frame.
; A reading of DT_WRAP counts or more against an equally large previous one of
; the other sign is taken as wrapped (a real reversal slows down through small
; readings first).
;---------------------------------------------------------------------------

DT_HZ		= 50		;PAL fields per second
DT_ONE		= 256		;fixed point: units per field
DT_TMIN		= 4
DT_TMAX		= 50
DT_STALL	= 25		;fields
DT_STICK_T	= 8
DT_WRAP		= 64		;mouse counts per field

; < A2: resload, D7: seglist (BPTR)
timing_patch	move.l	(_custom4,pc),d0
		beq.b	.done
		lea	(_pl_timing,pc),a0
		move.l	d7,a1
		jsr	(resload_PatchSeg,a2)
.done		rts

_pl_timing	PL_START
		PL_PS	$19e,dt_stick		;clr.w -4696(a4); clr.w -4694(a4)
		PL_NOP	$1a4,2
		PL_PS	$ad6e,dt_flight		;move.w 11698(a4),11700(a4)
		PL_PS	$12954,dt_loop		;clr.w 30652(a4); move.w #1,-(sp)
		PL_NOP	$1295a,2
		PL_P	$29bb2,dt_mouse		;mouse deltas, to its rts at 29bfe
		PL_END

; flight initialisation: back to the boot T, new frame timing
dt_flight	move.l	a0,-(a7)
		lea	(dt_boot,pc),a0
		tst.w	(a0)
		bne.b	.restore
		move.w	(11698,a4),(a0)
.restore	move.w	(a0),(11698,a4)
		lea	(dt_live,pc),a0
		clr.w	(a0)
		move.l	(a7)+,a0
		move.w	(11698,a4),(11700,a4)
		rts

; top of the flight loop, once per frame
dt_loop		clr.w	(30652,a4)
		movem.l	d0-d3/a0,-(a7)
		bsr.b	dt_frame
		movem.l	(a7)+,d0-d3/a0
		move.l	(a7)+,a0		;bob+$1295a (the NOP)
		move.w	#1,-(a7)
		jmp	(a0)

dt_frame	move.w	(-8010,a4),d0
		lea	(dt_last,pc),a0
		move.w	(a0),d1
		move.w	d0,(a0)
		lea	(dt_live,pc),a0
		tst.w	(a0)
		bne.b	.live
		st	(a0)			;first frame of a flight: keep T
		lea	(dt_err,pc),a0
		clr.w	(a0)
		rts
.live		neg.w	d1
		add.w	d0,d1			;fields since the last frame
		bpl.b	.fields
		move.w	d0,d1			;the game cleared its count meanwhile
.fields		cmp.w	#DT_STALL,d1
		bls.b	.time
		lea	(dt_err,pc),a0		;stall: no time owed, T unchanged
		clr.w	(a0)
		rts
.time		lsl.w	#8,d1			;*DT_ONE
		lea	(dt_err,pc),a0
		add.w	(a0),d1			;time owed, fields*DT_ONE
		cmp.w	#DT_HZ*DT_ONE/DT_TMIN,d1
		ble.b	.owed
		move.w	#DT_HZ*DT_ONE/DT_TMIN,d1
.owed		moveq	#DT_TMAX,d2
		cmp.w	#DT_HZ*DT_ONE/DT_TMAX,d1
		blt.b	.step
		move.w	d1,d3			;T = round(DT_HZ*DT_ONE / owed)
		lsr.w	#1,d3
		ext.l	d3
		add.l	#DT_HZ*DT_ONE,d3
		divu.w	d1,d3
		move.w	d3,d2
.step		move.l	#DT_HZ*DT_ONE,d3	;the step's length
		divu.w	d2,d3
		sub.w	d3,d1
		cmp.w	#-DT_ONE,d1		;never more than a field ahead
		bge.b	.err
		move.w	#-DT_ONE,d1
.err		move.w	d1,(a0)
	;T and the values derived from it
		move.w	(11698,a4),d0		;the T the step divisor was set from
		move.w	d2,(11698,a4)
		cmp.w	(11700,a4),d0
		beq.b	.normal
		moveq	#0,d3			;time acceleration (bob:13d1e)
		move.w	d2,d3
		divu.w	#3,d3
		cmp.w	#2,d3
		bhs.b	.accel
		moveq	#2,d3
.accel		move.w	d3,d2
.normal		move.w	d2,(11700,a4)
		lsr.w	#3,d2			;as bob:ad74
		addq.w	#1,d2
		move.w	d2,(11702,a4)
		rts

; end of bob:112, after the mouse (11968/11970 = counts << 6/5) or the joystick
; (<< 4/3) has set the stick input for this frame; the keys set it later, if zero
dt_stick	clr.w	(-4696,a4)
		clr.w	(-4694,a4)
		move.l	d1,-(a7)
		move.w	(11968,a4),d0
		bsr.b	.scale
		move.w	d0,(11968,a4)
		move.w	(11970,a4),d0
		bsr.b	.scale
		move.w	d0,(11970,a4)
		move.l	(a7)+,d1
		rts
.scale		muls.w	(11698,a4),d0
		asr.l	#3,d0			;/DT_STICK_T
		move.l	#32767,d1
		cmp.l	d1,d0
		ble.b	.lo
		move.l	d1,d0
.lo		neg.l	d1
		cmp.l	d1,d0
		bge.b	.ok
		move.l	d1,d0
.ok		rts

; replaces bob:29bb2: -4704/-4702(a4) = this field's mouse x/y counts, from
; JOY0DAT against the last field's counters in -4708/-4706(a4) (bytes)
dt_mouse	move.b	($dff00b),d4
		lea	(-4708,a4),a0
		lea	(dt_mdx,pc),a1
		bsr.b	.axis
		move.w	d5,(-4704,a4)
		move.b	($dff00a),d4
		lea	(-4706,a4),a0
		lea	(dt_mdy,pc),a1
		bsr.b	.axis
		move.w	d5,(-4702,a4)
		rts
; < D4.b counter now, A0 last counter, A1 last delta; > D5.w delta
.axis		move.b	d4,d5
		sub.b	(a0),d5
		move.b	d4,(a0)
		ext.w	d5
		move.w	(a1),d4
		cmp.w	#DT_WRAP,d5
		blt.b	.neg
		cmp.w	#-DT_WRAP,d4		;large +, last large -: wrapped
		bgt.b	.keep
		sub.w	#256,d5
		bra.b	.keep
.neg		cmp.w	#-DT_WRAP,d5
		bgt.b	.keep
		cmp.w	#DT_WRAP,d4		;large -, last large +: wrapped
		blt.b	.keep
		add.w	#256,d5
.keep		move.w	d5,(a1)
		rts

dt_mdx		dc.w	0
dt_mdy		dc.w	0
dt_boot		dc.w	0
dt_last		dc.w	0
dt_live		dc.w	0
dt_err		dc.w	0
