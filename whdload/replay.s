; FR-22 private simulation state. Keep this manifest complete as new timing
; state is introduced; replay_check.py checks coverage against timing.s.
; Snapshot buffers contain values, never live native pointers.
REPLAY_PRIVATE_BYTES = 3288
REPLAY_EXTRA_BYTES = 50
REPLAY_SNAPSHOT_BYTES = REPLAY_PRIVATE_BYTES+REPLAY_EXTRA_BYTES

; A0 = buffer, D0 = 0 save / 1 restore. All registers preserved.
replay_state_copy
		movem.l d0-d4/a0-a3,-(a7)
		move.l d0,d4
		move.l a0,a1
		lea (replay_state_table,pc),a2
.next		move.w (a2)+,d0
		beq.b .extra
		lea (replay_state_table,pc),a0
		adda.w d0,a0
		move.w (a2)+,d1
		bsr.b .bytes
		bra.b .next
.extra		lea (replay_extra_table,pc),a2
.more		move.w (a2)+,d0
		beq.b .done
		lea (a4,d0.w),a0
		move.w (a2)+,d1
		bsr.b .bytes
		bra.b .more
.done		movem.l (a7)+,d0-d4/a0-a3
		rts
.bytes		subq.w #1,d1
		tst.w d4
		bne.b .restore
.save		move.b (a0)+,(a1)+
		dbf d1,.save
		rts
.restore	move.b (a1)+,(a0)+
		dbf d1,.restore
		rts

replay_state_table
		dc.w dt_debris_time-replay_state_table,48
		dc.w dt_debris_grav-replay_state_table,24
		dc.w dt_bomb_active-replay_state_table,2
		dc.w dt_bomb_time-replay_state_table,128
		dc.w dt_mouse_axes-replay_state_table,4
		dc.w dt_mouse_shift-replay_state_table,2
		dc.w dt_mdx-replay_state_table,2
		dc.w dt_mdy-replay_state_table,2
		dc.w dt_boot-replay_state_table,2
		dc.w dt_last-replay_state_table,2
		dc.w dt_live-replay_state_table,2
		dc.w dt_err-replay_state_table,2
		dc.w dt_avg-replay_state_table,2
		dc.w dt_hz-replay_state_table,2
		dc.w dt_len-replay_state_table,10
		dc.w dt_rfrac-replay_state_table,96
		dc.w dt_frac-replay_state_table,912
		dc.w dt_aifrac-replay_state_table,304
		dc.w dt_group_left-replay_state_table,4
		dc.w dt_effect_time-replay_state_table,4
		dc.w dt_world_time-replay_state_table,4
		dc.w dt_shot_left-replay_state_table,192
		dc.w dt_shot_pending-replay_state_table,48
		dc.w dt_flak_left-replay_state_table,48
		dc.w dt_flak_generation-replay_state_table,48
		dc.w dt_plane_ids-replay_state_table,64
		dc.w dt_gun_left-replay_state_table,320
		dc.w dt_gun_requests-replay_state_table,80
		dc.w dt_salvo_active-replay_state_table,2
		dc.w dt_salvo_left-replay_state_table,64
		dc.w dt_bomb_batch-replay_state_table,2
		dc.w dt_bomb_batch_time-replay_state_table,4
		dc.w dt_guidance_ticks-replay_state_table,2
		dc.w dt_air_damage_left-replay_state_table,4
		dc.w dt_surface_damage_left-replay_state_table,4
		dc.w dt_ai_period-replay_state_table,64
		dc.w dt_ai_left-replay_state_table,80
		dc.w dt_ai_restart-replay_state_table,20
		dc.w dt_player_ai_left-replay_state_table,4
		dc.w dt_velocity_t-replay_state_table,2
		dc.w dt_att_rollfrac-replay_state_table,32
		dc.w dt_att_pitchfrac-replay_state_table,32
		dc.w dt_att_fallfrac-replay_state_table,32
		dc.w dt_recovery_frac-replay_state_table,64
		dc.w dt_ground_frac-replay_state_table,32
		dc.w dt_drift_frac-replay_state_table,96
		dc.w dt_contact_valid-replay_state_table,2
		dc.w dt_contact_ship_active-replay_state_table,2
		dc.w dt_contact_angles-replay_state_table,96
		dc.w dt_contact_ids-replay_state_table,64
		dc.w dt_contact_ship_types-replay_state_table,4
		dc.w dt_contact_ship_start-replay_state_table,64
		dc.w dt_contact_ship_end-replay_state_table,64
		dc.w dt_wait_left-replay_state_table,16
		dc.w dt_message_left-replay_state_table,4
		dc.w dt_message_viewfield-replay_state_table,2
		dc.w dt_fuel_frac-replay_state_table,32
		dc.w dt_key_memory-replay_state_table,2
		dc.w dt_ui_left-replay_state_table,2
		dc.w dt_field_phase-replay_state_table,2
		dc.w dt_field_due-replay_state_table,2
		dc.w dt_gunner_state-replay_state_table,10
		dc.w dt_cam_clock-replay_state_table,4
		dc.w dt_cam_elapsed-replay_state_table,4
		dc.w dt_cam_frac-replay_state_table,10
		dc.w dt_cam_wait-replay_state_table,4
		dc.w 0
