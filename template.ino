void setup() {
    Serial.begin(57600);
    while (Serial.available == 0);
    %code%
}

void loop() {}