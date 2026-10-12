;*---------------------------------------------------------------------------
; Enhanced framerate (CUSTOM2=1 only): real-time simulation (data/bob v1.1).
;
; Each pass of the flight loop (bob:1294e) is one simulation step of 1/T seconds,
; with T = 11698(a4) from a rendering benchmark at boot.  Game speed was therefore
; fps/T: right only at the frame rate the benchmark predicted.  Here T is set
; every frame from the frame's average length in fields (-8010(a4), the game's
; VERTB count; it moves 1/8 of the way to each frame's length): T = fields per
; second / average, as an integer.  The time owed (frames' lengths less the
; steps taken) is carried, and a quarter of it is added to the next step aimed
; at, so game time follows real time.  The game counts many intervals in frames,
; set as multiples of T (a gun's reload T/3, a bullet's life 2T): T from one
; frame's length would alternate with frames of 1 and 2 fields (2 and 3 on the
; 68020), and those intervals would take half or twice their time.
; T stays within 4 (the benchmark's minimum) and the field rate (one frame per
; field).  A frame of more than DT_STALL fields (a pause or a disk load) advances
; no extra time.  Above one frame per field the game would run faster than real
; time; frame pacing keeps it to one.
;
; Derived values follow T: 11700 (the step divisor; T/3, minimum 2, while the T
; key accelerates time) and 11702 = 11700/8+1.  The boot T is restored at
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
; object's step, the player's roll, turn and pitch rates and the AI planes' turn
; are computed in 16.16 here, with their fractions carried to the next step
; (dt_steplen, dt_polar, dt_roll, dt_turn, dt_aiadd, dt_aisub).
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
DT_AVG		= 3		;the average frame moves 1/8 of the way per frame
DT_STICK_T	= 8
DT_WRAP		= 64		;mouse counts per field
DT_PLANES	= 16		;per-plane arrays of the flight model (32 bytes)

; < A2: resload, D7: seglist (BPTR)
timing_patch	move.l	(_improve,pc),d0
		beq.b	.done
		move.l	(_custom3,pc),d0
		cmp.l	#3,d0
		bls.b	.mouse_option
		moveq	#0,d0
.mouse_option	tst.w	d0
		bne.b	.nondefault
		moveq	#1,d0
		bra.b	.mouse_shift
.nondefault	cmp.w	#1,d0
		bne.b	.mouse_shift
		moveq	#0,d0
.mouse_shift	lea	(dt_mouse_shift,pc),a0
		move.w	d0,(a0)
		bsr	dt_rate
		lea	(dt_hz,pc),a0
		move.w	d0,(a0)
		lea	(_pl_timing,pc),a0
		move.l	d7,a1
		jsr	(resload_PatchSeg,a2)
.done		rts

_pl_timing	PL_START
		PL_PS	$1467a,dt_ground_steer
		PL_NOP	$14680,2
		PL_PS	$149b0,dt_recovery
		PL_NOP	$149b6,2
		PL_PS	$20d18,dt_att_fall_limit
		PL_PS	$20e40,dt_att_fall_limit
		PL_PS	$20d32,dt_att_syncfall
		PL_PS	$20e5a,dt_att_syncfall
		PL_PS	$2076c,dt_att_syncpitch
		PL_PS	$21004,dt_att_ground
		PL_PS	$21026,dt_att_ground
		PL_PS	$202ca,dt_att_roll
		PL_NOP	$202d0,2
		PL_PS	$20340,dt_att_roll_done
		PL_PS	$2038c,dt_att_roll_done
		PL_PS	$203b6,dt_att_pitch
		PL_NOP	$203bc,2
		PL_PS	$20438,dt_att_pitch_done
		PL_PS	$204fe,dt_att_pitch_done
		PL_PS	$20478,dt_att_reflect
		PL_PS	$2053e,dt_att_reflect
		PL_PS	$205f4,dt_att_bank
		PL_NOP	$205fa,4
		PL_PS	$206a2,dt_att_bank
		PL_NOP	$206a8,4
		PL_PS	$20cf6,dt_att_stall
		PL_PS	$20e1e,dt_att_fall
		PL_PS	$20f02,dt_att_spin
		PL_P	$1ea46,dt_air_damage
		PL_P	$1f4f6,dt_surface_damage
		PL_P	$26e46,dt_ai_lead
		PL_P	$1cf98,dt_gunner_lead
		PL_P	$218a2,dt_surface_ai
		PL_P	$24fee,dt_script_wait
		PL_PS	$267c6,dt_taxi_left
		PL_PS	$267fe,dt_taxi_right
		PL_P	$22090,dt_air_ai
		PL_P	$22eaa,dt_player_ai
		PL_PS	$b07e,dt_ai_skill
		PL_PS	$bca6,dt_ai_default
		PL_PS	$21890,dt_ai_initial_delay
		PL_PS	$22002,dt_ai_script_delay
		PL_P	$154b2,dt_move
		PL_PS	$154ba,dt_move_object
		PL_NOP	$154c0,2
		PL_PS	$15b52,dt_move_next
		PL_R	$1fee4
		PL_PS	$1c690,dt_salvo_step
		PL_NOP	$1c696,2
		PL_PS	$1c780,dt_salvo_end
		PL_PS	$1d4e0,dt_salvo_reload
		PL_P	$1c876,dt_gun_request
		PL_PS	$1c5f8,dt_gun_step
		PL_NOP	$1c5fe,2
		PL_P	$1f77e,dt_flak_launch
		PL_P	$1f7a8,dt_flak_created
		PL_NOP	$1f7ae,2
		PL_PS	$1fdd0,dt_flak_age
		PL_PS	$b308,dt_plane_generation
		PL_NOP	$b30e,2
		PL_PS	$1cdaa,dt_shot_init
		PL_NOP	$1cdb0,4
		PL_PS	$15a2c,dt_shot_age
		PL_NOP	$15a32,2
		PL_PS	$1e6f0,dt_shot_damage_age
		PL_P	$1dc54,dt_shot_cleanup
		PL_PS	$14e5e,dt_world_clock
		PL_NOP	$14e64,2
		PL_P	$176a2,dt_effects
		PL_PS	$126c8,dt_effect_init
		PL_PS	$bf96,dt_group_timer
		PL_PS	$1d500,dt_bomb_init
		PL_NOP	$1d506,2
		PL_PS	$157c2,dt_bomb_begin
		PL_PS	$159f8,dt_bomb_end
		PL_PS	$15954,dt_debris_gravity
		PL_PS	$1d5fc,dt_debris_init4
		PL_NOP	$1d602,6
		PL_PS	$1d702,dt_debris_init5
		PL_NOP	$1d708,4
		PL_PS	$176,dt_input_kind	;capture which axes came from the mouse
		PL_NOP	$17c,2
		PL_P	$304,dt_deadzone		;relative mouse motion has no dead zone
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
		PL_PS	$210de,dt_aiadd		;move.w -42(a5),d0; swap d0
		PL_PS	$21170,dt_aisub		;same bytes
		PL_PS	$1e516,dt_hit		;swept projectile hit test
		PL_W	$1e5ba,$6000		;after attacker bookkeeping, accept hit
		PL_W	$1e5bc,$1e69e-$1e5bc
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
		lea	(dt_world_time,pc),a0
		clr.l	(a0)
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
		moveq	#0,d0			;the average frame from it
		move.w	(dt_hz,pc),d0
		lsl.w	#8,d0
		divu.w	(11698,a4),d0
		lea	(dt_avg,pc),a0
		move.w	d0,(a0)
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
.time		lsl.w	#8,d1			;*DT_ONE: this frame
		lea	(dt_avg,pc),a0
		move.w	d1,d0
		sub.w	(a0),d0
		addq.w	#(1<<DT_AVG)/2,d0
		asr.w	#DT_AVG,d0
		add.w	d0,(a0)			;the average frame
		lea	(dt_err,pc),a0
		move.w	(a0),d2
		add.w	d2,d1			;time owed, fields*DT_ONE
		asr.w	#2,d2
		add.w	(dt_avg,pc),d2		;the step aimed at: average + debt/4
		moveq	#0,d0
		move.w	(dt_hz,pc),d0
		lsl.w	#8,d0			;a second: dt_hz*DT_ONE
		move.w	d0,d3
		lsr.w	#2,d3			;/DT_TMIN
		cmp.w	d3,d1
		ble.b	.owed
		move.w	d3,d1
.owed		cmp.w	d3,d2
		ble.b	.aim
		move.w	d3,d2			;at most a step of T = DT_TMIN
.aim		move.w	d2,d3
		move.w	(dt_hz,pc),d2		;T at most dt_hz: a field's time
		cmp.w	#DT_ONE,d3
		blt.b	.step
		move.w	d3,d2			;T = round(dt_hz*DT_ONE / aim)
		lsr.w	#1,d2
		ext.l	d2
		add.l	d0,d2
		divu.w	d3,d2
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
; Capture before bob:112 clears the accumulated mouse motion. The joystick
; fallback and keyboard input remain separate, so CUSTOM3 affects only mouse.
dt_input_kind	move.l	a0,-(a7)
		lea	(dt_mouse_axes,pc),a0
		move.w	(11958,a4),(a0)+
		move.w	(11960,a4),(a0)
		clr.w	(11958,a4)
		clr.w	(11960,a4)
		move.l	(a7)+,a0
		rts

