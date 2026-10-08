;*---------------------------------------------------------------------------
; Always on: one-shot sounds end when their sample does (data/bob v1.1).  A bug fix
; of the original, applied without an option.
;
; A sound descriptor (started at bob:2771e) has a start segment and a repeat
; segment.  The VBL sound routine (bob:2b66c) writes the start segment to AUDxLC/
; AUDxLEN and enables DMA, and in the next field writes the repeat segment, which
; the channel plays once the start segment ends.  One-shots (explosions, splashes:
; ids 1002-1008, 1010, 1012, 1013 in the bank) have a repeat of 0, so the routine
; wrote nothing and the hardware played the sample again from its start until the
; envelope, counted in fields, switched the channel off (e.g. 1002: a 2.2 s sample
; against a sustain of 120 fields).  An empty repeat segment now queues a word of
; silence instead.
;---------------------------------------------------------------------------

; < A2: resload, D7: seglist (BPTR)
sound_patch	moveq	#2,d0
		move.l	#MEMF_CHIP|MEMF_CLEAR,d1
		move.l	a6,-(a7)
		move.l	(4).w,a6
		jsr	(_LVOAllocMem,a6)
		move.l	(a7)+,a6
		lea	(snd_null,pc),a0
		move.l	d0,(a0)
		beq.b	.done
		lea	(_pl_sound,pc),a0
		move.l	d7,a1
		jsr	(resload_PatchSeg,a2)
.done		rts

_pl_sound	PL_START
		PL_PS	$2b6a4,snd_repeat	;tst.l (a0); beq.s 2b6f4; asl.l #1,d0
		PL_END

; < A0: the segment to queue (pointer, its length in the parallel table),
;   D0: channel * 8; continues at bob:2b6aa with D0 = channel * 16
snd_repeat	asl.l	#1,d0
		tst.l	(a0)
		beq.b	.silence
		rts
.silence	lea	($dff0a0),a0		;AUD0LC
		add.l	d0,a0
		move.l	(snd_null,pc),(a0)
		move.w	#1,(4,a0)		;AUDxLEN: one word
		add.l	#$2b6f4-$2b6aa,(a7)	;as the beq.s
		rts

snd_null	dc.l	0			;a silent word in chip memory