; Missing from the native 195-field snapshot: RNG, mission/message state,
; transition reminders and player/view aiming coordinates.
replay_extra_table
		dc.w -7828,2,11214,6,30640,8,11668,30,11210,1,11203,2,11205,1
		dc.w 0

; Two independent snapshot companions: movie start and live-flight return.
replay_saved
		movem.l (a7)+,d4-d5
		unlk a5
		movem.l d0-d1/a0,-(a7)
		move.l (16,a7),d1
		sub.l #12213,d1	;native copy advanced its buffer argument
		cmp.l (13016,a4),d1
		beq.b .movie
		cmp.l (13020,a4),d1
		bne.b .done
		lea (replay_return_state,pc),a0
		bra.b .copy
.movie		lea (replay_movie_state,pc),a0
.copy		moveq #0,d0
		bsr replay_state_copy
.done		movem.l (a7)+,d0-d1/a0
		rts

replay_restored
		movem.l (a7)+,d4-d5
		unlk a5
		movem.l d0-d1/a0,-(a7)
		move.l (16,a7),d1
		sub.l #12213,d1	;native copy advanced its buffer argument
		cmp.l (13016,a4),d1
		beq.b .movie
		cmp.l (13020,a4),d1
		bne.b .done
		lea (replay_return_state,pc),a0
		bra.b .copy
.movie		move.w (replay_legacy,pc),d0
		beq.b .enhanced
		bsr replay_legacy_reset
		bra.b .done
.enhanced	lea (replay_movie_state,pc),a0
.copy		move.w (dt_hz,pc),-(a7)
		move.w (dt_boot,pc),-(a7)
		move.w (dt_mouse_shift,pc),-(a7)
		moveq #1,d0
		bsr replay_state_copy
		lea (dt_mouse_shift,pc),a0
		move.w (a7)+,(a0)
		lea (dt_boot,pc),a0
		move.w (a7)+,(a0)
		lea (dt_hz,pc),a0
		move.w (a7)+,(a0)
; The restored field counter is not a wall-clock sampling anchor.
		lea (dt_live,pc),a0
		clr.w (a0)
.done		movem.l (a7)+,d0-d1/a0
		rts

REPLAY_FRAMES = 7680
REPLAY_SECONDS = 128
REPLAY_INPUT_BYTES = REPLAY_FRAMES*8
REPLAY_META_BYTES = REPLAY_FRAMES*8