; Original bob:304 filters deflections <=64/24. For relative mouse motion
; that discards real counts, depending on T and how motion is split into frames.
; Retain the original dead zones for the joystick and keyboard only.
dt_deadzone	move.l	d0,-(a7)
		move.w	(dt_mouse_axes,pc),d0
		bne.b	.pitch
		move.w	(11968,a4),d0
		bpl.b	.roll_abs
		neg.w	d0
.roll_abs	cmp.w	#64,d0
		bhi.b	.pitch
		clr.w	(11968,a4)
.pitch		move.w	(dt_mouse_axes+2,pc),d0
		bne.b	.done
		move.w	(11970,a4),d0
		bpl.b	.pitch_abs
		neg.w	d0
.pitch_abs	cmp.w	#24,d0
		bhi.b	.done
		clr.w	(11970,a4)
.done		move.l	(a7)+,d0
		rts

dt_stick	clr.w	(-4696,a4)
		clr.w	(-4694,a4)
		movem.l	d1/a0,-(a7)
		lea	(dt_mouse_axes,pc),a0
		move.w	(11968,a4),d0
		bsr.b	.scale
		move.w	d0,(11968,a4)
		move.w	(11970,a4),d0
		bsr.b	.scale
		move.w	d0,(11970,a4)
		movem.l	(a7)+,d1/a0
		rts
.scale		muls.w	(11698,a4),d0
		asr.l	#3,d0			;/DT_STICK_T
		tst.w	(a0)+
		beq.b	.limit
		move.w	(dt_mouse_shift,pc),d1
		asl.l	d1,d0			;mouse gain after time normalization
.limit
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

; The AI planes turn (bob:210a6) by v = a / 3 / 11700 * 22346[plane] >> 16, a
; the bank angle folded to 0..16384 in -42(a5), added to the heading 18162 for a
; left bank (bob:2111c) and subtracted for a right one (bob:211b8); v also goes
; to bob:214a4 and 2160a.  D4 is the object (the heading arrays are per
; object, 152).  Here v is exact in 16.16, signed, with its fraction carried
; per object.

; bob:210de: v for a left bank, on to bob:21116
dt_aiadd	movem.l	d1-d3/a0,-(a7)
		bsr	dt_airate
		bsr	dt_aicarry
		move.w	d0,(-42,a5)
		movem.l	(a7)+,d1-d3/a0
		add.l	#$21116-$210e4,(a7)
		rts

; bob:21170: v for a right bank, on to bob:211a8
dt_aisub	movem.l	d1-d3/a0,-(a7)
		bsr	dt_airate
		neg.l	d0
		bsr	dt_aicarry
		neg.w	d0
		move.w	d0,(-42,a5)
		movem.l	(a7)+,d1-d3/a0
		add.l	#$211a8-$21176,(a7)
		rts

; > D0.l a * 22346[D4] / (3 * 11700) in 16.16
dt_airate	moveq	#0,d0
		move.w	(-42,a5),d0
		move.w	d4,d1
		add.w	d1,d1
		lea	(22346,a4),a0
		mulu.w	(a0,d1.w),d0
		move.w	(11700,a4),d2
		mulu.w	#3,d2
		bra	dt_ldiv

; < D0.l v in 16.16; > D0.w with object D4's fraction carried
dt_aicarry	move.w	d4,d1
		cmp.w	#152,d1
		bhs.b	.floor
		add.w	d1,d1
		lea	(dt_aifrac,pc),a0
		add.w	d1,a0
		moveq	#0,d1
		move.w	(a0),d1
		add.l	d1,d0
		move.w	d0,(a0)
.floor		swap	d0
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
dt_rate16	mulu.w	d2,d0
		move.w	(11698,a4),d2

; < D0.l, D2.w divisor; > D0.l D0 / D2 (the quotient's upper 16 bits from the
; high word, so no overflow)
dt_ldiv		movem.l	d1-d3,-(a7)
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

; Swept relative projectile/aircraft hit test, bob:1e3d6 locals. The original
; tests coordinate sign crossings in each frame, losing hits when the same
; trajectory is split into shorter steps. Intersect the relative segment with
; the original 500-unit axis tolerance instead. Exact rational slab intervals
; avoid division, rounding and any dependence on the number of steps.
; Previous relative x/y/z: -6/-10/-14(a5); current: -18/-22/-26(a5).
; Coordinates are differences within the game's bounded world, signed longs.
dt_hit		movem.l	d0-d7/a0-a1,-(a7)
		bsr.b	dt_hit_test
		tst.l	d0
		beq.b	.miss
		movem.l	(a7)+,d0-d7/a0-a1
		add.l	#$1e590-$1e51c,(a7)	;retain attacker bookkeeping
		rts
.miss		movem.l	(a7)+,d0-d7/a0-a1
		add.l	#$1e75e-$1e51c,(a7)	;next candidate plane
		rts

; D0 = 1 for a hit, 0 for a miss; D1-D7/A0-A1 scratch.
dt_hit_test	lea	(-6,a5),a0
		lea	(-18,a5),a1
		moveq	#0,d6			;entry = 0/1
		moveq	#1,d7
		move.l	d7,-(a7)		;exit denominator
		move.l	d7,-(a7)		;exit numerator = 1
		moveq	#2,d5
.axis		move.l	(a0),d4			;previous coordinate
		move.l	(a1),d2			;current coordinate
		subq.l	#4,a0
		subq.l	#4,a1
		cmp.l	d4,d2
		bge.b	.forward
		neg.l	d4			;reflect decreasing axes
		neg.l	d2
.forward	cmp.l	#500,d4
		bgt	.miss
		cmp.l	#-500,d2
		blt	.miss
		move.l	d2,d3
		sub.l	d4,d3			;positive displacement (or zero)
		cmp.l	#-500,d4
		bge.b	.exit
		move.l	d2,-(a7)		;save current coordinate
		move.l	#-500,d0
		sub.l	d4,d0			;candidate entry numerator
		move.l	d0,-(a7)
		move.l	d3,d1			;candidate denominator
		move.l	d6,d2
		move.l	d3,-(a7)
		move.l	d7,d3
		bsr	dt_ratio_gt
		move.l	(a7)+,d3
		tst.l	d0
		beq.b	.entry_kept
		move.l	(a7),d6
		move.l	d3,d7
.entry_kept	addq.l	#4,a7
		move.l	(a7)+,d2
.exit		cmp.l	#500,d2
		ble.b	.overlap
		move.l	#500,d0
		sub.l	d4,d0			;candidate exit numerator
		move.l	d0,d2
		move.l	(a7),d0		;old exit
		move.l	(4,a7),d1
		bsr	dt_ratio_gt		;old exit > candidate?
		tst.l	d0
		beq.b	.overlap
		move.l	d2,(a7)
		move.l	d3,(4,a7)
.overlap	move.l	d6,d0
		move.l	d7,d1
		move.l	(a7),d2
		move.l	(4,a7),d3
		bsr	dt_ratio_gt		;entry > exit means no common time
		tst.l	d0
		bne.b	.miss
		dbf	d5,.axis
		moveq	#1,d0
		bra.b	.done
.miss		moveq	#0,d0
.done		addq.l	#8,a7
		rts

; Unsigned fractions D0/D1 > D2/D3? D0 = boolean, other registers preserved.
; Denominators nonzero. Compare full 64-bit cross products on every CPU.
dt_ratio_gt	movem.l	d1-d7,-(a7)
		move.l	d2,d6
		move.l	d1,d7
		move.l	d3,d1
		bsr.b	dt_mul64
		move.l	d0,-(a7)
		move.l	d1,-(a7)
		move.l	d6,d0
		move.l	d7,d1
		bsr.b	dt_mul64
		move.l	(a7)+,d2
		move.l	(a7)+,d3
		cmp.l	d1,d2
		bhi.b	.yes
		blo.b	.no
		cmp.l	d0,d3
		bhi.b	.yes
.no		moveq	#0,d0
		bra.b	.done
.yes		moveq	#1,d0
.done		movem.l	(a7)+,d1-d7
		rts

; Unsigned D0 * D1 -> D1:D0. D2-D7 preserved; 68000 compatible.
dt_mul64	movem.l	d2-d5,-(a7)
		move.l	d0,d2
		move.l	d0,d3
		swap	d3
		move.l	d1,d4
		move.l	d1,d5
		swap	d5
		mulu.w	d4,d0
		move.l	d3,d1
		mulu.w	d5,d1
		mulu.w	d5,d2
		mulu.w	d4,d3
		move.l	d2,d4
		swap	d4
		clr.w	d4
		add.l	d4,d0
		moveq	#0,d4
		addx.l	d4,d1
		swap	d2
		and.l	#$ffff,d2
		add.l	d2,d1
		move.l	d3,d4
		swap	d4
		clr.w	d4
		add.l	d4,d0
		moveq	#0,d4
		addx.l	d4,d1
		swap	d3
		and.l	#$ffff,d3
		add.l	d3,d1
		movem.l	(a7)+,d2-d5
		rts

