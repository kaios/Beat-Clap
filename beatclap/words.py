"""English vocabulary, hyphenated by spoken syllable."""

WORDS = [
    "CAT", "DOG", "TRAIN",
    "RO-BOT", "HAP-PY", "WA-TER", "MU-SIC", "PEN-CIL", "RAIN-BOW", "MON-KEY",
    "TEA-CHER", "WIN-DOW", "GAR-DEN", "COF-FEE",
    "BA-NA-NA", "COM-PU-TER", "E-LE-PHANT", "TO-MA-TO", "HAM-BUR-GER",
    "PI-AN-O", "KAN-GA-ROO", "OC-TO-PUS", "BEAU-TI-FUL", "DI-NO-SAUR",
    "TEL-E-PHONE", "STRAW-BER-RY", "VI-O-LIN",
    "A-MER-I-CA", "HEL-I-COP-TER", "AV-O-CA-DO", "CAL-CU-LA-TOR",
    "VEG-E-TA-BLE", "TEL-E-VI-SION", "WA-TER-MEL-ON", "IN-FOR-MA-TION",
    "U-NI-VER-SI-TY", "DIC-TION-AR-Y", "HIP-PO-POT-A-MUS", "CON-GRAT-U-LA-TIONS",
    "AL-PHA-BET", "EN-VI-RON-MENT",
]

# How each syllable should sound when spoken alone. Written syllables like "I" or
# "TION" read as letter names / nonsense, so TTS gets these respellings instead.
SPOKEN = {
    "RO-BOT": "roe-bot", "HAP-PY": "hap-pee", "WA-TER": "waw-ter", "MU-SIC": "myoo-zik",
    "PEN-CIL": "pen-sill", "RAIN-BOW": "rain-boh", "MON-KEY": "mun-key",
    "TEA-CHER": "tee-chur", "WIN-DOW": "win-doh", "GAR-DEN": "gar-den",
    "COF-FEE": "kaw-fee", "BA-NA-NA": "buh-nan-uh", "COM-PU-TER": "kum-pyoo-ter",
    "E-LE-PHANT": "el-uh-funt", "TO-MA-TO": "tuh-may-toe", "HAM-BUR-GER": "ham-bur-gur",
    "PI-AN-O": "pee-an-oh", "KAN-GA-ROO": "kan-guh-roo", "OC-TO-PUS": "ock-tuh-puss",
    "BEAU-TI-FUL": "byoo-tih-full", "DI-NO-SAUR": "dye-nuh-sore",
    "TEL-E-PHONE": "tel-uh-phone", "STRAW-BER-RY": "straw-bair-ee",
    "VI-O-LIN": "vye-uh-lin", "A-MER-I-CA": "uh-mair-ih-kuh",
    "HEL-I-COP-TER": "hel-ih-kop-ter", "AV-O-CA-DO": "av-uh-kah-doe",
    "CAL-CU-LA-TOR": "kal-kyuh-lay-ter", "VEG-E-TA-BLE": "vej-uh-tuh-bull",
    "TEL-E-VI-SION": "tel-uh-vih-zhun", "WA-TER-MEL-ON": "waw-ter-mel-un",
    "IN-FOR-MA-TION": "in-fer-may-shun", "U-NI-VER-SI-TY": "you-nih-ver-sih-tee",
    "DIC-TION-AR-Y": "dick-shun-air-ee", "HIP-PO-POT-A-MUS": "hip-oh-pot-uh-muss",
    "CON-GRAT-U-LA-TIONS": "kun-grach-uh-lay-shunz", "AL-PHA-BET": "al-fuh-bet",
    "EN-VI-RON-MENT": "en-vye-run-ment",
}


def spoken_syllables(word):
    syllables = SPOKEN.get(word, word.lower()).split("-")
    assert len(syllables) == len(word.split("-")), word
    return syllables
