const int ledPin = 13;       // Built-in LED
const int triggerPin = 8;    // Trigger output pin

bool ledOn = false;
unsigned long ledStartTime = 0;
const unsigned long ledDuration = 500; // LED ON duration in ms

void setup() {
  pinMode(ledPin, OUTPUT);
  pinMode(triggerPin, OUTPUT);
  digitalWrite(triggerPin, LOW);  // Make sure trigger is low at start
  Serial.begin(9600);
}

void loop() {
  // Check serial input
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    if (cmd == '1') {
      // Trigger signal on pin 8
      digitalWrite(triggerPin, HIGH);
      delayMicroseconds(100); // Short pulse (adjust as needed)
      digitalWrite(triggerPin, LOW);

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