; Bombs advance at 64 fixed steps per simulation second. Only their movement
; block is repeated, never the world loop, input, effects or damage. A partial
; step stays in the slot's accumulator (less than 1/64 s of pending time).
; The native gravity already carries acceleration fractions. Using a fixed
; step also makes its displacement rounding and ground clamp independent of
; rendering. The native target/damage dispatch still runs once after movement.
DT_BOMB_HZ = 64

; Native creation: D5 is the allocated object, D1 is its bomb-slot index.
dt_bomb_init
		clr.b	(a0,d1.l)
		movem.l	d0-d2/a0,-(a7)
		move.l	d1,d0
		lsl.w	#2,d0
		lea	(dt_bomb_time,pc),a0
		clr.l	(a0,d0.w)
		move.w	d5,d0
		mulu.w	#6,d0
		lea	(dt_frac,pc),a0
		clr.l	(a0,d0.w)
		clr.w	(4,a0,d0.w)
		move.w	d5,d0
		add.w	d0,d0
		lea	(20798,a4),a0
		move.w	#DT_BOMB_HZ*5,(a0,d0.w)
		movem.l	(a7)+,d0-d2/a0
		cmp.w	(13318,a4),d4
		rts

; Fixed movement for bombs (20..51) and debris classes 9..11 (100..111).
; Debris uses its own clocks and fractional gravity; no world/effect replay.
dt_bomb_begin
		move.w	(dt_bomb_batch,pc),d0
		bne	.exit
		cmp.w	#3,(-18,a5)
		bne	.debris
		cmp.w	#20,d4
		blo	.exit
		cmp.w	#52,d4
		bhs	.exit
		movem.l	d0-d7/a0-a3/a6,-(a7)
		move.w	(11700,a4),-(a7)
		move.w	d4,d0
		sub.w	#20,d0
		lsl.w	#2,d0
		lea	(dt_bomb_time,pc),a3
		adda.w	d0,a3
		moveq	#1,d7
		bra.b	.clock
.debris		cmp.w	#9,(-18,a5)
		blo	.exit
		cmp.w	#11,(-18,a5)
		bhi	.exit
		cmp.w	#100,d4
		blo	.exit
		cmp.w	#112,d4
		bhs	.exit
		movem.l	d0-d7/a0-a3/a6,-(a7)
		move.w	(11700,a4),-(a7)
		move.w	d4,d0
		sub.w	#100,d0
		lsl.w	#2,d0
		lea	(dt_debris_time,pc),a3
		adda.w	d0,a3
		moveq	#2,d7
.clock
	; ceil(64 * 65536 / T), split DIVU to avoid its 16-bit quotient limit.
		moveq	#DT_BOMB_HZ,d0
		divu.w	(11700,a4),d0
		move.w	d0,d6
		swap	d6
		clr.w	d0
		divu.w	(11700,a4),d0
		move.w	d0,d6
		swap	d0
		tst.w	d0
		beq.b	.exact
		addq.l	#1,d6
.exact		add.l	(a3),d6
		moveq	#0,d0
		move.w	d6,d0
		move.l	d0,(a3)
		swap	d6
		and.l	#$ffff,d6
		beq	.done
		move.w	#DT_BOMB_HZ,(11700,a4)
		lea	(dt_bomb_active,pc),a0
		move.b	d7,(a0)
.tick		move.w	#DT_BOMB_HZ,-(a7)
		move.w	d4,d0
		add.w	d0,d0
		lea	(19694,a4),a0
		move.w	(a0,d0.w),-(a7)
		bsr	dt_steplen
		move.w	d0,(-2,a5)
		move.l	(-31744,a4),a2
		cmp.w	#2,d7
		beq.b	.debris_tick
		adda.l	#$157c8-$2eb4a,a2
		cmp.w	#3,(-18,a5)		;Z for the native branch at 157c8
		jsr	(a2)			;returns through dt_bomb_end
		bra.b	.contact
.debris_tick	adda.l	#$1589c-$2eb4a,a2
		jsr	(a2)			;skip native frame-based drag/expiry
		move.w	d4,d0
		add.w	d0,d0
		lea	(20798,a4),a0
		subq.w	#1,(a0,d0.w)
		bne.b	.contact
		cmp.w	#9,(-18,a5)
		beq.b	.expire
		move.w	#DT_BOMB_HZ*5,(a0,d0.w)
		lea	(19694,a4),a0
		tst.w	(a0,d0.w)
		beq.b	.contact
		subq.w	#1,(a0,d0.w)
		bra.b	.contact
.expire		lea	(13394,a4),a0
		clr.b	(a0,d4.w)
		bra.b	.landed
.contact	move.w	d4,d0
		lsl.w	#2,d0
		lea	(15506,a4),a0
		tst.l	(a0,d0.w)
		beq.b	.landed			;do not keep moving along the ground
		subq.w	#1,d6
		bne	.tick
.landed		lea	(dt_bomb_active,pc),a0
		clr.b	(a0)
.done		move.w	(a7)+,(11700,a4)
		movem.l	(a7)+,d0-d7/a0-a3/a6
		add.l	#$15b52-$157c8,(a7)	;continue at the next object
.exit		cmp.w	#3,(-18,a5)
		rts

; Native movement joins here before clamping altitude. During a fixed step,
; return to the wrapper instead of advancing the whole world's object loop.
dt_bomb_end
		moveq	#0,d0
		move.w	d4,d0
		asl.l	#2,d0
		lea	(dt_bomb_active,pc),a0
		tst.b	(a0)
		beq.b	.exit
		lea	(15506,a4),a0
		tst.l	(a0,d0.l)
		bpl.b	.return
		clr.l	(a0,d0.l)
.return		addq.l	#4,a7		;discard the patch's return address
		rts				;return from the native block to .tick
.exit		rts

; Constructors have already copied native position/velocity. Replace timer
; initialization and reset private state even when a slot is reused in one frame.
dt_debris_init4
		movem.l	d0-d2/a0,-(a7)
		move.w	d4,d2
		move.w	#DT_BOMB_HZ*5,d1
		bra.b	dt_debris_init
dt_debris_init5
		movem.l	d0-d2/a0,-(a7)
		move.w	d5,d2
		move.w	#DT_BOMB_HZ*4,d1
dt_debris_init
		move.w	d2,d0
		add.w	d0,d0
		lea	(20798,a4),a0
		move.w	d1,(a0,d0.w)
		move.w	d2,d0
		sub.w	#100,d0
		add.w	d0,d0
		lea	(dt_debris_grav,pc),a0
		clr.w	(a0,d0.w)
		add.w	d0,d0
		lea	(dt_debris_time,pc),a0
		clr.l	(a0,d0.w)
		mulu.w	#6,d2
		lea	(dt_frac,pc),a0
		clr.l	(a0,d2.w)
		clr.w	(4,a0,d2.w)
		movem.l	(a7)+,d0-d2/a0
		rts

; Exact 22/64 gravity carry, private to debris (native bomb carry is smaller).
; Called only for classes 9..11 by their fixed movement block.
dt_debris_gravity
		movem.l	d0-d1/a0,-(a7)
		lea	(dt_bomb_active,pc),a0
		cmp.b	#2,(a0)
		beq.b	.fixed
		movem.l	(a7)+,d0-d1/a0
		moveq	#22,d0
		swap	d0
		clr.w	d0
		rts
.fixed
		move.w	d4,d0
		sub.w	#100,d0
		add.w	d0,d0
		lea	(dt_debris_grav,pc),a0
		move.w	(a0,d0.w),d1
		add.w	#22,d1
		move.w	d1,(a0,d0.w)
		and.w	#63,(a0,d0.w)
		lsr.w	#6,d1
		move.w	d4,d0
		add.w	d0,d0
		lea	(20030,a4),a0
		sub.w	d1,(a0,d0.w)
		movem.l	(a7)+,d0-d1/a0
		add.l	#$15982-$1595a,(a7)
		rts

dt_debris_time	dcb.l	12,0
dt_debris_grav	dcb.w	12,0

dt_bomb_active	dc.w	0
dt_bomb_time	dcb.l	32,0

dt_mouse_axes	dc.w	0,0
dt_mouse_shift	dc.w	1			;2x default; CUSTOM3 selects 1x/4x/8x
dt_mdx		dc.w	0
dt_mdy		dc.w	0
dt_boot		dc.w	0
dt_last		dc.w	0
dt_live		dc.w	0
dt_err		dc.w	0
dt_avg		dc.w	0			;average frame, fields*DT_ONE
dt_hz		dc.w	DT_HZ			;fields per second, measured at boot
dt_len		dc.w	0,0,0,0,0		;valid, integer, fraction, rounded, object
dt_rfrac	dcb.w	DT_PLANES*3,0		;roll, heading, pitch rate fractions per plane
dt_frac		dcb.w	152*3,0			;x, y, z fractions per object (bob:154ba)
dt_aifrac	dcb.w	152,0			;AI turn fraction per object (bob:210a6)

; FR-02: immediate initial group scan, then every five simulation seconds.
; Native flight setup clears 24450 (bob:126e4); retain it as a reset marker.
; 8.24 seconds avoids a frame-count byte and keeps overshoot between scans.
dt_group_timer
		movem.l	d0-d1/a0,-(a7)
		lea	(dt_group_left,pc),a0
		tst.b	(24450,a4)
		bne.b	.advance
		move.b	#1,(24450,a4)
		move.l	#5*$1000000,(a0)
		bra.b	.due