; Called in place of the recording body, after native input sampling.
replay_record
		movem.l d0-d3/a0-a2,-(a7)
		moveq #0,d3
		move.w (25850,a4),d3
		cmp.w #REPLAY_FRAMES,d3
		bhs .full
		lea (replay_storage,pc),a0
		move.l d3,d0
		lsl.l #3,d0
		adda.l d0,a0
		move.l (11966,a4),(a0)+
		move.l (11970,a4),(a0)+
		move.l a0,(13012,a4)
		adda.l #REPLAY_INPUT_BYTES-8,a0
		move.w (11698,a4),(a0)+
		move.w (11700,a4),(a0)+
		move.w (11702,a4),(a0)+
		move.w (-7828,a4),(a0)+
		lea (replay_elapsed,pc),a1
		tst.w d3
		bne.b .age
		clr.l (a1)
		lea (replay_legacy,pc),a0
		clr.w (a0)
.age		move.w (11698,a4),d2
		moveq #0,d0
		move.w d2,d0
		subq.l #1,d0
		add.l #$1000000,d0
		bsr dt_ldiv
		add.l d0,(a1)
		addq.w #1,(25850,a4)
		cmp.l #REPLAY_SECONDS*$1000000,(a1)
		bhs.b .full
		cmp.w #REPLAY_FRAMES,(25850,a4)
		blo.b .done
.full		clr.w (30696,a4)
		move.w #18,-(a7)
		jsr (-32244,a4)
		addq.w #2,a7
.done		movem.l (a7)+,d0-d3/a0-a2
		unlk a5
		rts

; Rewind already restored native + private snapshot. Restore stream pointer.
replay_rewind
		move.l a0,-(a7)
		lea (replay_storage,pc),a0
		move.l a0,(13012,a4)
		lea (replay_index,pc),a0
		clr.w (a0)
		lea (replay_pace,pc),a0
		clr.l (a0)
		clr.l (4,a0)
		move.l (a7)+,a0
		rts

; Consume one complete recorded input/timestep pair. Callers check remaining.
replay_read
		movem.l d0-d1/a0-a1,-(a7)
		lea (replay_index,pc),a1
		moveq #0,d0
		move.w (a1),d0
		cmp.w #REPLAY_FRAMES,d0
		bhs.b .done
		addq.w #1,(a1)
		lsl.l #3,d0
		lea (replay_storage,pc),a0
		adda.l d0,a0
		move.l (a0)+,(11966,a4)
		move.l (a0)+,(11970,a4)
		move.l a0,(13012,a4)
		move.w (replay_legacy,pc),d1
		bne.b .done
		adda.l #REPLAY_INPUT_BYTES-8,a0
		move.w (a0)+,(11698,a4)
		move.w (a0)+,(11700,a4)
		move.w (a0)+,(11702,a4)
		move.w (a0)+,(-7828,a4)
.done		movem.l (a7)+,d0-d1/a0-a1
		rts

replay_read_continuous
		movem.l d0-d7/a0-a3,-(a7)
		lea (replay_pace,pc),a2
		move.w (-8010,a4),d0
		move.w (a2),d1
		move.w d0,(a2)
		cmp.w #1,(30656,a4)
		bne.b .paused
		tst.w (2,a2)
		bne.b .elapsed
		move.w #1,(2,a2)
		bra.b .done
.paused		clr.w (2,a2)
		clr.l (4,a2)
		bra.b .done
.elapsed		sub.w d1,d0
		cmp.w #DT_STALL,d0
		bhi.b .paused
		and.l #$ffff,d0
		swap d0
		lsl.l #8,d0
		move.w (dt_hz,pc),d2
		moveq #0,d1
		move.w d2,d1
		subq.l #1,d1
		add.l d1,d0
		bsr dt_ldiv
		add.l d0,(4,a2)
.next		tst.w (30728,a4)
		beq.b .paused
		move.w (11698,a4),d2
		move.w (replay_legacy,pc),d0
		bne.b .period
		moveq #0,d0
		move.w (replay_index,pc),d0
		lsl.l #3,d0
		lea (replay_storage,pc),a0
		adda.l #REPLAY_INPUT_BYTES,a0
		move.w (a0,d0.l),d2
