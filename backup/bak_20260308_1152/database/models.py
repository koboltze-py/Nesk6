"""
Datenbankmodelle (Datenklassen)
Spiegeln die PostgreSQL-Tabellenstruktur wider
"""
from dataclasses import dataclass, field
from datetime import date, time, datetime
from typing import Optional


@dataclass
class Mitarbeiter:
    """Repräsentiert einen Mitarbeiter."""
    id:             Optional[int]  = None
    vorname:        str            = ""
    nachname:       str            = ""
    personalnummer: str            = ""
    funktion:       str            = "stamm"      # stamm | dispo
    position:       str            = ""
    abteilung:      str            = ""
    email:          str            = ""
    telefon:        str            = ""
    eintrittsdatum: Optional[date] = None
    status:         str            = "aktiv"      # aktiv | inaktiv | beurlaubt
    erstellt_am:    Optional[datetime] = None
    geaendert_am:   Optional[datetime] = None

    @property
    def vollname(self) -> str:
        return f"{self.vorname} {self.nachname}".strip()


@dataclass
class Dienstplan:
    """Repräsentiert einen Dienstplan-Eintrag (Schicht)."""
    id:                  Optional[int]  = None
    mitarbeiter_id:      Optional[int]  = None
    mitarbeiter_name:    str            = ""
    datum:               Optional[date] = None
    start_uhrzeit:       Optional[time] = None
    end_uhrzeit:         Optional[time] = None
    position:            str            = ""
    schicht_typ:         str            = "regulär"  # regulär | nacht | bereitschaft
    notizen:             str            = ""
    erstellt_am:         Optional[datetime] = None


@dataclass
class Abteilung:
    """Repräsentiert eine Abteilung/Gruppe."""
    id:          Optional[int] = None
    name:        str           = ""
    beschreibung: str          = ""


@dataclass
class Position:
    """Repräsentiert eine Stellenbezeichnung."""
    id:   Optional[int] = None
    name: str           = ""
    kuerzel: str        = ""


@dataclass
class UebergabeProtokoll:
    """Repräsentiert ein Schicht-Übergabeprotokoll."""
    id:                 Optional[int]  = None
    datum:              str            = ""          # YYYY-MM-DD
    schicht_typ:        str            = "tagdienst" # tagdienst | nachtdienst
    beginn_zeit:        str            = ""          # HH:MM
    ende_zeit:          str            = ""          # HH:MM
    patienten_anzahl:   int            = 0
    personal:           str            = ""
    ereignisse:         str            = ""
    massnahmen:         str            = ""
    uebergabe_notiz:    str            = ""
    ersteller:          str            = ""
    abzeichner:         str            = ""
    status:             str            = "offen"     # offen | abgeschlossen
    erstellt_am:        Optional[datetime] = None
    geaendert_am:       Optional[datetime] = None


@dataclass
class Fahrzeug:
    """Repräsentiert ein Fahrzeug."""
    id:             Optional[int] = None
    kennzeichen:    str           = ""
    typ:            str           = ""          # RTW, KTW, PKW ...
    marke:          str           = ""
    modell:         str           = ""
    baujahr:        Optional[int] = None
    fahrgestellnr:  str           = ""
    tuev_datum:     str           = ""          # YYYY-MM-DD
    notizen:        str           = ""
    aktiv:          int           = 1
    erstellt_am:    Optional[datetime] = None
    geaendert_am:   Optional[datetime] = None


@dataclass
class FahrzeugStatus:
    """Repräsentiert einen Status-Eintrag in der Historie."""
    id:          Optional[int] = None
    fahrzeug_id: Optional[int] = None
    status:      str           = "fahrbereit"  # fahrbereit|defekt|werkstatt|ausser_dienst|sonstiges
    von:         str           = ""            # YYYY-MM-DD
    bis:         str           = ""            # YYYY-MM-DD oder leer
    grund:       str           = ""
    erstellt_am: Optional[datetime] = None


@dataclass
class FahrzeugSchaden:
    """Repräsentiert einen Schaden an einem Fahrzeug."""
    id:           Optional[int] = None
    fahrzeug_id:  Optional[int] = None
    datum:        str           = ""       # YYYY-MM-DD
    beschreibung: str           = ""
    schwere:      str           = "gering" # gering|mittel|schwer
    kommentar:    str           = ""
    behoben:      int           = 0
    behoben_am:   str           = ""
    erstellt_am:  Optional[datetime] = None
    geaendert_am: Optional[datetime] = None


@dataclass
class FahrzeugTermin:
    """Repräsentiert einen Termin (TÜV, Inspektion etc.) für ein Fahrzeug."""
    id:           Optional[int] = None
    fahrzeug_id:  Optional[int] = None
    datum:        str           = ""         # YYYY-MM-DD
    uhrzeit:      str           = ""         # HH:MM
    typ:          str           = "sonstiges" # tuev|inspektion|reparatur|hauptuntersuchung|sonstiges
    titel:        str           = ""
    beschreibung: str           = ""
    kommentar:    str           = ""
    erledigt:     int           = 0
    erstellt_am:  Optional[datetime] = None
    geaendert_am: Optional[datetime] = None