.advance	move.l	#$100,d0
		divu.w	(11700,a4),d0
		move.w	d0,d1
		swap	d1
		clr.w	d0
		divu.w	(11700,a4),d0
		move.w	d0,d1
		swap	d0
		tst.w	d0
		beq.b	.exact
		addq.l	#1,d1		;ceil(2^24/T), error < 2^-24 s/update
.exact		sub.l	d1,(a0)
		bgt.b	.wait
		add.l	#5*$1000000,(a0)
.due		movem.l	(a7)+,d0-d1/a0
		add.l	#$bfb0-$bf9c,(a7)	;unchanged native eligibility/placement
		rts
.wait		movem.l	(a7)+,d0-d1/a0
		add.l	#$c0f6-$bf9c,(a7)	;native epilogue
		rts

dt_group_left	dc.l	0

; FR-03: native effect state machine at its nominal eight ticks/second.
; Preserve every intermediate transition, including on accelerated/slow frames.
dt_effect_init
		movem.l d4/a0,-(a7)
		moveq #15,d4
.att_reset	bsr dt_att_reset
		dbf d4,.att_reset
		movem.l (a7)+,d4/a0
		move.l	a0,-(a7)
		lea	(dt_velocity_t,pc),a0
		clr.w	(a0)
		lea	(dt_bomb_batch_time,pc),a0
		clr.l	(a0)+
		clr.w	(a0)
		move.l	(a7)+,a0
		move.w	(11702,a4),(11704,a4)
		move.l	a0,-(a7)
		lea	(dt_effect_time,pc),a0
		clr.l	(a0)
		move.l	(a7)+,a0
		rts

dt_effects
		movem.l	d0-d7/a0-a3/a5-a6,-(a7)
		move.l	#$100,d0
		divu.w	(11700,a4),d0
		move.w	d0,d1
		swap	d1
		clr.w	d0
		divu.w	(11700,a4),d0
		move.w	d0,d1
		swap	d0
		tst.w	d0
		beq.b	.exact
		addq.l	#1,d1		;ceil(2^24/T) seconds
.exact		lea	(dt_effect_time,pc),a0
		add.l	d1,(a0)
.next		lea	(dt_effect_time,pc),a0
		cmp.l	#$200000,(a0)		;one eighth of a second
		blo.b	.done
		sub.l	#$200000,(a0)
		bsr.b	dt_effect_tick
		bra.b	.next
.done		movem.l	(a7)+,d0-d7/a0-a3/a5-a6
		rts

; Recreate the native stack frame, bypass only its frame-counted timer.
; The original epilogue returns to our catch-up loop.
dt_effect_tick
		link	a5,#-30
		movem.l	d4-d5,-(a7)
		move.l	(-31744,a4),a0
		adda.l	#$176bc-$2eb4a,a0
		jmp	(a0)

dt_effect_time	dc.l	0

; FR-04: one world-clock second per simulation second. Native date rollover
; and daylight calculations remain in bob; only its frame timer is replaced.
dt_world_clock
		movem.l	d0-d1/a0,-(a7)
		bsr.b	dt_seconds
		lea	(dt_world_time,pc),a0
		add.l	d0,(a0)
		cmp.l	#$1000000,(a0)
		blo.b	.wait
		sub.l	#$1000000,(a0)
		movem.l	(a7)+,d0-d1/a0
		add.l	#$14e6e-$14e64,(a7)
		rts
.wait		movem.l	(a7)+,d0-d1/a0
		add.l	#$14e9e-$14e64,(a7)
		rts

; D0 = ceil(2^24 / simulation divisor), D1 clobbered; 68000-safe division.
dt_seconds
		move.l	#$100,d0
		divu.w	(11700,a4),d0
		move.w	d0,d1
		swap	d1
		clr.w	d0
		divu.w	(11700,a4),d0
		move.w	d0,d1
		swap	d0
		tst.w	d0
		beq.b	.exact
		addq.l	#1,d1
.exact		move.l	d1,d0
		rts

dt_world_time	dc.l	0

; FR-05: two-second projectile life and one-second damage-age boundary.
dt_shot_init
		move.w	(11700,a4),d1
		add.w	d1,d1
		move.w	d1,(a0,d0.l)
		movem.l	d0-d1/a0,-(a7)
		move.w	(-2,a5),d0
		sub.w	#52,d0
		lea	(dt_shot_pending,pc),a0
		clr.b	(a0,d0.w)
		lsl.w	#2,d0
		lea	(dt_shot_left,pc),a0
		move.l	#2*$1000000,(a0,d0.w)
		move.w	(-2,a5),d0
		mulu.w	#6,d0
		lea	(dt_frac,pc),a0
		clr.l	(a0,d0.w)
		clr.w	(4,a0,d0.w)
		movem.l	(a7)+,d0-d1/a0
		rts

dt_shot_age
		movem.l	d0-d3/a0-a1,-(a7)
		move.w	d4,d3
		sub.w	#52,d3
		lsl.w	#2,d3
		lea	(dt_shot_left,pc),a1
		adda.w	d3,a1
		tst.l	(a1)
		beq	.expired
		bsr	dt_seconds
		cmp.l	(a1),d0
		blo.b	.live
		move.l	(a1),d0		;clip final movement to remaining life
		move.w	d4,d3
		sub.w	#52,d3
		lea	(dt_shot_pending,pc),a0
		st	(a0,d3.w)
.live		sub.l	d0,(a1)
		move.l	d0,d1
		move.w	d4,d0
		add.w	d0,d0
		lea	(19694,a4),a0
		move.w	(a0,d0.w),d0
		mulu.w	#4660,d0
		add.l	#128,d0
		lsr.l	#8,d0
		bsr	dt_mul64		;speed units/second * elapsed Q24
		lsr.l	#8,d0
		lsl.l	#8,d1
		lsl.l	#8,d1
		lsl.l	#8,d1
		or.l	d1,d0		;16.16 distance
		lea	(dt_len,pc),a0
		st	(a0)
		move.l	d0,(2,a0)
		move.w	d4,(8,a0)
		swap	d0
		move.w	d0,(6,a0)
		move.w	d0,(-2,a5)
		movem.l	(a7)+,d0-d3/a0-a1
		add.l	#$15a46-$15a32,(a7)
		rts
.expired	movem.l	(a7)+,d0-d3/a0-a1
		add.l	#$15a36-$15a32,(a7)
		rts

dt_shot_damage_age
		movem.l	d0/a0,-(a7)
		move.w	d4,d0
		sub.w	#52,d0
		lsl.w	#2,d0
		lea	(dt_shot_left,pc),a0
		cmp.l	#$1000000,(a0,d0.w)
		movem.l	(a7)+,d0/a0
		bhi.b	.young
		addq.l	#4,(a7)		;skip native double-damage shift
.young		rts

; Retire after the final swept segment has been tested, not before it.
; Replaces the native impact-dispatch epilogue.
dt_shot_cleanup
		movem.l	d0/a0-a1,-(a7)
		lea	(dt_shot_pending,pc),a0
		lea	(13394+52,a4),a1
		moveq	#47,d0
.loop		tst.b	(a0)
		beq.b	.next
		clr.b	(a0)
		clr.b	(a1)
.next		addq.l	#1,a0
		addq.l	#1,a1
		dbf	d0,.loop
		movem.l	(a7)+,d0/a0-a1
		move.l	(a7)+,d4
		unlk	a5
		rts

dt_shot_left	dcb.l	48,0
dt_shot_pending	dcb.b	48,0

; FR-06: use the established 8Hz reference for native flak launch jitter.
; Normalize per-update target displacement to 1/8 second for native lead math,
; then restore it and T. Hit probability/RNG and native miss placement remain.
dt_flak_launch
		movem.l	d0-d7/a0-a3/a5-a6,-(a7)
		lea	(60,a7),a6
		move.w	(11700,a4),-(a7)
		bsr	dt_velocity_rate
		move.w	#8,(11700,a4)
		lea	(-12,a7),a7
		move.l	a7,a1
		moveq	#0,d0
		move.w	(2,a6),d0
		lsl.w	#2,d0
		lea	(17378,a4),a0
		adda.w	d0,a0
		moveq	#2,d2
.scale		move.l	(a0),d0
		move.l	d0,(a1)+
		moveq	#0,d3
		tst.l	d0
		bpl.b	.positive
		moveq	#1,d3
		neg.l	d0
.positive	moveq	#0,d1
		move.w	d7,d1
		bsr	dt_mul64
		lsr.l	#3,d0
		ror.l	#3,d1
		or.l	d1,d0
		tst.w	d3
		beq.b	.store
		neg.l	d0
.store		move.l	d0,(a0)
		lea	(64,a0),a0
		dbf	d2,.scale
		move.w	(4,a6),-(a7)
		move.w	(2,a6),-(a7)
		move.w	(a6),-(a7)
		bsr.b	dt_flak_native
		addq.l	#6,a7
		lea	(74,a7),a6
		moveq	#0,d0
		move.w	(2,a6),d0
		lsl.w	#2,d0
		lea	(17378,a4),a0
		adda.w	d0,a0
		moveq	#2,d2
