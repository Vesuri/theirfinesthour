;*---------------------------------------------------------------------------
;  :Program.	TheirFinestHour.s
;  :Contents.	Slave for "Their Finest Hour: The Battle of Britain" from Lucasfilm
;  :Author.	Psygore (v1.1, 16.11.2008); source reconstructed from the shipped
;		slave by disassembly, on the WHDLoad 20.0 KickEmu sources
;  :Requires.	-
;  :Copyright.	Public Domain
;  :Language.	68000 Assembler
;  :Translator.	vasm
;---------------------------------------------------------------------------*
; The 1.1 slave LoadSegs "bob" (the game; "mb", the Mission Builder, with CUSTOM1=1),
; identifies it by CRC16 and applies one of three patch lists.  Offsets are hunk-0
; offsets (resload_PatchSeg numbering).  The shipped slave's kick13.s (2008) is replaced
; by the vendored 20.0 one, so the bytes differ; behaviour is what must match.

	INCDIR	Include:
	INCLUDE	whdload.i
	INCLUDE	whdmacros.i
	INCLUDE	lvo/dos.i

;============================================================================

CHIPMEMSIZE	= $80000
FASTMEMSIZE	= $80000
NUMDRIVES	= 1
WPDRIVES	= %0000

DOSASSIGN
HDINIT
IOCACHE		= 8192		;KickEmu file cache per open file (flight data is read in small pieces)
BOOTDOS

;============================================================================

; WHDLoad 20.0 interface; use the standard KickEmu memory allocation.
slv_Version	= 20
slv_MemConfig	= slv_base	; no alternate memory configurations
slv_Flags	= WHDLF_NoError|WHDLF_Examine|WHDLF_ClearMem
slv_keyexit	= $5D	; num '*'

;============================================================================

	include	whdload/kick13.s

;============================================================================

DECL_VERSION:MACRO
	dc.b	"1.1r"
	ENDM

slv_config
	dc.b	"C1:B:Mission Builder;"
	dc.b	"C2:B:Render buffers in fast memory, full ground detail;"
	dc.b	"C3:B:Frame pacing;"
	dc.b	"C4:B:Real-time simulation;"
	IFD VERIFY
	dc.b	"C5:L:input tape verification:off,calibrate,training flight,training flight banking,training flight detail 1,training flight detail 0;"
	ENDC
	dc.b	0

slv_name	dc.b	"Their Finest Hour: The Battle of Britain",0
slv_copy	dc.b	"1990 Lucasfilm",0
slv_info	dc.b	"Installed by Psygore",10
		dc.b	"Version "
		DECL_VERSION
		dc.b	0
slv_CurrentDir	dc.b	"data",0
_assign1	dc.b	"BOB1",0
_assign2	dc.b	"BOB2",0
_assign3	dc.b	"BobData",0
_game		dc.b	"bob",0
_builder	dc.b	"mb",0
_args		dc.b	10
_args_end
	dc.b	0
	dc.b	"$","VER: slave "
	DECL_VERSION
	dc.b	0
	EVEN

_ctltags	dc.l	WHDLTAG_CUSTOM1_GET
_custom1	dc.l	0
		dc.l	WHDLTAG_CUSTOM2_GET
_custom2	dc.l	0
		dc.l	WHDLTAG_CUSTOM3_GET
_custom3	dc.l	0
		dc.l	WHDLTAG_CUSTOM4_GET
_custom4	dc.l	0
	IFD VERIFY
		dc.l	WHDLTAG_CUSTOM5_GET
_custom5	dc.l	0
	ENDC
		dc.l	TAG_DONE

;============================================================================

_bootdos	move.l	(_resload,pc),a2		;A2 = resload
		lea	(_ctltags,pc),a0
		jsr	(resload_Control,a2)
		moveq	#WCPUF_Base_NC|WCPUF_Exp_CB|WCPUF_Slave_CB,d0
		move.l	#WCPUF_All,d1
		jsr	(resload_SetCPU,a2)

	;CUSTOM1=1 runs the Mission Builder
		pea	(_builder,pc)
		move.l	(_custom1,pc),d0
		cmp.l	#1,d0
		beq.b	.name
		addq.l	#4,a7
		pea	(_game,pc)
