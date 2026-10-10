;*---------------------------------------------------------------------------
; CUSTOM4: real-time simulation (data/bob v1.1).
;
; Each pass of the flight loop (bob:1294e) is one simulation step of 1/T seconds,
; with T = 11698(a4) from a rendering benchmark at boot.  Game speed was therefore
; fps/T: right only at the frame rate the benchmark predicted.  With this option T
; is set every frame from the fields the previous frame took (-8010(a4), the
; game's VERTB count): T = fields per second / fields, as an integer whose
; rounding error is carried to the next frame, so game time follows real time.
; T stays within 4 (the benchmark's minimum) and the field rate (one frame per
; field).  A frame of more than DT_STALL fields (a pause or a disk load) advances
; no extra time.  Above one frame per field, i.e. without CUSTOM3, the game runs
; faster than real time.
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
;
; At large T the per-step increments are small and the game truncated each one
; (at T = 50 ground speed 1.3% low, a 30-degree bank turning 3% slow).  Each
; object's step and the player's roll, turn and pitch rates are computed in
; 16.16 here, with their fractions carried to the next step (dt_steplen,
; dt_polar, dt_roll, dt_turn).
;
; The field rate is measured at boot from the beam's line count (PAL 313, NTSC
; 263), so T follows real time on NTSC machines too, with up to one frame per
; field (T 60).  The boot benchmark (T = 380 / fields, bob:2c24) is left as it
; is: its T is used outside flight too (scaling it changed the menus), so on NTSC
; the boot T and the detail level chosen from it are as in the original there.
; Still counted in fields (shorter at 60 Hz, as in the original on NTSC): the
; joystick's deflection ramp (bob:29c00), sound envelopes and fixed waits.
;---------------------------------------------------------------------------

DT_HZ		= 50		;PAL fields per second
DT_HZ_NTSC	= 60
DT_LINES	= 288		;highest line of a field: PAL 312, NTSC 262
DT_ONE		= 256		;fixed point: units per field
DT_TMIN		= 4		;divided by with lsr #2; T at most dt_hz (one frame per field)
DT_STALL	= 25		;fields
DT_STICK_T	= 8
DT_WRAP		= 64		;mouse counts per field
DT_PLANES	= 16		;per-plane arrays of the flight model (32 bytes)

; < A2: resload, D7: seglist (BPTR)
timing_patch	move.l	(_custom4,pc),d0
		beq.b	.done
		bsr	dt_rate
		lea	(dt_hz,pc),a0
		move.w	d0,(a0)
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
		PL_PS	$154dc,dt_steplen	;jsr -31938(a4); addq.w #4,sp
		PL_PS	$15576,dt_polar		;jsr -31746(a4); addq.w #6,sp
		PL_PS	$157a0,dt_polar
		PL_PS	$15800,dt_polar
		PL_PS	$158b2,dt_polar
		PL_PS	$15ac6,dt_polar
		PL_PS	$1448a,dt_roll		;moveq #0,d0; move.w 13318(a4),d0
		PL_PS	$144ee,dt_turn		;moveq #0,d0; move.w 13318(a4),d0
		PL_END

; > D0.w: fields per second, from the highest beam line of a field
dt_rate		movem.l	d1-d3,-(a7)
		bsr.b	.line
.sync		move.w	d0,d1			;wait for the beam to wrap to line 0
		bsr.b	.line
		cmp.w	d1,d0
		bhs.b	.sync
		moveq	#0,d2
.field		cmp.w	d2,d0
		bls.b	.next
		move.w	d0,d2
.next		move.w	d0,d1
		bsr.b	.line
		cmp.w	d1,d0
		bhs.b	.field			;until it wraps again
		moveq	#DT_HZ,d0
		cmp.w	#DT_LINES,d2
		bhs.b	.done
		moveq	#DT_HZ_NTSC,d0
.done		movem.l	(a7)+,d1-d3
		rts
; > D0.w: the beam's line; VPOSR (line bit 8) and VHPOSR are read again until
; both reads agree, so a read across line 255/256 is not taken as a wrap
.line		move.l	($dff004),d0
		lsr.l	#8,d0
		and.w	#$1ff,d0
		move.l	($dff004),d3
		lsr.l	#8,d3
		and.w	#$1ff,d3
		cmp.w	d0,d3
		bne.b	.line
		rts

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
		moveq	#0,d0
		move.w	(dt_hz,pc),d0
		lsl.w	#8,d0			;a second: dt_hz*DT_ONE
		move.w	d0,d3
		lsr.w	#2,d3			;/DT_TMIN
		cmp.w	d3,d1
		ble.b	.owed
		move.w	d3,d1