.restore	move.l	(a7)+,(a0)
		lea	(64,a0),a0
		dbf	d2,.restore
		move.w	(a7)+,(11700,a4)
		movem.l	(a7)+,d0-d7/a0-a3/a5-a6
		rts

dt_flak_native
		link	a5,#-26
		movem.l	d4-d5,-(a7)
		move.l	(-31744,a4),a0
		adda.l	#$1f786-$2eb4a,a0
		jmp	(a0)

; Common creation epilogue, including allocation failure (D5=124).
dt_flak_created
		cmp.w	#124,d5
		bhs.b	.done
		movem.l	d0-d2/a0-a1,-(a7)
		move.w	d5,d0
		add.w	d0,d0
		lea	(20798,a4),a0
		moveq	#0,d1
		move.w	(a0,d0.w),d1
		lsl.l	#8,d1
		lsl.l	#5,d1		;native reference ticks /8 in Q16 seconds
		move.w	d5,d0
		sub.w	#112,d0
		lsl.w	#2,d0
		lea	(dt_flak_left,pc),a0
		move.l	d1,(a0,d0.w)
		lea	(dt_flak_generation,pc),a0
		clr.l	(a0,d0.w)
		cmp.w	#16,d4
		bhs.b	.saved
		move.w	d4,d2
		lsl.w	#2,d2
		lea	(dt_plane_ids,pc),a1
		move.l	(a1,d2.w),(a0,d0.w)
.saved		movem.l	(a7)+,d0-d2/a0-a1
.done		movem.l	(a7)+,d4-d5
		unlk	a5
		rts

dt_plane_generation
		bsr	dt_att_reset
		bsr	dt_gun_reset
		movem.l	d0/a0,-(a7)
		move.w	d4,d0
		lsl.w	#2,d0
		lea	(dt_plane_ids,pc),a0
		addq.l	#1,(a0,d0.w)
		movem.l	(a7)+,d0/a0
		move.w	(25990,a4),d0
		mulu.w	#26,d0
		rts

dt_flak_age
		movem.l	d0-d3/a0-a1,-(a7)
		lea	(13394,a4),a0
		cmp.b	#34,(a0,d4.w)
		beq.b	.active
		cmp.b	#35,(a0,d4.w)
		bne	.wait
.active		move.w	d4,d3
		sub.w	#112,d3
		lsl.w	#2,d3
		bsr	dt_seconds
		add.l	#255,d0
		lsr.l	#8,d0		;ceil(65536/T)
		lea	(dt_flak_left,pc),a0
		cmp.l	(a0,d3.w),d0
		bhs.b	.due
		sub.l	d0,(a0,d3.w)
		bra.b	.wait
.due		clr.l	(a0,d3.w)
		move.w	d4,d0
		add.w	d0,d0
		lea	(20798,a4),a0
		clr.w	(a0,d0.w)
		lea	(13394,a4),a0
		cmp.b	#34,(a0,d4.w)
		beq.b	.deliver
		lea	(20470,a4),a1
		moveq	#0,d0
		move.b	(a1,d4.w),d0
		tst.b	(a0,d0.w)
		beq.b	.stale
		cmp.w	#16,d0
		bhs.b	.deliver
		lsl.w	#2,d0
		lea	(dt_plane_ids,pc),a0
		move.l	(a0,d0.w),d1
		lea	(dt_flak_generation,pc),a0
		cmp.l	(a0,d3.w),d1
		beq.b	.deliver
.stale		lea	(13394,a4),a0
		clr.b	(a0,d4.w)
		bra.b	.wait
.deliver	movem.l	(a7)+,d0-d3/a0-a1
		add.l	#$1fe02-$1fdd6,(a7)
		rts
.wait		movem.l	(a7)+,d0-d3/a0-a1
		add.l	#$1fed4-$1fdd6,(a7)
		rts

dt_flak_left	dcb.l	12,0
dt_flak_generation dcb.l	12,0
dt_plane_ids	dcb.l	16,0

; FR-07: requests are serviced in the gun section of the native weapon update.
; One fire event per third second; preserve phase across reload/rate changes.
; The caller ignores the player fire result. Bombs still run once per update.
dt_gun_request
		movem.l	d1/a0,-(a7)
		move.w	(13318,a4),d0
		mulu.w	#5,d0
		moveq	#0,d1
		move.w	(12,a7),d1
		add.w	d1,d0
		lea	(dt_gun_requests,pc),a0
		st	(a0,d0.w)
		movem.l	(a7)+,d1/a0
		moveq	#0,d0
		rts

dt_gun_reset
		movem.l	d0-d1/a0-a1,-(a7)
		move.w	d4,d0
		lsl.w	#2,d0
		lea	(dt_salvo_left,pc),a0
		clr.l	(a0,d0.w)
		move.w	d4,d0
		mulu.w	#5,d0
		lea	(dt_gun_requests,pc),a0
		adda.w	d0,a0
		lsl.w	#2,d0
		lea	(dt_gun_left,pc),a1
		adda.w	d0,a1
		moveq	#4,d1
.loop		clr.b	(a0)+
		clr.l	(a1)+
		dbf	d1,.loop
		movem.l	(a7)+,d0-d1/a0-a1
		rts

dt_gun_step
		movem.l	d0-d3/d6-d7/a0-a3,-(a7)
		move.l	(40,a7),a3
		adda.l	#$1c8a8-$1c5fe,a3
		move.w	d4,d6
		mulu.w	#5,d6
		add.w	d5,d6
		move.w	d6,d0
		lsl.w	#2,d0
		lea	(dt_gun_left,pc),a2
		adda.w	d0,a2
		bsr	dt_seconds
		subq.l	#1,d0		;lower bound: never emit at the interval end
		move.l	d0,d7
.again		cmp.l	(a2),d7
		bls.b	.advance
		lea	(dt_gun_requests,pc),a0
		tst.b	(a0,d6.w)
		bne.b	.fire
		lea	(23586,a4),a0
		cmp.b	#1,(a0,d6.w)
		bne.b	.idle
.fire		move.w	d5,-(a7)
		move.w	d4,-(a7)
		jsr	(a3)			;native ammo, barrels, sound and slot allocation
		addq.w	#4,a7
		add.l	#5592406,(a2)		;ceil(2^24/3) seconds per event
		lea	(23586,a4),a0
		cmp.b	#1,(a0,d6.w)
		bne.b	.again
		lea	(23666,a4),a1
		subq.b	#1,(a1,d6.w)
		bne.b	.again
		move.b	#2,(a0,d6.w)
		bra.b	.again
.idle		move.l	d7,(a2)		;no stored firing credit after release
.advance	sub.l	d7,(a2)
		lea	(dt_gun_requests,pc),a0
		clr.b	(a0,d6.w)
		lea	(23106,a4),a0
		tst.l	(a2)
		sne	(a0,d6.w)		;compatibility busy marker, not a frame count
		movem.l	(a7)+,d0-d3/d6-d7/a0-a3
		add.l	#$1c686-$1c5fe,(a7)
		rts

dt_gun_left	dcb.l	80,0
dt_gun_requests dcb.b	80,0

; FR-08: half-second salvo releases, with source position at the due instant.
dt_salvo_reload
		movem.l	d0/a0,-(a7)
		move.w	(dt_salvo_active,pc),d0
		bne.b	.done
		move.w	d4,d0
		lsl.w	#2,d0
		lea	(dt_salvo_left,pc),a0
		move.l	#$800000,(a0,d0.w)
.done		movem.l	(a7)+,d0/a0
		moveq	#1,d0
		rts

dt_salvo_end
		move.w	(dt_salvo_active,pc),d0
		beq.b	.normal
		addq.l	#4,a7		;return from the native salvo section
		rts
.normal		addq.w	#1,d4
		cmp.w	#16,d4
		rts

dt_salvo_step
		movem.l	d0-d3/d6-d7/a0-a3,-(a7)
		move.l	(40,a7),a3
		adda.l	#$1c6be-$1c696,a3
		move.w	d4,d6
		lsl.w	#2,d6
		lea	(dt_salvo_left,pc),a2
		adda.w	d6,a2
		bsr	dt_seconds
		subq.l	#1,d0
		move.l	d0,d7
.again		cmp.l	(a2),d7
		bls	.advance
		lea	(23890,a4),a0
		tst.b	(a0,d4.w)
		beq	.idle
		; Fraction of this step after the release, in Q24.
		move.l	d7,d0
		sub.l	(a2),d0
		moveq	#0,d1
		move.w	(11700,a4),d1
		bsr	dt_mul64
		move.l	d0,d3
		lea	(14290,a4),a0
		adda.w	d6,a0
		lea	(17378,a4),a1
		adda.w	d6,a1
		moveq	#2,d2
.pose		move.l	(a0),-(a7)
		move.l	(a1),d0
		bpl.b	.positive
		neg.l	d0
.positive	move.l	d3,d1
		bsr	dt_mul64
		lsr.l	#8,d0
		lsr.l	#8,d0
		lsr.l	#8,d0
		lsl.l	#8,d1
		or.l	d1,d0
		tst.l	(a1)
		bpl.b	.subtract
		neg.l	d0
