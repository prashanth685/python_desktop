
import math
import struct
import time
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
        self.count = 0

        self.frequency = 15
        self.amplitude = (46537 - 16390) / 2
        self.offset = (46537 + 16390) / 2

        self.sample_rate = 4096
        self.time_per_message = 1.0
        self.current_time = 0.0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.publish_message)
        self.timer.start(1000)  # Publish every 1 second

        self.channel = 4

    def publish_message(self):
        if self.count < 200:  # Limiting to 200 messages
            values = []
            for i in range(self.sample_rate):
                t = self.current_time + (i / self.sample_rate)
                value = self.offset + self.amplitude * math.sin(2 * math.pi * self.frequency * t)
                values.append(int(round(value)))  # Convert to integer

            self.current_time += 1   #


            temp=[]   # we are organizing channel data data[0,0,0,0],data[1,1,1,1],...
            for i in range(0, len(values), 1):
                for j in range(0,self.channel,1):
                    temp.append(int(round(values[i])))  # Convert to integer                    
            print(len(temp))

            binary_message = struct.pack(f"{len(temp)}H", *temp)  #convert decimal to binary format
            # logging.debug(f"messsage {binary_message}")
            print(len(temp))
            
            for topic in self.topics:
                try:
                    publish.single(topic, binary_message, hostname=self.broker, qos=1)
                    logging.info(f"[{self.count}] Published to {topic}: group at index {i} with {len(binary_message)} uint16_t values")
                except Exception as e:
                    logging.error(f"Failed to publish to {topic}: {str(e)}")

            self.count += 1
        else:
            self.timer.stop()
            logging.info("Publishing stopped after 200 messages.")

if __name__ == "__main__":
    app = QApplication([])
    broker = "192.168.1.173"
    topics = ["sarayu/tag2/topic2|m/s"]
    mqtt_publisher = MQTTPublisher(broker, topics)
    app.exec_()