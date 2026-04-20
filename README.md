***Simulointi***

* RaspberryPi_Simulation.py on Python-koodia, joka simuloi anturitietoa virtuaalisessa ympäristössä Raspberry Pi -laitteella.
* Koodia käytettiin Grafanan käyttöönottoon tilanteessa, jossa kaikkia oikeita antureita ei ollut saatavilla.
* Koodi simuloi normaalia vuorokausisykliä, jotta aurinko-olosuhteita voidaan jäljitellä ja jännitteen muutoksia päivän aikana voidaan havainnollistaa.
* Seuraavat tiedot simuloitiin:
           
            timestamp
            datetime
            day_cycle_position
            is_daytime
            solar_power_w
            battery_voltage_v
            temperature_c
            current_draw_a
            alarm
            vibration



***ESP32***

* ESP32-koodia käytetään datan keräämiseen BME680-anturin avulla.
* Pääajatuksena on käyttää samaa peruskoodia ja vaihtaa vain kunkin anturin tarvitsemat kirjastot, jolloin useat ESP32-laitteet voivat lähettää dataa samalle InfluxDB-palvelimelle.
* Seuraavat tiedot keräätiin:
  
            temprature
            pressure
            humidity
            gas



***Palvelin***

* Raspberry Pi:tä käytettiin InfluxDB- ja Mosquitto-palvelimena.
* Tiedosto DG_1D.csv sisältää osan simuloidusta datasta.