.subtract	sub.l	d0,(a0)
		adda.w	#608,a0
		adda.w	#64,a1
		dbf	d2,.pose
		lea	(dt_salvo_active,pc),a0
		move.w	#1,(a0)
		jsr	(a3)			;unchanged native release/count/guidance/HUD
		lea	(dt_salvo_active,pc),a0
		clr.w	(a0)
		lea	(15506,a4),a0
		adda.w	d6,a0
		moveq	#2,d2
.restore	move.l	(a7)+,(a0)
		suba.w	#608,a0
		dbf	d2,.restore
		add.l	#$800000,(a2)
		bra	.again
.idle		move.l	d7,(a2)
.advance	sub.l	d7,(a2)
		lea	(23922,a4),a0
		tst.l	(a2)
		sne	(a0,d4.w)
		movem.l	(a7)+,d0-d3/d6-d7/a0-a3
		add.l	#$1c780-$1c696,(a7)
		rts

dt_salvo_active dc.w	0
dt_salvo_left	dcb.l	16,0

; FR-09: interleave the complete bomb pool and native guidance on one 64 Hz
; clock. Per-object catch-up cannot safely propagate a leader's turn to peers.
dt_move
		movem.l	d0-d7/a0-a3/a5-a6,-(a7)
		move.w	(11700,a4),-(a7)
		move.l	(-31744,a4),a6
		suba.l	#$2eb4a,a6
		bsr	dt_move_native
		bsr	dt_seconds
		addq.l	#3,d0
		lsr.l	#2,d0		;ceil(64*65536/T)
		lea	(dt_bomb_batch_time,pc),a0
		add.l	(a0),d0
		move.l	d0,d6
		and.l	#$ffff,d0
		move.l	d0,(a0)
		swap	d6
		and.l	#$ffff,d6
		beq.b	.done
		lea	(dt_bomb_batch,pc),a0
		move.w	#1,(a0)
		move.w	#64,(11700,a4)
.tick		lea	(dt_guidance_ticks,pc),a0
		tst.w	(a0)
		bne.b	.move
		move.w	#32,(a0)
		bsr	dt_guidance_native
.move		lea	(dt_guidance_ticks,pc),a0
		subq.w	#1,(a0)
		bsr	dt_move_native
		subq.w	#1,d6
		bne.b	.tick
		lea	(dt_bomb_batch,pc),a0
		clr.w	(a0)
.done		move.w	(a7)+,(11700,a4)
		lea	(dt_velocity_t,pc),a0
		move.w	(11700,a4),(a0)
		movem.l	(a7)+,d0-d7/a0-a3/a5-a6
		rts

dt_move_native
		link	a5,#-18
		move.l	d4,-(a7)
		moveq	#0,d4
		move.w	(dt_bomb_batch,pc),d0
		beq.b	.start
		moveq	#20,d4
.start		move.l	a6,a0
		adda.l	#$154ba,a0
		jmp	(a0)

dt_guidance_native
		link	a5,#-4
		movem.l	d4-d5,-(a7)
		move.l	a6,a0
		adda.l	#$1ff04,a0
		jmp	(a0)

dt_move_object
		moveq	#0,d0
		move.w	d4,d0
		move.w	(dt_bomb_batch,pc),d1
		bne.b	.batch
		cmp.w	#20,d4
		blo.b	.normal
		cmp.w	#52,d4
		bhs.b	.normal
		lea	(13562,a4),a0
		cmp.b	#3,(a0,d0.w)
		bne.b	.normal
		bra.b	.skip
.batch		lea	(13562,a4),a0
		cmp.b	#3,(a0,d0.w)
		bne.b	.skip
		move.w	d4,d1
		lsl.w	#2,d1
		lea	(15506,a4),a0
		tst.l	(a0,d1.w)
		beq.b	.skip
.normal		lea	(13394,a4),a0
		rts
.skip		add.l	#$15b52-$154c0,(a7)
		rts

dt_move_next
		addq.w	#1,d4
		move.w	(dt_bomb_batch,pc),d0
		bne.b	.batch
		cmp.w	#152,d4
		rts
.batch		cmp.w	#52,d4
		rts

dt_bomb_batch	dc.w	0
dt_bomb_batch_time dc.l	0
dt_guidance_ticks dc.w	0

; FR-10: native aircraft damage decisions, three times per simulation second.
dt_air_damage
		movem.l	d0-d7/a0-a3/a5-a6,-(a7)
		lea	(dt_air_damage_left,pc),a2
		tst.w	(11714,a4)
		bne.b	.live
		clr.l	(a2)
		move.w	#1,(11714,a4)	;native flight reset is the initialization marker
.live		move.l	#5592406,d7
		lea	(dt_air_damage_native,pc),a3
		bsr	dt_periodic
		movem.l	(a7)+,d0-d7/a0-a3/a5-a6
		rts

dt_air_damage_native
		link	a5,#-12
		movem.l	d4-d5,-(a7)
		move.l	(-31744,a4),a0
		adda.l	#$1ea6e-$2eb4a,a0
		jmp	(a0)

; Run a native subsystem at each deadline in this half-open update interval.
; A2 -> Q24 countdown, A3 = native body, D7 = period. Caller saves registers.
dt_periodic
		bsr	dt_seconds
		subq.l	#1,d0		;conservative elapsed rounding, like gun/salvo clocks
		move.l	d0,d6
.again		cmp.l	(a2),d6
		bls.b	.done
		jsr	(a3)
		add.l	d7,(a2)
		bra.b	.again
.done		sub.l	d6,(a2)
		rts

dt_air_damage_left dc.l	0

; FR-11: surface damage progression, once per four simulation seconds.
dt_surface_damage
		movem.l	d0-d7/a0-a3/a5-a6,-(a7)
		lea	(dt_surface_damage_left,pc),a2
		tst.w	(11712,a4)
		bne.b	.live
		clr.l	(a2)
		move.w	#1,(11712,a4)
.live		move.l	#$4000000,d7
		lea	(dt_surface_damage_native,pc),a3
		bsr	dt_periodic
		movem.l	(a7)+,d0-d7/a0-a3/a5-a6
		rts

dt_surface_damage_native
		link	a5,#-8
		move.l	d4,-(a7)
		move.l	(-31744,a4),a0
		adda.l	#$1f514-$2eb4a,a0
		jmp	(a0)

dt_surface_damage_left dc.l	0

; FR-12: native aircraft decisions keep their skill period in Q24 seconds.
; Native byte intervals remain available to script/aim calculations.
dt_ai_skill
		move.b	(-3,a5),(a0,d0.l)
		movem.l	d0-d2/a0,-(a7)
		move.l	#$2000000,d1
		move.w	(-2,a5),d2
		cmp.w	#$4000,d2
		blo.b	.store
		lsr.l	#1,d1
		cmp.w	#$8000,d2
		blo.b	.store
		lsr.l	#1,d1
		cmp.w	#$c000,d2
		blo.b	.store
		move.l	#5592406,d1
.store		lsl.w	#2,d0
		lea	(dt_ai_period,pc),a0
		move.l	d1,(a0,d0.w)
		movem.l	(a7)+,d0-d2/a0
		rts

dt_ai_default
		move.b	d0,(a0,d1.l)
		movem.l	d1/a0,-(a7)
		lsl.w	#2,d1
		lea	(dt_ai_period,pc),a0
		move.l	#$2000000,(a0,d1.w)
		movem.l	(a7)+,d1/a0
		moveq	#1,d0
		rts

dt_ai_initial_delay
		moveq	#0,d1
		move.w	(11710,a4),d1
		bra.b	dt_ai_delay

dt_ai_script_delay
		move.b	d0,(a0,d1.l)
		bsr.b	dt_ai_delay
		moveq	#0,d0
		rts

dt_ai_delay
		cmp.w	#20,d1
		bhs.b	.done
		movem.l	d1/a0,-(a7)
		lea	(dt_ai_restart,pc),a0
		move.b	#1,(a0,d1.w)
		lsl.w	#2,d1
		lea	(dt_ai_left,pc),a0
		move.l	#$2000000,(a0,d1.w)
		movem.l	(a7)+,d1/a0
.done		rts

dt_air_ai
		movem.l	d0-d7/a0-a3/a5-a6,-(a7)
		bsr	dt_seconds
		subq.l	#1,d0
		move.l	d0,d7
		move.l	(-31744,a4),a3
		adda.l	#$22140-$2eb4a,a3
; Select the earliest event, breaking ties by slot. Catch-up must not reorder
; the shared RNG stream when more than one aircraft is due in an outer frame.
.scan		move.l	d7,d5
		moveq	#-1,d6
		moveq	#0,d4
		lea	(dt_ai_left,pc),a2
.object		lea	(13394,a4),a0
		tst.b	(a0,d4.w)
		beq.b	.next
		lea	(22706,a4),a0
		tst.b	(a0,d4.w)
		bne.b	.next
		lea	(13562,a4),a0
		cmp.b	#1,(a0,d4.w)
		bne.b	.next
		cmp.l	(a2),d5
		bls.b	.next
		move.l	(a2),d5
		move.w	d4,d6
