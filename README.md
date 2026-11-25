# Grillfürst Independence P530E – Home Assistant (lokal)

Lokale Einbindung des Grillfürst Independence P530E („Grillfürst Smart Grill 2025“ in der Smart Life App)
in Home Assistant – ohne Cloud.

## Eigene Integration `grillfuerst_p530e` (empfohlen)

`custom_components/grillfuerst_p530e` – über den Marketplace/HACS als benutzerdefiniertes Repository
(Kategorie *Integration*) installieren oder den Ordner nach `/config/custom_components/` kopieren.

Einrichtung: Einstellungen → Geräte & Dienste → Integration hinzufügen → „Grillfürst Independence P530E“.
IP-Adresse, Geräte-ID und lokaler Schlüssel werden aus einer vorhandenen Tuya-Local-Einrichtung übernommen.
Den Grill danach aus Tuya Local entfernen – zwei gleichzeitige lokale Verbindungen vertragen Tuya-Geräte schlecht.

Entitäten:

| Entität | Typ | Quelle |
|---------|-----|--------|
| Garraumtemperatur (vermutet) | Sensor | DP 101 |
| Temperatur Fühler F1–F4 (vermutet) | Sensor | DP 102–105 |
| Zieltemperatur Fühler F1–F4 (0–200 °C) | Zahl | DP 106–109 |
| Garstufe Fühler F1–F4 (Vorauswahl der App, setzt die Zieltemperatur) | Auswahl | DP 106–109 |
| Gasmenge (kg) | Sensor | DP 119 |
| Gasfüllstand (%) | Sensor | berechnet: DP 119 / DP 122 |
| Grillmodus | Auswahl | DP 114 |
| Zieltemperatur Direkt (200–360 °C) | Zahl | DP 110 |
| Zieltemperatur Indirekt (120–200 °C) | Zahl | DP 111 |
| Zieltemperatur Low & Slow (95–115 °C) | Zahl | DP 112 |
| Tara Gasflasche (4,0–15,0 kg) | Zahl (Konfiguration) | DP 123 |
| Gasflaschengröße (3,0–12,0 kg, 0,5er) | Zahl (Konfiguration) | DP 122 |
| Timer (Status) | Sensor | DP 126 |
| Timer Restzeit (min) | Sensor | DP 124 |
| Garraumlicht | Schalter | DP 129 |
| Logo-Beleuchtung | Schalter | DP 128 |
| Reglerbeleuchtung | Schalter (an = individuell) | DP 116 |
| Reglerlicht-Modus | Auswahl | DP 116 |
| Reglerfarbe | Auswahl | DP 118 |
| Ton | Schalter | DP 130 |
| Gewicht Waage (kg) | Sensor (Diagnose) | DP 121 |
| Füllstandsstufe 1–7 | Sensor (Diagnose, deaktiviert) | DP 120 |

Schreibbare Werte werden auf die Grenzen der App begrenzt. Modus und Zieltemperaturen steuern die
Gasbrenner des Grills – nach dem Grillen die Gasflasche wie gewohnt zudrehen.

Garstufen (wie in der App, nur die Temperatur wird an den Grill übertragen):

| Sorte | °C |
|-------|----|
| Rind | Well done 66 · Medium well 61 · Medium 56 · Medium rare 53 · Rare 50 |
| Kalb | Well done 74 · Medium well 71 · Medium 66 · Medium rare 63 |
| Lamm | Well done 68 · Medium well 66 · Medium 62 · Medium rare 56 · Rare 50 |
| Schwein | Well done 70 · Medium well 66 · Medium 62 |
| Burger / Hähnchen / Truthahn / Fisch | 74 / 78 / 78 / 60 |

Im Standby meldet der Grill die Gaswerte nicht; die Sensoren behalten dann den letzten Wert
(auch über einen Neustart von Home Assistant hinweg).

## Alternative: Gerätedatei für Tuya Local

`tuya-local/grillfuerst_smart_grill_2025.yaml` – nach `/config/custom_components/tuya_local/devices/` kopieren,
Home Assistant neu starten und das Gerät in Tuya Local auf den Typ `grillfuerst_smart_grill_2025` umstellen.

> Achtung: Ein Update von Tuya Local überschreibt den `devices`-Ordner. Datei danach erneut kopieren
> (oder sie upstream bei Tuya Local einreichen).

## Datenpunkte (DPs)

Protokoll 3.5, Product-ID `eo4tfylu1iue4ytt`. Im Standby meldet der Grill nur DP 101–107.

| DP | Typ | Bedeutung | Status |
|----|-----|-----------|--------|
| 110 | int °C | Zieltemperatur Direktes Grillen (200–360) | ✅ |
| 111 | int °C | Zieltemperatur Indirektes Grillen (120–200) | ✅ |
| 112 | int °C | Zieltemperatur Low & Slow (95–115) | ✅ |
| 113 | int | 5 – vermutlich Anzahl Brenner | ❓ |
| 114 | int | Grillmodus: 0 Direkt, 1 Stufen, 2 Frei, 3 Low & Slow, 4 Indirekt | ✅ (1/2 sehr wahrscheinlich) |
| 116 | int | Reglerlicht-Modus: 0 aus, 1 zufällig, 2 temperaturabhängig, 3 individuell, 4 magic | ✅ |
| 118 | string | Reglerfarbe: red, orange, yellow, green, light_green, deep_blue, purple, pink | ✅ |
| 119 | int ×0,1 kg | aktuelle Gasmenge (= Waage − Tara, min. 0) | ✅ |
| 120 | string `"1"`–`"7"` | Füllstandsstufe für die Flaschengrafik | ✅ |
| 121 | int ×0,1 kg | Bruttogewicht auf der Waage | ✅ |
| 122 | int ×0,1 kg | Gasflaschengröße (App-Einstellung, 3,0–12,0 kg, 0,5er-Schritte) | ✅ |
| 123 | int ×0,1 kg | Tara (App-Einstellung, 4,0–15,0 kg) | ✅ |
| 128 | bool | Logo-Beleuchtung | ✅ |
| 129 | bool | Garraumlicht | ✅ |
| 101 | int °C | vermutlich Garraumtemperatur (Fühler unter dem Rost); 23 bzw. 0 je nach Modus | ❓ |
| 102–105 | int °C | vermutlich Ist-Temperatur Fühler F1–F4 | ❓ (Fühler noch nicht getestet) |
| 106–109 | int °C | Zieltemperatur Fühler F1–F4 (0–200) | ✅ F1–F3, F4 nach Muster |
| 124 | int min | Timer-Restzeit (aufgerundet) | ✅ |
| 130 | bool | Ton (Sound) an/aus | ✅ |
| 125, 131 | bool | ? | ❓ |
| 126 | int | Timer-Status: 0 gestoppt, 1 pausiert, 2 läuft, 3 bereit | ✅ |
| 132 | bool | evtl. Grill aktiv/wach | ❓ |
