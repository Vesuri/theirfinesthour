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
		move.l	(_custom5,pc),d0
		cmp.l	#10,d0
		beq.b	.replay
		cmp.l	#9,d0
		bne.b	.done
		lea	(_pl_guidance_probe,pc),a0
		move.l	d7,a1
		jsr	(resload_PatchSeg,a2)
		bra.b .done
.replay		lea (_pl_replay_probe,pc),a0
		move.l d7,a1
		jsr (resload_PatchSeg,a2)
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
		dc.w	tape_detail-tapes
		dc.w	tape_detail0-tapes
		dc.w	tape_accel-tapes
		dc.w	tape_fire-tapes
		dc.w	tape_burst-tapes
		dc.w	tape_training-tapes
		dc.w tape_training-tapes
tapes_end

; 1: mouse calibration: from field 600, one count right and down every field
tape_calibrate	dc.w	1
		dc.b	0,0,0,0
		dc.w	600
		dc.b	1,1,0,0
		dc.w	-1

; 2: main menu (bounds set at field 2090, pointer at 160,40) -> Fly Training Flight (159,52)
; ... -> training flight 4 (bomber with escort) -> GO FLIGHT.  The flight loop starts at
; field 7603 on the 68030/50 (improved frame rate) and 8244 on the A500-eq.
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

; 4: tape 2, then in flight Ctrl+G twice (ground detail 11196(a4) cycles 0-1-2: from the
; 68030's boot level 2 to level 1, the A500's).  Key bytes are decoded (bit 7 = down):
; Ctrl $63, G $24; any key-up byte clears the qualifier.  For the 68030/50 (flight from 7603).
tape_detail	TO_FLIGHT
		dc.w	7900
		dc.b	0,0,0,$e3
		dc.w	7903
		dc.b	0,0,0,$a4
		dc.w	7906
		dc.b	0,0,0,$24
		dc.w	7909
		dc.b	0,0,0,$e3
		dc.w	7912
		dc.b	0,0,0,$a4
		dc.w	7915
		dc.b	0,0,0,$24
		dc.w	7918
		dc.b	0,0,0,0
		dc.w	-1

; 5: as 4 with one press: the 68030's level 2 to level 0
tape_detail0	TO_FLIGHT
		dc.w	7900
		dc.b	0,0,0,$e3
		dc.w	7903
		dc.b	0,0,0,$a4
		dc.w	7906
		dc.b	0,0,0,$24
		dc.w	7909
		dc.b	0,0,0,0
		dc.w	-1

; 6: tape 2, then in flight T (time acceleration, bob:13cf2) at 8800 and again at 9300
; (back to normal).  T is rawkey $14.  Flight starts at 8244 on the A500-eq, 7603 on
; the 68030/50.
tape_accel	TO_FLIGHT
		dc.w	8800
		dc.b	0,0,0,$94
		dc.w	8803
		dc.b	0,0,0,$14
		dc.w	8806
		dc.b	0,0,0,0
		dc.w	9300
		dc.b	0,0,0,$94
		dc.w	9303
		dc.b	0,0,0,$14
		dc.w	9306
		dc.b	0,0,0,0
		dc.w	-1

; 7: tape 2, then the fire button (left mouse) in flight from tape field 8600 to 8606
; (gun sounds, one-shots in the bank)
tape_fire	TO_FLIGHT
		dc.w	8600
		dc.b	0,0,2,0
		dc.w	8606
		dc.b	0,0,0,0
		dc.w	-1

; 8: tape 2, then the fire button held in flight from tape field 7800 to 8100 (in flight on
; every machine): the guns' rate of fire
tape_burst	TO_FLIGHT
		dc.w	7800
		dc.b	0,0,2,0
		dc.w	8100
		dc.b	0,0,0,0
		dc.w	-1
	EVEN

; Tape 9: training input plus one controlled guided bomb in the live mission.
; All stimulus executes in the emulated CPU; the Barto debugger cannot write.
_pl_guidance_probe PL_START
		PL_PS	$12968,probe_guidance_loop
		PL_NOP	$1296e,2
		PL_PS	$1ff5c,probe_guidance_turn
		PL_P	$1df1e,probe_guidance_impact
		PL_END

probe_guidance_loop
		movem.l	d0-d7/a0-a3/a5-a6,-(a7)
		lea	(probe_guidance_frames,pc),a0
		addq.w	#1,(a0)
		cmp.w	#64,(a0)
		bne	probe_guidance_run
		move.w	(13318,a4),d4
		lea	(13394,a4),a0
		moveq	#0,d0
		move.b	(a0,d4.w),d0
		move.w	d0,-(a7)
		move.b	#4,(a0,d4.w)
		lea	(23826,a4),a0
		move.b	(a0,d4.w),d0
		move.w	d0,-(a7)
		move.b	#8,(a0,d4.w)
		lea	(23842,a4),a0
		move.b	(a0,d4.w),d0
		move.w	d0,-(a7)
		move.b	#16,(a0,d4.w)
		move.w	#1,-(a7)
		move.w	d4,-(a7)
		move.l	(-31744,a4),a0
		adda.l	#$1d280-$2eb4a,a0
		jsr	(a0)
		addq.w	#4,a7
		lea	(23842,a4),a0
		move.w	(a7)+,d0
		move.b	d0,(a0,d4.w)
		lea	(23826,a4),a0
		move.w	(a7)+,d0
		move.b	d0,(a0,d4.w)
		lea	(13394,a4),a0
		move.w	(a7)+,d0
		move.b	d0,(a0,d4.w)
		move.w	(30720,a4),d0
		lea	(probe_guidance_slot,pc),a0
		move.w	d0,(a0)
		cmp.w	#20,d0
		blo.b	.failed
		cmp.w	#52,d0
		bhs.b	.failed
		move.w	d0,d1
		sub.w	#20,d1
		lea	(20766,a4),a0
		move.b	#1,(a0,d1.w)
		lsl.w	#2,d0
		lea	(15506,a4),a0
		move.l	#5000,(a0,d0.w)
		lea	(14290,a4),a0
		move.l	(a0,d0.w),d1
		add.l	#1000,d1
		lea	(16114,a4),a0
		move.l	d1,(a0,d0.w)
		lea	(14898,a4),a0
		move.l	(a0,d0.w),d1
		add.l	#5000,d1
		lea	(16322,a4),a0
		move.l	d1,(a0,d0.w)
		lea	(probe_guidance_state,pc),a0
		move.w	#1,(a0)
		bra.b	probe_guidance_run