.period		move.l #$1000000,d0
		bsr dt_ldiv
		cmp.l (4,a2),d0
		bhi.b .done
		sub.l d0,(4,a2)
		move.l a2,-(a7)
		bsr replay_step
		move.l (a7)+,a2
		bra.b .next
.done		movem.l (a7)+,d0-d7/a0-a3
		move.l (-32380,a4),a0
		adda.l #$15fba-$11ea2,a0
		jmp (a0)

replay_skip_second
		movem.l d0-d7/a0-a3,-(a7)
		move.w (12058,a4),-(a7)
		move.b #1,(12059,a4)
		moveq #0,d7
.next		tst.w (30728,a4)
		beq.b .done
		move.l d7,-(a7)
		bsr replay_step
		bsr dt_seconds
		move.l (a7)+,d7
		add.l d0,d7
		cmp.l #$1000000,d7
		blo.b .next
.done		move.w (a7)+,(12058,a4)
		movem.l (a7)+,d0-d7/a0-a3
		move.l (-32380,a4),a0
		adda.l #$167aa-$11ea2,a0
		jmp (a0)

; Single-step and fast-forward share the same complete-step path, including
; the final sample. Native continuous playback skipped its last world update.
replay_single
		link a5,#0
		bsr replay_step
		move.w #64,-(a7)
		move.w #17,-(a7)
		jsr (-32532,a4)
		addq.w #4,a7
		unlk a5
		rts

replay_step
		tst.w (30728,a4)
		beq.b .done
		bsr replay_read
; The live loop services reports/transitions before sampling the next input.
; The initial snapshot already includes that first service opportunity.
		move.w (replay_index,pc),d0
		cmp.w #1,d0
		beq.b .world
		move.w (26004,a4),-(a7)
		move.w (-7828,a4),-(a7)
		clr.w (26004,a4)
		move.w #1,-(a7)
		move.l (-32380,a4),a0
		lea ($12984-$11ea2,a0),a0
		jsr (a0)
		addq.w #2,a7
		move.l (-32380,a4),a0
		lea ($12dba-$11ea2,a0),a0
		jsr (a0)
		move.w (a7)+,(-7828,a4)
		move.w (a7)+,(26004,a4)
.world		lea (replay_running,pc),a0
		move.w #1,(a0)
		move.l (-32380,a4),a0
		lea ($12eaa-$11ea2,a0),a0
		jsr (a0)
		lea (replay_running,pc),a0
		clr.w (a0)
		subq.w #1,(30728,a4)
		bne.b .done
		clr.w (30656,a4)
		move.w #33,-(a7)
		jsr (-32244,a4)
		addq.w #2,a7
.done		rts

; File extensions follow the unchanged native prefix and snapshot. A zero count
; in that prefix makes enhanced movies harmless (empty) to the original loader.
replay_save_prefix
		lea (replay_storage,pc),a0
		move.l a0,(-4,a5)
		rts
replay_load_prefix
		lea (replay_storage,pc),a0
		move.l a0,(-6,a5)
		rts

replay_save_extension
		movem.l d4-d7/a2-a3,-(a7)
		lea (replay_header,pc),a0
		move.l #$54464833,(a0)
		move.w #1,(4,a0)
		move.w (25850,a4),(6,a0)
		move.l (replay_elapsed,pc),(8,a0)
		move.w #REPLAY_SNAPSHOT_BYTES,(12,a0)
		move.w (replay_legacy,pc),(14,a0)
		move.l a0,a2
		moveq #16,d6
		bsr replay_write_block
		tst.w d0
		beq .failed
		lea (replay_movie_state,pc),a2
		move.l #REPLAY_SNAPSHOT_BYTES,d6
		bsr replay_write_block
		tst.w d0
		beq .failed
		lea (replay_storage,pc),a2
		moveq #0,d6
		move.w (25850,a4),d6
		lsl.l #3,d6
		bsr replay_write_block
		tst.w d0
		beq .failed
		lea (replay_storage,pc),a2
		adda.l #REPLAY_INPUT_BYTES,a2
		moveq #0,d6
		move.w (25850,a4),d6
		lsl.l #3,d6
		bsr replay_write_block
		tst.w d0
		beq .failed
		bsr replay_close
		movem.l (a7)+,d4-d7/a2-a3
		move.l (-32380,a4),a0
		adda.l #$1ba0-$11ea2,a0
		jmp (a0)
