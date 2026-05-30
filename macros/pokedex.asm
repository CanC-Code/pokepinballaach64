MACRO dex_number
	db (((\\1) / 100) % 10) + $30
	db (((\\1) / 10) % 10) + $30
	db ((\\1) % 10) + $30
	db "@"
ENDM

; \1 = feet
; \2 = inches
MACRO dex_height
	DEF feet_tens_digit = ((\\1) / 10) % 10
	IF feet_tens_digit == 0
		db " "
	ELSE
		db feet_tens_digit + $30
	ENDC
	DEF feet_ones_digit = (\\1) % 10
	db feet_ones_digit + $30
	DEF inches_tens_digit = ((\\2) / 10) % 10
	IF inches_tens_digit > 0
		db $70
	ELSE
		db $72
	ENDC
	DEF inches_ones_digit = (\\2) % 10
	db inches_ones_digit + $30
	db "@"
ENDM

MACRO dex_weight
	IF \\1 >= 1000
		db ((\\1 / 1000) % 10) + $30
	ELSE
		db " "
	ENDC

	IF \\1 >= 100
		db ((\\1 / 100) % 10) + $30
	ELSE
		db " "
	ENDC

	IF \\1 >= 10
		db ((\\1 / 10) % 10) + $30
	ELSE
		db " "
	ENDC

	db ((\\1) % 10) + $30
	db $00, $83
ENDM

MACRO dex_weight_decimal
	DEF x = (\\1) * 10
	IF x >= 100
		db ((x / 100) % 10) + $30
	ELSE
		db " "
	ENDC

	IF x >= 10
		db ((x / 100) % 10) + $30
	ELSE
		db " "
	ENDC

	db (x % 10) + $30
	db ((\\2) % 10) + $30
	db $00, $FC
ENDM

; \1 = species string
MACRO dex_species
; Add right padding to format to 11 characters, define 2 bytes
; for each character (using dex_species_char below)
	FOR I, STRLEN(\\1)
		dex_species_char CHARVAL(STRSLICE(\\1, I, I + 1))
	ENDR
	REPT 11 - STRLEN(\\1)
		dex_species_char $20
	ENDR
	db "@"
ENDM

MACRO dex_species_char
	IF (\\1) == $20
		db $81, $40
	ELSE
		db $82, (\\1) + $1F
	ENDC
ENDM