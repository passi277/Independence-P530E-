# Grillfürst Independence P530E – Home Assistant (lokal)

Lokale Einbindung des Grillfürst Independence P530E („Grillfürst Smart Grill 2025“ in der Smart Life App)
in Home Assistant – ohne Cloud.

## Eigene Integration `grillfuerst_p530e` (empfohlen)

`custom_components/grillfuerst_p530e` – über den Marketplace/HACS als benutzerdefiniertes Repository
(Kategorie *Integration*) installieren oder den Ordner nach `/config/custom_components/` kopieren.

Einrichtung: Einstellungen → Geräte & Dienste → Integration hinzufügen → „Grillfürst Independence P530E“.
IP-Adresse, Geräte-ID und lokaler Schlüssel werden aus einer vorhandenen Tuya-Local-Einrichtung übernommen.
Den Grill danach aus Tuya Local entfernen – zwei gleichzeitige lokale Verbindungen vertragen Tuya-Geräte schlecht.

Sensoren (bisher nur Gasflasche):

| Sensor | Quelle |
|--------|--------|
| Gasmenge (kg) | DP 119 |
| Gasfüllstand (%) | berechnet: DP 119 / DP 122 |
| Gewicht Waage (kg) | DP 121 (Diagnose) |
| Gasflaschengröße (kg) | DP 122 (Diagnose) |
| Tara Gasflasche (kg) | DP 123 (Diagnose) |
| Füllstandsstufe 1–7 | DP 120 (Diagnose, standardmäßig deaktiviert) |

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
| 119 | int ×0,1 kg | aktuelle Gasmenge (= Waage − Tara, min. 0) | ✅ bestätigt |
| 120 | string `"1"`–`"7"` | Füllstandsstufe für die Flaschengrafik | ✅ bestätigt |
| 121 | int ×0,1 kg | Bruttogewicht auf der Waage | ✅ bestätigt |
| 122 | int ×0,1 kg | Gasflaschengröße (App-Einstellung, 0,5er-Schritte) | ✅ bestätigt |
| 123 | int ×0,1 kg | Tara (App-Einstellung, min. 4,0 kg) | ✅ bestätigt |
| 101 | int | evtl. Garraum-/Umgebungstemperatur (23) | ❓ |
| 102–107 | int | evtl. Kerntemperaturfühler | ❓ |
| 108, 109, 113, 114, 124 | int | ? | ❓ |
| 110 / 111 / 112 | int | 200 / 125 / 95 – evtl. Zieltemperaturen/Alarme | ❓ |
| 116, 126 | int | 3 | ❓ |
| 118 | string | `"red"` – evtl. Lichtfarbe | ❓ |
| 125, 128–131 | bool | ? | ❓ |
| 132 | bool | evtl. Ein/Aus bzw. aktiv | ❓ |