.next		addq.l	#4,a2
		addq.w	#1,d4
		cmp.w	#16,d4
		blo.b	.object
		bsr.b	dt_ai_advance
		sub.l	d5,d7
		tst.w	d6
		bmi.b	.done
		move.w	d6,d4
		move.w	d4,d0
		lsl.w	#2,d0
		lea	(dt_ai_left,pc),a2
		adda.w	d0,a2
		lea	(dt_ai_restart,pc),a0
		clr.b	(a0,d4.w)
		move.w	d4,(11706,a4)
		jsr	(a3)
		lea	(dt_ai_restart,pc),a0
		tst.b	(a0,d4.w)
		bne.b	.scan
		move.w	d4,d0
		lsl.w	#2,d0
		lea	(dt_ai_period,pc),a0
		move.l	(a0,d0.w),(a2)
		bne.b	.scan
		move.l	#$2000000,(a2)
		bra.b	.scan
.done		clr.w	(11706,a4)
		movem.l	(a7)+,d0-d7/a0-a3/a5-a6
		rts

dt_ai_advance
		lea	(dt_ai_left,pc),a0
		moveq	#15,d0
.loop		move.l	(a0),d1
		sub.l	d5,d1
		bcc.b	.store
		moveq	#0,d1
.store		move.l	d1,(a0)+
		dbf	d0,.loop
		rts

dt_player_ai
		movem.l	d0-d7/a0-a3/a5-a6,-(a7)
		lea	(dt_player_ai_left,pc),a2
		tst.b	(13332,a4)
		bne.b	.live
		clr.l	(a2)
		move.b	#1,(13332,a4)
.live		cmp.b	#1,(13322,a4)
		beq.b	.manual
		move.l	#$1000000,d7
		lea	(dt_player_ai_native,pc),a3
		bsr	dt_periodic
		bra.b	.restore
.manual		bsr	dt_seconds
		subq.l	#1,d0
		cmp.l	(a2),d0
		blo.b	.subtract
		move.l	(a2),d0
.subtract	sub.l	d0,(a2)
.restore	movem.l	(a7)+,d0-d7/a0-a3/a5-a6
		rts

dt_player_ai_native
		cmp.b	#1,(13322,a4)
		beq.b	.done
		link	a5,#-6
		move.l	(-31744,a4),a0
		adda.l	#$22ec2-$2eb4a,a0
		jmp	(a0)
.done		rts

dt_ai_period	dcb.l	16,0
dt_ai_left	dcb.l	20,0
dt_ai_restart	dcb.b	20,0
dt_player_ai_left dc.l	0

; FR-13: reference-8Hz native pursuit and gunner lead. The displacement arrays
; describe the last completed movement step, which may have used another T.
dt_ai_lead
		movem.l	d0-d7/a0-a3/a5-a6,-(a7)
		lea	(60,a7),a6
		moveq	#0,d0
		move.w	(a6),d0
		lea	(dt_ai_lead_native,pc),a3
		bra.b	dt_lead

dt_gunner_lead
		movem.l	d0-d7/a0-a3/a5-a6,-(a7)
		lea	(60,a7),a6
		moveq	#0,d0
		move.w	(2,a6),d0
		lea	(dt_gunner_lead_native,pc),a3

dt_lead
		move.w	d0,-(a7)
		move.w	(11700,a4),-(a7)
		bsr	dt_velocity_rate
		move.w	#8,(11700,a4)
		lea	(-12,a7),a7
		move.l	a7,a1
		lsl.w	#2,d0
		lea	(17378,a4),a0
		adda.w	d0,a0
		moveq	#2,d2
.scale		move.l	(a0),d0
		move.l	d0,(a1)+
		moveq	#0,d3
		tst.l	d0
		bpl.b	.positive
		moveq	#1,d3
		neg.l	d0
.positive	moveq	#0,d1
		move.w	d7,d1
		bsr	dt_mul64
		lsr.l	#3,d0
		ror.l	#3,d1
		or.l	d1,d0
		tst.w	d3
		beq.b	.store
		neg.l	d0
.store		move.l	d0,(a0)
		lea	(64,a0),a0
		dbf	d2,.scale
		move.w	(4,a6),-(a7)
		move.w	(2,a6),-(a7)
		move.w	(a6),-(a7)
		jsr	(a3)
		addq.l	#6,a7
		move.l	d0,(16,a7)	;retain native return value (gun arc acceptance)
		moveq	#0,d0
		move.w	(14,a7),d0
		lsl.w	#2,d0
		lea	(17378,a4),a0
		adda.w	d0,a0
		moveq	#2,d2
.restore	move.l	(a7)+,(a0)
		lea	(64,a0),a0
		dbf	d2,.restore
		move.w	(a7)+,(11700,a4)
		addq.l	#2,a7
		movem.l	(a7)+,d0-d7/a0-a3/a5-a6
		rts

dt_ai_lead_native
		link	a5,#-8
		movem.l	d4-d5,-(a7)
		move.l	(-31744,a4),a0
		adda.l	#$26e4e-$2eb4a,a0
		jmp	(a0)

dt_gunner_lead_native
		link	a5,#-16
		movem.l	d4-d5,-(a7)
		move.l	(-31744,a4),a0
		adda.l	#$1cfa0-$2eb4a,a0
		jmp	(a0)

dt_velocity_rate
		move.w	(dt_velocity_t,pc),d7
		bne.b	.done
		move.w	(11700,a4),d7
.done		rts

dt_velocity_t	dc.w	0

; FR-14: all four surface slots keep independent two-second deadlines.
dt_surface_ai
		movem.l	d0-d7/a0-a3/a5-a6,-(a7)
		bsr	dt_seconds
		subq.l	#1,d0
		move.l	d0,d7
		move.l	(-31744,a4),a3
		adda.l	#$21954-$2eb4a,a3
.scan		move.l	d7,d5
		moveq	#-1,d6
		moveq	#16,d4
		lea	(dt_ai_left+64,pc),a2
.object		lea	(13394,a4),a0
		tst.b	(a0,d4.w)
		beq.b	.next
		lea	(22706,a4),a0
		tst.b	(a0,d4.w)
		bne.b	.next
		cmp.l	(a2),d5
		bls.b	.next
		move.l	(a2),d5
		move.w	d4,d6
.next		addq.l	#4,a2
		addq.w	#1,d4
		cmp.w	#20,d4
		blo.b	.object
		lea	(dt_ai_left+64,pc),a0
		moveq	#3,d0
.decay		move.l	(a0),d1
		sub.l	d5,d1
		bcc.b	.store
		moveq	#0,d1
.store		move.l	d1,(a0)+
		dbf	d0,.decay
		sub.l	d5,d7
		tst.w	d6
		bmi.b	.done
		move.w	d6,d4
		move.w	d4,d0
		lsl.w	#2,d0
		lea	(dt_ai_left,pc),a2
		adda.w	d0,a2
		move.w	d4,(11708,a4)
		jsr	(a3)
		move.l	#$2000000,(a2)
		bra.b	.scan
.done		move.w	#16,(11708,a4)
		movem.l	(a7)+,d0-d7/a0-a3/a5-a6
		rts

; Script delays are decision counts, not rendering-frame counts. Every native
; call uses N<=20 (including the 10/6/3 skill table); N*6 fits the native byte.
dt_script_wait
		movem.l	d1/a0,-(a7)
		moveq	#1,d0
		move.w	(11710,a4),d1
		cmp.w	#16,d1
		bhs.b	.multiply
		lsl.w	#2,d1
		lea	(dt_ai_period,pc),a0
		move.l	(a0,d1.w),d1
		beq.b	.multiply
		cmp.l	#$2000000,d1
		bhs.b	.multiply
		moveq	#2,d0
		cmp.l	#$1000000,d1
		beq.b	.multiply
		moveq	#4,d0
		cmp.l	#$800000,d1
		beq.b	.multiply
		moveq	#6,d0
.multiply	mulu.w	(12,a7),d0
		movem.l	(a7)+,d1/a0
		rts

; Taxi action 16 is invoked per decision, not per movement update. Preserve
; its native reference-T=8 correction per opportunity instead of dividing by
; the unrelated outer update rate.
dt_taxi_left
		move.l	#1024,d0
		sub.w	d0,(a0)
		rts

dt_taxi_right
		move.l	#1024,d0
		add.w	d0,(a0)
		rts

; FR-15: signed fractional attitude rates. D4 is one of sixteen aircraft.
; Three channels: commanded roll, commanded pitch, falling/stalled pitch.
; D0.w signed rate/second; A0 fraction array. Return signed integer D0.w.
dt_att_rate
		movem.l d1-d3/a0,-(a7)
		move.w d0,d3
		tst.w d0
		bpl.b .positive
		neg.w d0
.positive	swap d0
		clr.w d0
		move.w (11700,a4),d2
		bsr dt_ldiv
		tst.w d3
		bpl.b .carry
		neg.l d0
.carry		move.w d4,d1
		add.w d1,d1
		add.w d1,a0
		moveq #0,d1
		move.w (a0),d1
		add.l d1,d0
		move.w d0,(a0)
		swap d0
		movem.l (a7)+,d1-d3/a0
		rts

dt_att_roll
		movem.l d0-d2/a0-a1,-(a7)
		move.w d4,d1
		lea (19278,a4),a0
		move.w #4096,d0
		cmp.b #1,(a0,d1.w)
		bne.b .rate
		move.w #16384,d0
