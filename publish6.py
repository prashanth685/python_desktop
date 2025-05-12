import math
import struct
import paho.mqtt.publish as publish
from PyQt5.QtCore import QTimer, QObject
from PyQt5.QtWidgets import QApplication
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class MQTTPublisher(QObject):
    def __init__(self, broker, topics):
        super().__init__()
        self.broker = broker
        self.topics = topics if isinstance(topics, list) else [topics]
        self.count = 1

        self.frequency = 5
        self.amplitude = (46537 - 16390) / 2
        self.offset = (46537 + 16390) / 2

        self.sample_rate = 4096
        self.time_per_message = 1.0
        self.current_time = 0.0

        self.channel = 4
        self.frame_index = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.publish_message)
        self.timer.start(1000)  # Publish every 1 second

    def publish_message(self):
        if self.count < 200:
            # Generate sine values for each channel
            samples_per_channel = self.sample_rate
            all_channel_data = []

            for i in range(samples_per_channel):
                t = self.current_time + (i / self.sample_rate)
                base_value = self.offset + self.amplitude * math.sin(2 * math.pi * self.frequency * t)
                rounded_value = int(round(base_value))
                all_channel_data.append(rounded_value)

            self.current_time += self.time_per_message

            # Interleave channel data: CH0_0, CH1_0, CH2_0, CH3_0, CH0_1, ...
            interleaved = []
            for i in range(samples_per_channel):
                for ch in range(self.channel):
                    interleaved.append(all_channel_data[i])  # same value for now

            assert len(interleaved) == 16384, f"Expected 16384 values, got {len(interleaved)}"

            # Create header
            header = [
                self.frame_index % 65535,
                self.frame_index // 65535,
                self.channel,
                self.sample_rate,
                16,  # samplingSize (bits)
                int(self.sample_rate / self.channel),
                0, 0, 0, 0  # Placeholder slots
            ]

            message_values = header + interleaved

            # Pack into binary
            binary_message = struct.pack(f"{len(message_values)}H", *message_values)
            # print(len(all_channel_data))

            for topic in self.topics:
                try:
                    publish.single(topic, binary_message, hostname=self.broker, qos=1)
                    logging.info(f"[{self.count}] Published to {topic}: frame {self.frame_index} with {len(interleaved)} values")
                except Exception as e:
                    logging.error(f"Failed to publish to {topic}: {str(e)}")

            self.frame_index += 1
            self.count += 1
        else:
            self.timer.stop()
            logging.info("Publishing stopped after 200 messages.")

if __name__ == "__main__":
    app = QApplication([])
    broker = "192.168.1.175"
    topics = ["sarayu/tag2/topic2|m/s"]
    mqtt_publisher = MQTTPublisher(broker, topics)
    app.exec_()