.owed		move.w	(dt_hz,pc),d2		;T at most dt_hz: a field's time
		cmp.w	#DT_ONE,d1
		blt.b	.step
		move.w	d1,d3			;T = round(dt_hz*DT_ONE / owed)
		lsr.w	#1,d3
		ext.l	d3
		add.l	d0,d3
		divu.w	d1,d3
		move.w	d3,d2
.step		move.l	d0,d3			;the step's length
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

; bob:154dc, object D4's step length in the object loop (bob:154ba): as the
; helper bob:29188, round(round(speed*4660/256) / divisor), and also the exact
; length in 16.16 for dt_polar.  Like the helper, only D0-D2 change.
dt_steplen	move.l	a0,-(a7)
		lea	(dt_len,pc),a0
		clr.w	(a0)			;no exact length unless it fits
		moveq	#0,d0
		move.w	(8,a7),d0		;speed
		move.w	(10,a7),d2		;divisor (11700)
		mulu.w	#4660,d0
		add.l	#128,d0
		lsr.l	#8,d0
		move.l	d0,d1
		swap	d1
		cmp.w	d2,d1
		bhs.b	.round			;quotient over 16 bits: as the helper
		move.l	d0,-(a7)
		divu.w	d2,d0			;remainder : integer part
		cmp.w	#$7fff,d0
		bhs.b	.big
		move.w	d0,(2,a0)		;integer part
		clr.w	d0
		divu.w	d2,d0			;remainder << 16 / divisor
		move.w	d0,(4,a0)		;fraction
		move.w	d4,(8,a0)		;object
		st	(a0)
.big		move.l	(a7)+,d0
.round		move.w	d0,d1
		lsr.w	#1,d1			;half the dividend, for rounding
		divu.w	d2,d0			;as bob:29188
		move.l	d0,d2
		swap	d2
		cmp.w	d1,d2
		blo.b	.q
		addq.l	#1,d0
.q		move.w	d0,(6,a0)		;the length the game uses
		move.l	(a7)+,a0
		move.l	(a7),(4,a7)		;return over the two arguments
		addq.l	#4,a7
		rts

; bob:15576, 157a0, 15800, 158b2, 15ac6: the object loop's velocity from the
; step length, heading and pitch (bob:2eb4a sets 4204/4208/4212(a4) to x, y, z
; per step, each truncated).  With the exact length of this object's step the
; components come in 16.16 from bob:2e9c0, and each object's fractions carry to
; its next step.  Like bob:2eb4a, only D0 changes.
dt_polar	movem.l	d1-d3/a0-a1/a6,-(a7)
		lea	(dt_len,pc),a0
		tst.w	(a0)
		beq.b	.orig
		move.w	(28,a7),d0		;length pushed
		cmp.w	(6,a0),d0
		bne.b	.orig
		cmp.w	(8,a0),d4
		bne.b	.orig
		move.w	(2,a0),(4094,a4)	;length 16.16
		move.w	(4,a0),(4096,a4)
		move.w	(30,a7),d0		;heading, as bob:2eb5e
		sub.w	#16384,d0
		neg.w	d0
		move.w	d0,(4098,a4)
		move.w	(32,a7),(4100,a4)	;pitch
		move.l	(-31744,a4),a0		;bob:2eb4a, from the jump table
		lea	(-$2eb4a+$2e9c0,a0),a0
		jsr	(a0)
		lea	(dt_frac,pc),a0
		move.w	d4,d0
		mulu.w	#6,d0
		add.w	d0,a0
		lea	(4102,a4),a1
		lea	(4204,a4),a6
		moveq	#3-1,d3
.axis		move.l	(a1)+,d0		;16.16, signed
		moveq	#0,d1
		move.w	(a0),d1
		add.l	d1,d0
		move.w	d0,(a0)+		;fraction carried
		swap	d0
		ext.l	d0			;floor
		move.l	d0,(a6)+
		dbf	d3,.axis
		movem.l	(a7)+,d1-d3/a0-a1/a6
		bra.b	.ret
.orig		movem.l	(a7)+,d1-d3/a0-a1/a6
		move.w	(8,a7),-(a7)		;pitch, heading, length again
		move.w	(8,a7),-(a7)
		move.w	(8,a7),-(a7)
		jsr	(-31746,a4)
		addq.l	#6,a7
.ret		move.l	(a7),(6,a7)		;return over the three arguments
		addq.l	#6,a7
		rts

; The flight model (bob:13c6e) for plane P = 13318(a4) turns the stick input
; into per-step rates, divided by T: the roll rate 30676 = 19230[P] * |roll
; stick 11968| / T, and from the pitch stick 11970, v = 19134[P] * |11970| / T,
; the heading rate 30680 = v * sin(roll) / 4 and the pitch rate 30682 = v *
; cos(roll).  The game truncates after each division and product, which at large
; T loses most of a small rate: a shallow bank does not turn.  Here each rate is
; computed exactly in 16.16 and its fraction carries to the plane's next step.