.failed		bsr replay_close
		movem.l (a7)+,d4-d7/a2-a3
		move.l (-32380,a4),a0
		adda.l #$1afa-$11ea2,a0
		jmp (a0)

replay_load_extension
		movem.l d4-d7/a2-a3,-(a7)
		lea (replay_header,pc),a2
		moveq #16,d6
		bsr replay_read_block
		tst.w d0
		beq .legacy
		lea (replay_header,pc),a0
		cmp.l #$54464833,(a0)
		bne .bad
		cmp.w #1,(4,a0)
		bne .bad
		cmp.w #REPLAY_FRAMES,(6,a0)
		bhi .bad
		cmp.w #REPLAY_SNAPSHOT_BYTES,(12,a0)
		bne .bad
		cmp.w #1,(14,a0)
		bhi .bad
		lea (replay_movie_state,pc),a2
		move.l #REPLAY_SNAPSHOT_BYTES,d6
		bsr replay_read_block
		tst.w d0
		beq .bad
		lea (replay_storage,pc),a2
		moveq #0,d6
		move.w (replay_header+6,pc),d6
		lsl.l #3,d6
		bsr replay_read_block
		tst.w d0
		beq .bad
		lea (replay_storage,pc),a2
		adda.l #REPLAY_INPUT_BYTES,a2
		moveq #0,d6
		move.w (replay_header+6,pc),d6
		lsl.l #3,d6
		bsr replay_read_block
		tst.w d0
		beq .bad
		move.w (replay_header+14,pc),d0
		bne.b .accepted
; Validate recorded divisors before any input can reach a division instruction.
		lea (replay_storage,pc),a0
		adda.l #REPLAY_INPUT_BYTES,a0
		move.w (replay_header+6,pc),d6
		beq.b .accepted
		subq.w #1,d6
.check		move.w (a0),d0
		beq .bad
		cmp.w #60,d0
		bhi .bad
		move.w (2,a0),d0
		beq .bad
		cmp.w #60,d0
		bhi .bad
		addq.l #8,a0
		dbf d6,.check
.accepted	move.w (replay_header+6,pc),(25850,a4)
		lea (replay_elapsed,pc),a0
		move.l (replay_header+8,pc),(a0)
		lea (replay_legacy,pc),a0
		move.w (replay_header+14,pc),(a0)
		bra.b .ok
.legacy		cmp.w #1023,(25850,a4)
		bhi.b .bad
		tst.w (25850,a4)
		beq.b .bad
; Old movies have no private state or per-frame T. Preserve their native input
; stream and constant saved clock; no claim of reconstructing missing history.
		lea (replay_legacy,pc),a0
		move.w #1,(a0)
.ok		moveq #1,d7
		bra.b .close
.bad		clr.w (25850,a4)
		moveq #0,d7
.close		bsr replay_close
		move.l d7,d0
		movem.l (a7)+,d4-d7/a2-a3
		move.l (-32380,a4),a0
		adda.l #$1ca6-$11ea2,a0
		jmp (a0)

; A2 buffer, D6 byte count. D0=success. Use native buffered file operations.
replay_write_block
		move.l (-32380,a4),a3
		adda.l #$3418-$11ea2,a3
