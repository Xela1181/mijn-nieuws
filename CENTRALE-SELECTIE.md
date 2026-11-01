# Eén dagelijkse nieuwsselectie — uitvoeringsplan

## Feitelijke status
De GitHub-workflow maakt een gratis RSS-voorselectie in `daily-selection.json`, met 8–13 berichten waar voldoende bronnen beschikbaar zijn. Dit is `selection_mode: "rss_shortlist"`, niet een redactioneel gecontroleerde selectie. De artikelen behouden hun oorspronkelijke taal. Het dashboard leest de titels en RSS-samenvattingen; de browser leest exact die zichtbare titels en samenvattingen voor, met een Nederlandse of Engelse stem. De maximale spreektekst is 1.700 woorden (ongeveer 15 minuten, afhankelijk van stem en snelheid).

## Tijdstip en bron
De GitHub-workflow staat op één dagelijkse run om 03:17 UTC, dus 04:17 Nederlandse wintertijd en 05:17 zomertijd. GitHub Actions kan vertraging hebben. Na samenvoegen is het publieke dagbestand bereikbaar via:
https://xela1181.github.io/mijn-nieuws/daily-selection.json

De bestaande ChatGPT-automatisering draait om 06:00 Europe/Amsterdam en is **nog niet gekoppeld** aan dit bestand. Die automatisering pas aanpassen nadat de workflow op de hoofdbranch is geactiveerd en een correct dagbestand publiceert. Bij ontbreken van een dagbestand moet ChatGPT de mismatch expliciet melden, niet een eigen selectie als identiek presenteren.

## Afgesproken bron-van-waarheid
1. GitHub maakt eenmaal per dag een vaste RSS-selectie; geen stilzwijgende wijzigingen later op de dag.
2. Het dashboard toont dezelfde volgorde als het dagbestand.
3. Audio leest exact de zichtbare titel en samenvatting van elk geselecteerd artikel voor; geen vertaling.
4. ChatGPT haalt na activatie hetzelfde dagbestand op en geeft dezelfde items in dezelfde volgorde weer, met dezelfde titel en samenvatting. De Business English-les en podcast-tip zijn afzonderlijke rubrieken.
5. Een RSS-samenvatting is niet de volledige tekst van het bronartikel. Klik door naar de uitgever voor de volledige tekst.

## Grenzen
De selectie is automatisch gerangschikt op onderwerp en actualiteit, niet inhoudelijk gecontroleerd door een redacteur. Browserstemmen en spraakweergave verschillen per apparaat. De ChatGPT-automatisering kan een externe URL mogelijk niet altijd openen; zonder verificatie is synchronisatie niet gegarandeerd. Het dashboard blijft op de huidige live-versie totdat de PR is goedgekeurd.