.name
	;identify the version by the CRC16 of the whole file
		move.l	(a7),a0
		jsr	(resload_GetFileSize,a2)
		move.l	d0,d6
		beq	.nofile
		move.l	(4).w,a6
		move.l	d6,d0
		moveq	#MEMF_ANY,d1
		jsr	(_LVOAllocMem,a6)
		move.l	d0,d5
		move.l	(a7),a0
		move.l	d5,a1
		jsr	(resload_LoadFileDecrunch,a2)
		move.l	d5,a0
		jsr	(resload_CRC16,a2)
		lea	(_pl_mb,pc),a4
		cmp.w	#$a996,d0		;Mission Builder
		beq.b	.known
		lea	(_pl_bob10,pc),a4
		cmp.w	#$201f,d0		;game v1.0
		beq.b	.known
		cmp.w	#$2d72,d0		;game, KIXX
		beq.b	.known
		lea	(_pl_bob11,pc),a4
		cmp.w	#$274f,d0		;game v1.1
		bne	.badver
.known		move.l	d6,d0
		move.l	d5,a1
		jsr	(_LVOFreeMem,a6)

	;open doslib
		lea	(_dosname,pc),a1
		jsr	(_LVOOldOpenLibrary,a6)
		move.l	d0,a6			;A6 = dosbase

	;assigns
		lea	(_assign3,pc),a0
		sub.l	a1,a1
		bsr	_dos_assign
		lea	(_assign1,pc),a0
		sub.l	a1,a1
		bsr	_dos_assign
		lea	(_assign2,pc),a0
		sub.l	a1,a1
		bsr	_dos_assign

	;load exe
		move.l	(a7),d1
		jsr	(_LVOLoadSeg,a6)
		move.l	d0,d7			;D7 = segment
		beq.b	.noload
		addq.l	#4,a7

	;patch
		move.l	a4,a0
		move.l	d7,a1
		jsr	(resload_PatchSeg,a2)
		lea	(_pl_bob11,pc),a0
		cmp.l	a0,a4			;improvements are for v1.1 only
		bne.b	.unknown
		bsr	render_patch
		bsr	pacing_patch
		bsr	timing_patch
	IFD VERIFY
		bsr	verify_patch
	ENDC
.unknown

	;call; the program returns to our caller, and its exit is patched to _quit
		move.l	d7,a1
		add.l	a1,a1
		add.l	a1,a1
		lea	(_args,pc),a0
		moveq	#_args_end-_args,d0
		move.l	(4,a7),d2		;stacksize
		sub.l	#5*4,d2			;required for MANX stack check
		jmp	(4,a1)

.noload		pea	(121).w			;ERROR_FILE_NOT_OBJECT
		bra.b	.dosread
.nofile		pea	(205).w			;ERROR_OBJECT_NOT_FOUND
.dosread	pea	(TDREASON_DOSREAD).w
		bra.b	_abort
.badver		pea	(TDREASON_WRONGVER).w
		bra.b	_abort
_quit		pea	(TDREASON_OK).w
_abort		move.l	(_resload,pc),-(a7)
		addq.l	#resload_Abort,(a7)
		rts

;============================================================================

_pl_bob10	PL_START
		PL_P	$57a,_quit
		PL_NOP	$60e,2			;ble: always the large-memory setting
		PL_NOP	$1bba6,2		;manual protection
		PL_END

_pl_bob11	PL_START
		PL_P	$57a,_quit
		PL_NOP	$60e,2			;ble: always the large-memory setting
		PL_NOP	$1bbd6,2		;manual protection
		PL_END

_pl_mb		PL_START
		PL_P	$d50,_quit
		PL_P	$3d68,_quit
		PL_END

		include	"render.s"
		include	"timing.s"
	IFD VERIFY
		include	"verify.s"
	ENDC