.loop		tst.l d6
		beq.b .status
		move.l (25560,a4),-(a7)
		moveq #0,d0
		move.b (a2)+,d0
		move.w d0,-(a7)
		jsr (a3)
		addq.w #6,a7
		cmp.w #-1,d0
		beq.b .bad
		subq.l #1,d6
		bra.b .loop
.status		move.l (25560,a4),-(a7)
		move.l (-32380,a4),a0
		adda.l #$357a-$11ea2,a0
		jsr (a0)
		addq.w #4,a7
		tst.w d0
		bne.b .bad
		moveq #1,d0
		rts
.bad		moveq #0,d0
		rts
replay_read_block
		move.l (-32380,a4),a3
		adda.l #$33f8-$11ea2,a3
.loop		tst.l d6
		beq.b .ok
		move.l (25560,a4),-(a7)
		jsr (a3)
		addq.w #4,a7
		cmp.w #-1,d0
		beq.b .bad
		move.b d0,(a2)+
		subq.l #1,d6
		bra.b .loop
.ok		moveq #1,d0
		rts
.bad		moveq #0,d0
		rts
replay_close
		move.l (25560,a4),-(a7)
		move.l (-32380,a4),a0
		adda.l #$33c8-$11ea2,a0
		jsr (a0)
		addq.w #4,a7
		rts

replay_legacy_reset
		movem.l d0-d4/a0-a2,-(a7)
		move.w (dt_mouse_shift,pc),d2
		move.w (dt_hz,pc),d3
		move.w (dt_boot,pc),d4
		lea (replay_state_table,pc),a2
.next		move.w (a2)+,d0
		beq.b .done
		lea (replay_state_table,pc),a0
		adda.w d0,a0
		move.w (a2)+,d1
		subq.w #1,d1
.clear		clr.b (a0)+
		dbf d1,.clear
		bra.b .next
.done		lea (dt_mouse_shift,pc),a0
		move.w d2,(a0)
		lea (dt_hz,pc),a0
		move.w d3,(a0)
		lea (dt_boot,pc),a0
		move.w d4,(a0)
		movem.l (a7)+,d0-d4/a0-a2
		rts

; Keep the existing capacity gauge, now based on elapsed recording time.
replay_gauge
		bsr.b replay_gauge_value
		move.l (-32380,a4),a0
		adda.l #$18c96-$11ea2,a0
		jmp (a0)
replay_gauge_update
		bsr.b replay_gauge_value
		move.l (-32380,a4),a0
		adda.l #$19742-$11ea2,a0
		jmp (a0)
replay_gauge_value
		move.w (replay_legacy,pc),d0
		beq.b .time
		moveq #0,d0
		move.w (25850,a4),d0
		bra.b .scale
.time		move.l (replay_elapsed,pc),d0
		lsr.l #8,d0
		lsr.l #8,d0
		lsr.l #5,d0
.scale		cmp.w #1023,d0
		bls.b .valid
		move.w #1023,d0
.valid		neg.w d0
		add.w #1023,d0
		move.w #1023,-(a7)
		move.w d0,-(a7)
		jsr (-31950,a4)
		addq.w #4,a7
		rts

; Allow recorded gunner input while retaining movie UI guards elsewhere.
replay_gunner_gate
		move.l d0,-(a7)
		move.w (replay_running,pc),d0
		bne.b .allow
		tst.w (26004,a4)
		beq.b .allow
		add.l #28,(4,a7)
.allow		move.l (a7)+,d0
		rts

replay_running dc.w 0
replay_pace dc.w 0,0
		dc.l 0
replay_header dcb.b 16,0
replay_legacy dc.w 0

replay_elapsed dc.l 0
replay_index dc.w 0
replay_movie_state dcb.b REPLAY_SNAPSHOT_BYTES,0
replay_return_state dcb.b REPLAY_SNAPSHOT_BYTES,0
		even
replay_storage dcb.b REPLAY_INPUT_BYTES+REPLAY_META_BYTES,0
