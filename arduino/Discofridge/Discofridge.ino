/*
 *  This file is the hardware interface for Nuvation's Discofridge project.
 *  The Arduino is used to handle the hardware interface and to convert 0->5VDC
 *  pulses from the SF800 flow meters to 3.3V and reads the temperature sensors.
 *  It then encodes the sensor values in a serial stream which is sent over USB
 *  at 115200bd to the main computer (currently a Raspberry Pi Model 1 B)
 *  
 *  The PinChangeInterrupt library is used to extend the interrupt capabilities
 *  of the Arduino Uno (ATMega328), which normally has only 2 external interrupts.
 *  
 *  In this file, the Uno's pin A2 corresponds to tap 1 flow, A3 to tap 2 and A4
 *  to tap 3.
 *
 *  Full serial message will look like
 *       tap1:63 tap2:0 tap3:0 temp1:34.7 temp2:0.0
 *  meaning 63 flow meter pulses seen on tap1 since last message, none on
 *  taps 2 or 3, temperature sensor 1 reads 34.7F and temperature sensor 2
 *  wasn't found or could not be read
 */

// This library allows any pin to be used as a medium-speed interrupt
#include <PinChangeInt.h>

// For DS18S20 Temperature Sensor
#include <OneWire.h>
OneWire tempSensor(10); // on pin 10, need 4.7Kohm PU to VCC

// Flow Meter Pin Numbers
#define TAP_PIN_1 A2
#define TAP_PIN_2 A3
#define TAP_PIN_3 A4

// Serial interface settings
#define SERIAL_BAUD 115200
#define SERIAL_MSG_INTERVAL 500 //333
#define READ_TEMP_INTERVAL 10 // number of serial messages between reading the temperature sensor

// Temperature sensor variables
int HighByte, LowByte, TReading, SignBit, Tc_100, Whole, Fract;
bool tempSensorFound = false;
byte i;
byte addr[8];

#define NUM_TEMP_SENSORS 1

uint8_t ii;         // Counting variable for loops
uint8_t count;      // Store the pulse count value so the interrupts can continue to be handled
uint8_t temp_sens_wait;      // Read the temperature sensor every 5-10 seconds

#define TOTAL_PINS 19 // DON'T CHANGE THIS
// Notice that anything that gets modified inside an interrupt, that I wish to access
// outside the interrupt, is marked "volatile". That tells the compiler not to optimize
// them.
volatile uint8_t interrupt_count[TOTAL_PINS]={0}; // possible arduino pins

// Callback functions to track flow meter pulses
void tap1_tick() {
  interrupt_count[TAP_PIN_1]++;
};
void tap2_tick() {
  interrupt_count[TAP_PIN_2]++;
};
void tap3_tick() {
  interrupt_count[TAP_PIN_3]++;
}

void setup() {
  pinMode(TAP_PIN_1, INPUT_PULLUP);
  pinMode(TAP_PIN_2, INPUT_PULLUP);
  pinMode(TAP_PIN_3, INPUT_PULLUP);
  attachPinChangeInterrupt(TAP_PIN_1, tap1_tick, RISING);
  attachPinChangeInterrupt(TAP_PIN_2, tap2_tick, RISING);
  attachPinChangeInterrupt(TAP_PIN_3, tap3_tick, RISING);
  //OneWire tempSensor(45);  // DS18S20 Temperature chip on pin 10
  Serial.begin(SERIAL_BAUD);
  temp_sens_wait = 1;      // Read the temperature sensor every 5-10 seconds
  Whole = 0; // temperature sensor values
  Fract = 0; // temperature sensor values
  // Look for temperature sensor. If found, report address
  //   If not found, report not found
  if (tempSensor.search(addr)) {
    tempSensorFound = true;
    // Serial.print("DEVICE address: ");
    // for( i = 0; i < 8; i++) {
      // Serial.print(addr[i], HEX);
      // Serial.print(" ");
    // }
    // if ( addr[0] == 0x10) {
      // Serial.print("Device is a DS18S20 family device.\n");
    // }
    // else if ( addr[0] == 0x28) {
      // Serial.print("Device is a DS18B20 family device.\n");
    // }
    // else {
      // Serial.print("Device family is not recognized: 0x");
      // Serial.println(addr[0],HEX);
      // return;
    // }
  } else { //if ( !tempSensor.search(addr)) {
    tempSensorFound = false;
    // Serial.print("DEVICE NOT FOUND.\n");
    tempSensor.reset_search();
    //return;
  }
}

// Read the temperature from the sensor
void readTemp(const byte* addr) {
  byte present = 0;
  byte data[12];
  
  // Check CRC
  if ( OneWire::crc8( addr, 7) != addr[7]) {
      // Serial.print("CRC is not valid!\n");
      return;
  }
  tempSensor.reset();
  tempSensor.select(addr);
  tempSensor.write(0x44,1);         // start conversion, with parasite power on at the end
  present = tempSensor.reset();
  tempSensor.select(addr);    
  tempSensor.write(0xBE);           // Read Scratchpad
  
  // Reading the temperature data
  for ( i = 0; i < 9; i++) {        // we need 9 bytes
    data[i] = tempSensor.read();
  }
  
  // Extract temperature bytes
  LowByte = data[0];
  HighByte = data[1];
  TReading = (HighByte << 8) + LowByte;
  SignBit = TReading & 0x8000;      // test most sig bit
  if (SignBit) { // negative
    TReading = (TReading ^ 0xffff) + 1; // 2's comp
  }
  
  // multiply by (100 * 0.0625) or 6.25
  Tc_100 = (6 * TReading) + TReading / 4;
  
  // Convert temperature to decimal
  Whole = Tc_100 / 100;  // separate off the whole and fractional portions
  Fract = Tc_100 % 100;

  // if (SignBit) // If its negative
  // {
     // Serial.print("-");
  // }
  // Serial.print(Whole);
  // Serial.print(".");
  // if (Fract < 10)
  // {
     // Serial.print("0");
  // }
  // Serial.print(Fract);
  // Serial.print("\n");
}

// Initialize string for serial message
String serial_message;// = "";

// Every SERIAL_MSG_INTERVAL ms, send the number of pulses seen on each
// interrupt over the serial interface, where it will be parsed by a regex
void loop() {

    // wait
    delay(SERIAL_MSG_INTERVAL);
    
    // Initialize string for serial message
    serial_message = "";
    
    // Initialize temperature sensor variables
    // Whole = 0;
    // Fract = 0;
    
    // Flow meters
    for (ii=16; ii < 19; ii++) {
        count=interrupt_count[ii];        // store its count since the last iteration
        interrupt_count[ii]=0;            // and reset it to 0
        serial_message += " tap";
        serial_message += ii-15;
        serial_message += ":";
        serial_message += count;
    }
    
    // Read the temperature from the sensor
    if (temp_sens_wait == READ_TEMP_INTERVAL) { // Check if time to read temp sensor
        readTemp(addr);
        temp_sens_wait = 1;
    } else {
        temp_sens_wait++;
    }
    
    // Temperature sensors
    for (ii=0; ii<NUM_TEMP_SENSORS; ii++) {
        serial_message += " temp";
        serial_message += ii+1;
        serial_message += ":";
        serial_message += Whole;
        serial_message += ".";
        serial_message += Fract;
        //serial_message += "C";
    }
    
    // Finish serial message with newline
    //serial_message += "\n";
 
     // Send serial message
     Serial.println(serial_message);

}


