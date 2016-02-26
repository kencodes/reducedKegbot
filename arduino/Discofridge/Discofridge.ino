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
 *       tap1:63 tap2:0 tap3:0 temp1:4.7
 *  meaning 63 flow meter pulses seen on tap1 since last message, none on
 *  taps 2 or 3, temperature sensor 1 reads 4.7C
 */

// This library allows any pin to be used as a medium-speed interrupt
#include <PinChangeInt.h>

// For DS18S20 Temperature Sensor
#include <OneWire.h>
OneWire tempSensor1(9);  // on pin 9,  need 4.7Kohm PU to VCC
OneWire tempSensor2(10); // on pin 10, need 4.7Kohm PU to VCC
OneWire tempSensor3(11); // on pin 11, need 4.7Kohm PU to VCC

// Flow Meter Pin Numbers
#define TAP_PIN_1 A2
#define TAP_PIN_2 A3
#define TAP_PIN_3 A4

// Serial interface settings
#define SERIAL_BAUD 115200
#define SERIAL_MSG_INTERVAL 500//333//1000//
//#define READ_TEMP_INTERVAL 15 // number of serial messages between reading the temperature sensor

// Temperature sensor
int HighByte, LowByte, TReading, SignBit, Tc_100, Whole, Fract;
bool tempSensor1Found = false;
bool tempSensor2Found = false;
bool tempSensor3Found = false;
byte i;
byte addr1[8];
byte addr2[8];
byte addr3[8];
//uint8_t temp_sens_wait; // Read the temperature sensor every 5-10 seconds
//#define NUM_TEMP_SENSORS 3

uint8_t ii;             // Counting variable for loops
uint8_t count;          // Store the pulse count value so the interrupts can continue to be handled
String serial_message;  // Initialize string for serial message

#define TOTAL_PINS 19 // DON'T CHANGE THIS
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
  Serial.begin(SERIAL_BAUD);
  //temp_sens_wait = 1;      // Read the temperature sensor every 5-10 seconds
  Whole = 0; // temperature sensor values
  Fract = 0; // temperature sensor values
  // Look for temperature sensor. If found, report address
  //   If not found, report not found
  if (tempSensor1.search(addr1)) {
    tempSensor1Found = true;
  } else {
    tempSensor1Found = false;
    tempSensor1.reset_search();
  }
  if (tempSensor2.search(addr2)) {
    tempSensor2Found = true;
  } else {
    tempSensor2Found = false;
    tempSensor2.reset_search();
  }
  if (tempSensor3.search(addr3)) {
    tempSensor3Found = true;
  } else {
    tempSensor3Found = false;
    tempSensor3.reset_search();
  }
  // Start off by reading temperature
  //readTemp(addr);
}

// Read the temperature from the sensor
void readTemp(const byte* addr, int whichSensor) {
  byte present = 0;
  byte data[12];
  
  // Check CRC
  if ( OneWire::crc8( addr, 7) != addr[7]) {
      // Serial.print("CRC is not valid!\n");
      return;
  }
  if (whichSensor==1) {
    tempSensor1.reset();
    tempSensor1.select(addr);
    tempSensor1.write(0x44,1);         // start conversion, with parasite power on at the end
    present = tempSensor1.reset();
    tempSensor1.select(addr);    
    tempSensor1.write(0xBE);           // Read Scratchpad
    // Reading the temperature data
    for ( i = 0; i < 9; i++) {        // we need 9 bytes
      data[i] = tempSensor1.read();
    }
  } else if (whichSensor==2) {
    tempSensor2.reset();
    tempSensor2.select(addr);
    tempSensor2.write(0x44,1);         // start conversion, with parasite power on at the end
    present = tempSensor2.reset();
    tempSensor2.select(addr);    
    tempSensor2.write(0xBE);           // Read Scratchpad
    // Reading the temperature data
    for ( i = 0; i < 9; i++) {        // we need 9 bytes
      data[i] = tempSensor2.read();
    }
  } else if (whichSensor==3) {
    tempSensor3.reset();
    tempSensor3.select(addr);
    tempSensor3.write(0x44,1);         // start conversion, with parasite power on at the end
    present = tempSensor3.reset();
    tempSensor3.select(addr);    
    tempSensor3.write(0xBE);           // Read Scratchpad
    // Reading the temperature data
    for ( i = 0; i < 9; i++) {        // we need 9 bytes
      data[i] = tempSensor3.read();
    }
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

}

// Every SERIAL_MSG_INTERVAL ms, send the number of pulses seen on each
// interrupt over the serial interface, where it will be parsed by a regex
void loop() {

    // Debug
//    if (tempSensor1Found) {
//      Serial.println("tempSensor1Found TRUE");
//      Serial.print("tempSensor1 addr = ");
//      Serial.println(addr1);
//    } else {
//      Serial.println("tempSensor1Found FALSE");
//    }
//    if (tempSensor2Found) {
//      Serial.println("tempSensor2Found TRUE");
//      Serial.print("tempSensor2 addr = ");
//      Serial.println(addr2);
//    } else {
//      Serial.println("tempSensor2Found FALSE");
//    }
//    if (tempSensor3Found) {
//      Serial.println("tempSensor3Found TRUE");
//      Serial.print("tempSensor3 addr = ");
//      Serial.println(addr3);
//    } else {
//      Serial.println("tempSensor3Found FALSE");
//    }
    
    // wait
    delay(SERIAL_MSG_INTERVAL);
    
    // Initialize string for serial message
    
    serial_message = "";
    
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
    if (tempSensor1Found) {
      readTemp(addr1, 1);
      serial_message += " temp1:";
      serial_message += Whole;
      serial_message += ".";
      serial_message += Fract;
    } else {
      serial_message += " temp1:0.0";
    }
    
    if (tempSensor2Found) {
      readTemp(addr2, 2);
      serial_message += " temp2:";
      serial_message += Whole;
      serial_message += ".";
      serial_message += Fract;
    } else {
      serial_message += " temp2:0.0";
    }
    
    if (tempSensor3Found) {
      readTemp(addr3, 3);
      serial_message += " temp3:";
      serial_message += Whole;
      serial_message += ".";
      serial_message += Fract;
    } else {
      serial_message += " temp3:0.0";
    }

     // Send serial message
     Serial.println(serial_message);
}