; bob:1448a: 30676, the roll rate's magnitude (bob:144a8 applies the sign)
dt_roll		movem.l	d1-d2/a0,-(a7)
		move.w	(11968,a4),d0
		bsr	dt_abs
		lea	(19230,a4),a0
		move.w	(a0,d1.w),d2
		bsr	dt_rate16
		moveq	#0,d1			;slot 0: roll
		bsr	dt_carry
		move.w	d0,(30676,a4)
		movem.l	(a7)+,d1-d2/a0
		add.l	#$144a8-$14490,(a7)
		rts

; bob:144ee: 30680 and 30682 from 30678 (set by the game) and the roll angle
dt_turn		movem.l	d1-d4/a0,-(a7)
		move.w	(11970,a4),d0
		bsr	dt_abs
		lea	(19134,a4),a0
		move.w	(a0,d1.w),d2
		bsr	dt_rate16		;v, 16.16
		move.l	d0,d4
		lea	(19198,a4),a0
		move.w	(a0,d1.w),d3		;roll
		move.w	d3,d2
		bsr	dt_sin			;v * sin(roll), 16.16
		asr.l	#2,d0
		moveq	#2,d1			;slot 1: heading
		bsr	dt_carry
		move.w	d0,(30680,a4)
		move.l	d4,d0
		move.w	d3,d2
		add.w	#16384,d2
		bsr	dt_sin			;v * cos(roll)
		moveq	#4,d1			;slot 2: pitch
		bsr	dt_carry
		move.w	d0,(30682,a4)
		movem.l	(a7)+,d1-d4/a0
		add.l	#$1452c-$144f4,(a7)
		rts

; < D0.w stick; > D0.l |stick|, D1.l P*2
dt_abs		bpl.b	.pos
		neg.w	d0
.pos		and.l	#$ffff,d0
		moveq	#0,d1
		move.w	(13318,a4),d1
		add.w	d1,d1
		rts

; < D0.l |stick|, D2.w factor; > D0.l factor*|stick|/T in 16.16 (factor*|stick|
; is the result << 16, as the game's mulu/swap helper bob:29110)
dt_rate16	movem.l	d1-d3,-(a7)
		mulu.w	d2,d0
		move.w	(11698,a4),d2
		move.l	d0,d1
		clr.w	d1
		swap	d1
		divu.w	d2,d1			;remainder : quotient of the high word
		move.l	d1,d3
		move.w	d0,d1
		divu.w	d2,d1			;quotient of (remainder << 16) | low word
		swap	d3
		move.w	d1,d3
		move.l	d3,d0
		movem.l	(a7)+,d1-d3
		rts

; < D0.l v (16.16, >= 0), D2.w angle; > D0.l v * sin(angle) in 16.16, from the
; game's table at 4420(a4) (magnitudes, sign from angle bit 15) as bob:2e94c
dt_sin		movem.l	d1-d3/a0,-(a7)
		move.w	d2,d3
		lea	(4420,a4),a0
		lsr.w	#5,d2
		and.w	#-2,d2
		move.w	(a0,d2.w),d2
		move.l	d0,d1
		swap	d1
		mulu.w	d2,d1			;high word * sin
		mulu.w	d2,d0			;low word * sin
		clr.w	d0
		swap	d0
		add.l	d1,d0
		tst.w	d3
		bpl.b	.pos
		neg.l	d0
.pos		movem.l	(a7)+,d1-d3/a0
		rts

; < D0.l rate in 16.16, D1.w slot*2; > D0.w the rate with plane P's fraction
; of that slot carried (planes beyond DT_PLANES: truncated as the game)
dt_carry	movem.l	d1-d2/a0,-(a7)
		move.w	(13318,a4),d2
		cmp.w	#DT_PLANES,d2
		bhs.b	.floor
		mulu.w	#6,d2
		add.w	d1,d2
		lea	(dt_rfrac,pc),a0
		add.w	d2,a0
		moveq	#0,d1
		move.w	(a0),d1
		add.l	d1,d0
		move.w	d0,(a0)
.floor		swap	d0
		movem.l	(a7)+,d1-d2/a0
		rts

dt_mdx		dc.w	0
dt_mdy		dc.w	0
dt_boot		dc.w	0
dt_last		dc.w	0
dt_live		dc.w	0
dt_err		dc.w	0
dt_hz		dc.w	DT_HZ			;fields per second, measured at boot
dt_len		dc.w	0,0,0,0,0		;valid, integer, fraction, rounded, object
dt_rfrac	dcb.w	DT_PLANES*3,0		;roll, heading, pitch rate fractions per plane
dt_frac		dcb.w	152*3,0			;x, y, z fractions per object (bob:154ba)