.failed		lea	(probe_guidance_state,pc),a0
		move.w	#-1,(a0)
probe_guidance_failed
		nop
probe_guidance_run
		movem.l	(a7)+,d0-d7/a0-a3/a5-a6
		move.l	(a7),a0
		jsr	($12eaa-$1296e,a0)
		move.l	(a7),a0
		jsr	($12efc-$1296e,a0)
		addq.l	#2,(a7)
		rts

probe_guidance_turn
		movem.l	d0/a0,-(a7)
		cmp.w	(probe_guidance_slot,pc),d4
		bne.b	.done
		move.w	d4,d0
		lsl.w	#2,d0
		lea	(15506,a4),a0
		move.l	(a0,d0.w),d0
		lea	(probe_guidance_altitude,pc),a0
		move.l	d0,(a0)
		lea	(probe_guidance_state,pc),a0
		move.w	#2,(a0)
.done		movem.l	(a7)+,d0/a0
		move.b	#2,(a0,d1.l)
		rts

probe_guidance_impact
		movem.l	d0/a0,-(a7)
		move.w	(12,a7),d0
		cmp.w	(probe_guidance_slot,pc),d0
		bne.b	probe_guidance_impact_done
		lea	(probe_guidance_state,pc),a0
		move.w	#3,(a0)
probe_guidance_observed
		nop
probe_guidance_impact_done		movem.l	(a7)+,d0/a0
		link	a5,#-6
		move.l	d4,-(a7)
		move.l	(-31744,a4),a0
		adda.l	#$1df24-$2eb4a,a0
		jmp	(a0)

probe_guidance_frames dc.w 0
probe_guidance_slot dc.w -1
probe_guidance_state dc.w 0
probe_guidance_altitude dc.l 0

; Tape 10: record 21 live steps, replay them with another current T, compare
; all object positions/classes and restore the live flight snapshot.
_pl_replay_probe PL_START
		PL_PS $12968,probe_replay_loop
		PL_NOP $1296e,2
		PL_END
probe_replay_loop
		movem.l d0-d7/a0-a3/a5-a6,-(a7)
		lea (probe_replay_frames,pc),a0
		addq.w #1,(a0)
		cmp.w #64,(a0)
		bne.b .snapshot
		clr.w (25850,a4)
		move.w #1,(30696,a4)
		bra probe_replay_run
.snapshot	cmp.w #65,(a0)
		bne.b .replay
		move.w #1,-(a7)
		move.l (13016,a4),-(a7)
		jsr (-32598,a4)
		addq.w #6,a7
		move.w (-7828,a4),(25852,a4)
		bra probe_replay_run
.replay		cmp.w #86,(a0)
		bne probe_replay_run
		clr.w (30696,a4)
		move.w #21,(25850,a4)
		bsr probe_replay_hash
		lea (probe_replay_expected,pc),a0
		move.l d0,(a0)
		clr.w -(a7)
		move.l (13020,a4),-(a7)
		jsr (-32598,a4)
		addq.w #6,a7
		move.l (-32380,a4),a0
		lea ($16a9e-$11ea2,a0),a0
		jsr (a0)
		move.w #1,(26004,a4)
		moveq #20,d7
.steps		move.w #17,(11698,a4)
		move.l d7,-(a7)
		bsr replay_step
		move.l (a7)+,d7
		dbf d7,.steps
		bsr probe_replay_hash
		lea (probe_replay_actual,pc),a0
		move.l d0,(a0)
		clr.w -(a7)
		move.l (13020,a4),-(a7)
		jsr (-32592,a4)
		addq.w #6,a7
		clr.w (26004,a4)
		lea (probe_replay_state,pc),a0
		move.w #1,(a0)
		move.l (probe_replay_expected,pc),d0
		cmp.l (probe_replay_actual,pc),d0
		beq.b probe_replay_observed
		move.w #-1,(a0)
probe_replay_observed
		nop
probe_replay_run		movem.l (a7)+,d0-d7/a0-a3/a5-a6
		move.l (a7),a0
		jsr ($12eaa-$1296e,a0)
		move.l (a7),a0
		jsr ($12efc-$1296e,a0)
		addq.l #2,(a7)
		rts
probe_replay_hash
		moveq #0,d0
		lea (13394,a4),a0
		move.w #320-1,d1
.types		rol.l #1,d0
		move.b (a0)+,d2
		eor.b d2,d0
		dbf d1,.types
		lea (14290,a4),a0
		move.w #1824-1,d1
.xyz		rol.l #1,d0
		move.b (a0)+,d2
		eor.b d2,d0
		dbf d1,.xyz
		rts
probe_replay_frames dc.w 0
probe_replay_state dc.w 0
probe_replay_expected dc.l 0
probe_replay_actual dc.l 0
