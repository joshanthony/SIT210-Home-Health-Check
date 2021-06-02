#define USE_ARDUINO_INTERRUPTS true // Interrupts set to low level for accuracy
#include <PulseSensorPlayground.h> // Basic pulse sensor library

const int PulseWire = 0; // Signal to analog 0
int Threshold = 550; // Threshold for which signal we count as a heart beat
PulseSensorPlayground pulseSensor; // Instance of pulse sensor class

void setup() {
  // Serial output to send to the Raspberry Pi
  Serial.begin(9600);
  
  // Configure initial settings and start the sensor
  pulseSensor.analogInput(PulseWire);
  pulseSensor.setThreshold(Threshold);
  pulseSensor.begin();
}

void loop() {
  // Try to read the beats per minute as an int
  int BPM = pulseSensor.getBeatsPerMinute();

  // Poll for the heart beat event
  if (pulseSensor.sawStartOfBeat()) {
    // Print the result to serial
    Serial.println(BPM);
  }
  // Short delay before next reading
  delay(20);
}