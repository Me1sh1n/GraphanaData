
// ----------------------------
// Install depensensies and libraries
// ----------------------------

#include <ArduinoJson.h>	      // add to create JSON messages
#include <ArduinoJson.hpp>
#include <Adafruit_Sensor.h>  	//  add Adafruit libraries
#include "Adafruit_BME680.h"	  //  add BME680 sensor library
#include <WiFi.h>		            //  enable network conectivity
#include <Wire.h>		            //  enable I2C communication
#include <PubSubClient.h>	      //  add MQTT communication

Adafruit_BME680 bme;            //  create bme object to initiate bme sensor connected over I2C 

// ----------------------------
// Store wifi details and mqqt server ip
// ----------------------------

const char* ssid = "XXX";              // add router ssid
const char* password = "XXX";          // add router password
const char* mqtt_server = "XXX";       // add Server IP


// ----------------------------
// Set wifi client
// ----------------------------

WiFiClient espClient;
PubSubClient client(espClient);

long lastMesg = 0;


// ----------------------------
// Check wiring / wifi conection [Runs once]
// ----------------------------

void setup() {
  delay(100);                    // 100ms delay to make sure everything has started

  Serial.begin(115200);          // start serial connection and wait for serial monitor to open
  while (!Serial);

  // attempt to start BME senor (wiring check)
  if (!bme.begin()) {                                                  
    Serial.println("BME680 sensor Not found, check wiring!");
    while (1);
  }

// configure BME – (Arduino/BME library)
  bme.setTemperatureOversampling(BME680_OS_8X);
  bme.setHumidityOversampling(BME680_OS_2X);
  bme.setPressureOversampling(BME680_OS_4X);
  bme.setIIRFilterSize(BME680_FILTER_SIZE_3);
  bme.setGasHeater(320, 150); // 320*C for 150 ms

// connect to WiFi network (prints ssid / debug messages)
Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);


 // constant check if connected – prints dots if waiting to connect
while (WiFi.status() != WL_CONNECTED) {      
    delay(500);
    Serial.print(".");
  }

// print alert when wifi is connected
  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());


  client.setServer(mqtt_server, 1883);   // set mqqt server details
}


// ----------------------------
// Main Loop
// ----------------------------

//  loop runs constantly
void loop() {

  // check connection to mqtt server
// runs until connection is made
  if (!client.connected()) {
    reconnect();
  }

   // document stores and contains data read from sensor
  StaticJsonDocument<80> doc;
  
  // “output” stores Json message that we send to mqqt server
  char output[80];

   // 5 delay timer for sending data
  long now = millis();
  if (now - lastMsg > 5000) {
    lastMsg = now;

    // read data from the sensor using bme. read functions
    float temp = bme.readTemperature();
    float pressure = bme.readPressure()/100.0;
    float humidity = bme.readHumidity();
    float gas = bme.readGas()/1000.0;

     // add variable to JSON document
    doc["t"] = temp;
    doc["p"] = pressure;
    doc["h"] = humidity;
    doc["g"] = gas;

    // serialise JSON document – turn document into string
    serializeJson(doc, output);
    
     // send JSON character array to argument of topic with publish function
    // Example  {"t":25.45623,"p":860.20,"h":60.463241,"g":310.564}
    Serial.println(output);
    client.publish("/home/sensors", output);
  }
    
}


// ----------------------------
// Reconection Loop
// ----------------------------

// loop until reconnected
void reconnect() {

// print connection message
while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    
     // create a random client ID  // Attempt to connect
    String clientId = "ESP8266Client-";
    clientId += String(random(0xffff), HEX);

    // attempt connection and print 
    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      delay(5000);
    }
  }
}

