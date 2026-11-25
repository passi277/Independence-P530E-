# Grillfürst Independence P530E – Home Assistant (lokal)

Lokale Einbindung des Grillfürst Independence P530E („Grillfürst Smart Grill 2025“ in der Smart Life App)
in Home Assistant über [Tuya Local](https://github.com/make-all/tuya-local).

## Gerätedatei

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
