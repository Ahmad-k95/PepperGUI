const int ledPin = 13;       // Built-in LED
const int vicontriggerpin = 8;    // Trigger output pin
const int emgtriggerpin = 7;
bool emg_activated = false;
bool ledOn = false;
unsigned long ledStartTime = 0;
const unsigned long ledDuration = 500; // LED ON duration in ms

void setup() {
  pinMode(ledPin, OUTPUT);
  pinMode(vicontriggerpin, OUTPUT);
  pinMode(emgtriggerpin, OUTPUT);
  digitalWrite(vicontriggerpin, LOW);  // Make sure trigger is low at start
  digitalWrite(emgtriggerpin, LOW);
  Serial.begin(9600);
}

void loop() {
  // Check serial input
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    if (cmd == '1') {
      // Trigger signal on pin 8
      digitalWrite(vicontriggerpin, HIGH);
      delayMicroseconds(100); // Short pulse (adjust as needed)
      digitalWrite(vicontriggerpin, LOW);
      if(emg_activated == false){
        digitalWrite(emgtriggerpin, HIGH);
        emg_activated = true;
      }
      else{
        digitalWrite(emgtriggerpin, LOW);
        emg_activated = false;
      }
      

      // Start LED blink (non-blocking)
      digitalWrite(ledPin, HIGH);
      ledOn = true;
      ledStartTime = millis();
    }
  }

  // Turn off LED after duration (non-blocking)
  if (ledOn && (millis() - ledStartTime >= ledDuration)) {
    digitalWrite(ledPin, LOW);
    ledOn = false;
  }
}
