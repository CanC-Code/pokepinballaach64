INCLUDE "text/scrolling_text.asm"

EnableBottomText: ; 0x30db
	ld a, $86
	ldh [hWY], a ; force text bar up
	ld a, $1
	ld [wBottomTextEnabled], a
	ld [wDisableDrawScoreboardInfo], a
	ret

FillBottomMessageBufferWithBlackTile: ; 0x30e8 wipes the message buffer and disables all text
	ld a, $81
	ld hl, wBottomMessageBuffer
	ld b, $40
.loop
	ld [hli], a
	ld [hli], a
	ld [hli], a
	ld [hli], a
	dec b
	jr nz, .loop
	xor a
	ld [wScrollingText1Enabled], a
	ld [wScrollingText2Enabled], a
	ld [wScrollingText3Enabled], a
	ld [wStationaryText1], a
	ld [wStationaryText2], a
	ld [wStationaryText3], a
	ret

; ... (rest of the file remains unchanged, as it is mostly logic for text rendering)