.rate		add.w d1,d1
		lea (19294,a4),a0
		lea (19198,a4),a1
		move.w (a0,d1.w),d2
		sub.w (a1,d1.w),d2
		bpl.b .positive
		neg.w d0
.positive	lea (dt_att_rollfrac,pc),a0
		bsr dt_att_rate
		tst.w d2
		bpl.b .store
		neg.w d0
.store		move.w d0,(-46,a5)
		movem.l (a7)+,d0-d2/a0-a1
		add.l #$202ec-$202d0,(a7)
		rts

dt_att_roll_done
		move.b #2,(a0,d0.l)
		movem.l d0/a0,-(a7)
		lea (dt_att_rollfrac,pc),a0
		bra.b dt_att_clear

dt_att_pitch_done
		move.b #3,(a0,d0.l)
		movem.l d0/a0,-(a7)
		lea (dt_att_pitchfrac,pc),a0
dt_att_clear	move.w d4,d0
		add.w d0,d0
		clr.w (a0,d0.w)
		movem.l (a7)+,d0/a0
		rts

dt_att_pitch
		movem.l d0-d1/a0,-(a7)
		move.w d4,d1
		lea (19326,a4),a0
		cmp.b #1,(a0,d1.w)
		beq.b .down
		cmp.b #2,(a0,d1.w)
		bne.b .done
		move.w #5120,d0
		lea (dt_att_pitchfrac,pc),a0
		bsr dt_att_rate
		move.w d0,(-52,a5)
		bra.b .done
.down		move.w #-4096,d0
		lea (dt_att_pitchfrac,pc),a0
		bsr dt_att_rate
		neg.w d0
		move.w d0,(-50,a5)
.done		movem.l (a7)+,d0-d1/a0
		moveq #0,d0
		move.w d4,d0
		lea (19326,a4),a0
		rts

; A pole changes direction AND native pitch speed (4096 <-> 5120).
; Convert the overshoot to the new speed, so the portion of this same step
; after the crossing uses the new direction's rate. Reflect the full fraction.
dt_att_reflect
		movem.l d1-d3/a1,-(a7)
		lea (dt_att_pitchfrac,pc),a1
		move.w d4,d1
		add.w d1,d1
		move.w (a0,d0.l),d2
		swap d2
		move.w (a1,d1.w),d2
		neg.l d2
		lea (19326,a4),a1
		cmp.b #1,(a1,d4.w)
		bne.b .upper
; Lower pole: reflected overshoot is positive. New speed is 5/4 of old.
		move.l d2,d3
		lsr.l #2,d3
		add.l d3,d2
		bra.b .store
; Upper pole: reflected value is $80000000 minus positive overshoot.
.upper		move.l #$80000000,d3
		sub.l d2,d3
		move.l d0,-(a7)
		move.l d3,d0
		moveq #5,d2
		bsr dt_ldiv
		lsl.l #2,d0
		move.l #$80000000,d2
		sub.l d0,d2
		move.l (a7)+,d0
.store		lea (dt_att_pitchfrac,pc),a1
		move.w d2,(a1,d1.w)
		swap d2
		move.w d2,(a0,d0.l)
		movem.l (a7)+,d1-d3/a1
		moveq #0,d0
		rts

dt_att_bank
		move.l a0,-(a7)
		lea (dt_att_pitchfrac,pc),a0
		bsr dt_att_rate
		move.l (a7)+,a0
		rts

dt_att_stall
		move.l d0,-(a7)
		move.w d1,d0
		bsr dt_att_fall
		move.w d0,d1
		move.l (a7)+,d0
		rts

dt_att_fall
		move.l a0,-(a7)
		lea (dt_att_fallfrac,pc),a0
		bsr dt_att_rate
		move.l (a7)+,a0
		add.w d0,(a0)
		rts

dt_att_spin
		move.l a0,-(a7)
		lea (dt_att_rollfrac,pc),a0
		bsr dt_att_rate
		move.l (a7)+,a0
		add.w d0,(a0)
		rts

dt_att_reset
		movem.l d0/a0,-(a7)
		move.w d4,d0
		add.w d0,d0
		lea (dt_att_rollfrac,pc),a0
		clr.w (a0,d0.w)
		clr.w (32,a0,d0.w)
		clr.w (64,a0,d0.w)
		lea (dt_aifrac,pc),a0
		clr.w (a0,d0.w)
		lea (dt_recovery_frac,pc),a0
		clr.w (a0,d0.w)
		clr.w (32,a0,d0.w)
		lea (dt_ground_frac,pc),a0
		clr.w (a0,d0.w)
		movem.l (a7)+,d0/a0
		rts

dt_att_rollfrac dcb.w 16,0
dt_att_pitchfrac dcb.w 16,0
dt_att_fallfrac dcb.w 16,0

; Keep the two native pitch representations coherent through state changes.
dt_att_syncfall
		move.w (a0,d0.l),(a1,d1.l)
		movem.l d0-d1/a0,-(a7)
		move.w d4,d0
		add.w d0,d0
		lea (dt_att_pitchfrac,pc),a0
		move.w (32,a0,d0.w),(a0,d0.w)
		movem.l (a7)+,d0-d1/a0
		rts

dt_att_syncpitch
		move.w (a0,d0.l),(a1,d1.l)
		movem.l d0-d1/a0,-(a7)
		move.w d4,d0
		add.w d0,d0
		lea (dt_att_pitchfrac,pc),a0
		move.w (a0,d0.w),(32,a0,d0.w)
		movem.l (a7)+,d0-d1/a0
		rts

dt_att_fall_limit
		move.w #$8000,(a0,d0.l)
		movem.l d0/a0,-(a7)
		lea (dt_att_fallfrac,pc),a0
		bra dt_att_clear

dt_att_ground
		move.w #$4000,(a0,d0.l)
		bra dt_att_reset

; FR-16: player recovery uses the control clock (11698), as the native input
; routine does, rather than accelerated world time. Roll levels first; unused
; crossing time then levels pitch at half the roll speed. Both goals clamp.
dt_recovery
		movem.l d0-d6/a0-a1,-(a7)
		move.w (13318,a4),d1
		add.w d1,d1
		move.w (11698,a4),d2
		lea (19198,a4),a0
		lea (dt_recovery_frac,pc),a1
		add.w d1,a1
		moveq #0,d3
		move.w (a0,d1.w),d3
		beq.b .pitch_tick
		move.w d3,d6
		tst.w d3
		bpl.b .roll_abs
		neg.w d3
.roll_abs	swap d3
		clr.w d3
		move.l #$04000000,d0
		bsr dt_ldiv
		moveq #0,d5
		move.w (a1),d5
		add.l d5,d0
		cmp.l d3,d0
		bhs.b .roll_done
		move.w d0,(a1)
		swap d0
		tst.w d6
		bmi.b .roll_negative
		sub.w d0,(a0,d1.w)
		bra .done
.roll_negative	add.w d0,(a0,d1.w)
		bra .done
.roll_done	clr.w (a0,d1.w)
		clr.w (a1)
		sub.l d3,d0
		lsr.l #1,d0
		bra.b .pitch
.pitch_tick	clr.w (a1)
		move.l #$02000000,d0
		bsr dt_ldiv
.pitch		lea (22402,a4),a0
		cmp.w #24576,(a0,d1.w)
		blo.b .done
		lea (18830,a4),a0
		move.w (a0,d1.w),d3
		sub.w #16384,d3
		move.w d3,d6
; Native pitch is unsigned: values above 16384 approach from above even when
; their difference has bit 15 set (e.g. an inverted player attitude).
		cmp.w #16384,(a0,d1.w)
		bhs.b .pitch_abs
		neg.w d3
.pitch_abs	swap d3
		clr.w d3
		moveq #0,d5
		move.w (32,a1),d5
		add.l d5,d0
		cmp.l d3,d0
		bhs.b .pitch_done
		move.w d0,(32,a1)
		swap d0
		cmp.w #16384,(a0,d1.w)
		blo.b .pitch_below
		sub.w d0,(a0,d1.w)
		bra.b .done
.pitch_below	add.w d0,(a0,d1.w)
		bra.b .done
.pitch_done	move.w #16384,(a0,d1.w)
		clr.w (32,a1)
.done		movem.l (a7)+,d0-d6/a0-a1
		add.l #$14ac2-$149b6,(a7)
		rts

dt_recovery_frac dcb.w 32,0

; FR-17: ground steering is stick / (4 * control T), with signed carry.
; Native state-2 and nonzero-throttle gates precede this hook.
dt_ground_steer
		movem.l d0-d3/a0,-(a7)
		move.w (11968,a4),d0
		move.w d0,d3
		bsr dt_abs
		move.w #16384,d2
		bsr dt_rate16
		tst.w d3
		bpl.b .carry
		neg.l d0
.carry		lea (dt_ground_frac,pc),a0
		add.w d1,a0
		moveq #0,d2
		move.w (a0),d2
		add.l d2,d0
		move.w d0,(a0)
		swap d0
		move.w d0,(30676,a4)
		lea (18162,a4),a0
		add.w d0,(a0,d1.w)
		movem.l (a7)+,d0-d3/a0
		add.l #$146ac-$14680,(a7)
		rts

dt_ground_frac dcb.w 16,0
