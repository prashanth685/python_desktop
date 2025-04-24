import paho.mqtt.client as mqtt
from PyQt5.QtCore import QThread, QObject, pyqtSignal, QTimer
import logging
import struct
from datetime import datetime
import time

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

class MQTTWorker(QObject):
    data_received = pyqtSignal(str, list)
    connected = pyqtSignal()
    connection_failed = pyqtSignal(str)
    stopped = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, db, project_name, broker="192.168.1.171", port=1883):
        super().__init__()
        self.db = db
        self.project_name = project_name
        self.broker = broker
        self.port = port
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.subscribed_topics = set()
        self.running = False
        self.retry_interval = 5

    def start(self):
        if not self.running:
            self.running = True
            self.connect_with_retry()
            self.client.loop_start()
            logging.info("MQTT worker loop started")

    def stop(self):
        if self.running:
            self.running = False
            self.client.loop_stop()
            self.client.disconnect()
            self.subscribed_topics.clear()
            logging.info("MQTT worker loop stopped and client disconnected")
            self.stopped.emit()

    def connect_with_retry(self):
        max_retries = 3
        attempt = 0
        while self.running and attempt < max_retries:
            try:
                self.client.connect(self.broker, self.port, keepalive=60)
                logging.info(f"Connected to MQTT broker at {self.broker}:{self.port}")
                self.connected.emit()
                return
            except Exception as e:
                attempt += 1
                logging.error(f"Failed to connect to MQTT broker (attempt {attempt}/{max_retries}): {str(e)}")
                if attempt < max_retries:
                    time.sleep(self.retry_interval)
                else:
                    self.connection_failed.emit(f"Failed to connect to MQTT broker after {max_retries} attempts: {str(e)}")
                    return

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info(f"Connected to MQTT broker with result code {rc}")
            self.subscribe_to_topics()
            self.connected.emit()
        else:
            logging.error(f"Connection failed with result code {rc}")
            self.connection_failed.emit(f"Connection failed with result code {rc}")

    def subscribe_to_topics(self):
        tags = list(self.db.tags_collection.find({"project_name": self.project_name}))
        if not tags:
            logging.warning(f"No tags found for project {self.project_name}")
            return
        for tag in tags:
            topic = tag["tag_name"]
            if topic not in self.subscribed_topics:
                self.client.subscribe(topic, qos=1)
                self.subscribed_topics.add(topic)
                logging.info(f"Subscribed to topic: {topic}")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload

        logging.debug(f"Received message on {topic}, payload size: {len(payload)} bytes")

        try:
            if len(payload) % 2 != 0:
                raise ValueError("Payload size is not a multiple of 2, cannot unpack as uint16_t")
            values = list(struct.unpack(f"{len(payload) // 2}H", payload))
            logging.debug(f"First 5 values: {values[:5]}")
            
            if not values:
                raise ValueError("Empty or invalid payload")
            
            tag_name = topic
            timestamp = datetime.now().isoformat()
            
            success, message = self.db.update_tag_value(self.project_name, tag_name, values, timestamp)
            if success:
                logging.info(f"Stored {len(values)} values for {tag_name}")
                self.data_received.emit(tag_name, values)
            else:
                logging.error(f"Failed to store values: {message}")
                self.error_occurred.emit(f"Failed to store values for {tag_name}: {message}")
        
        except struct.error as se:
            logging.error(f"Failed to unpack binary data on {topic}: {str(se)}")
            self.error_occurred.emit(f"Failed to unpack binary data on {topic}: {str(se)}")
        except Exception as e:
            logging.error(f"Error processing message on {topic}: {str(e)}")
            self.error_occurred.emit(f"Error processing message on {topic}: {str(e)}")

class MQTTHandler(QObject):
    data_received = pyqtSignal(str, list)
    connection_status = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, db, project_name):
        super().__init__()
        self.db = db
        self.project_name = project_name
        self.thread = QThread()
        self.worker = MQTTWorker(db, project_name)
        self.worker.moveToThread(self.thread)
        self.running = False

        self.worker.data_received.connect(self.data_received)
        self.worker.connected.connect(self.on_connected)
        self.worker.connection_failed.connect(self.on_connection_failed)
        self.worker.error_occurred.connect(self.error_occurred)
        self.worker.stopped.connect(self.on_worker_stopped)
        self.thread.started.connect(self.worker.start)

    def start(self):
        if not self.running:
            self.thread.start()
            self.running = True
            logging.info("MQTTHandler started")

    def stop(self):
        if self.running:
            self.worker.stop()
            self.thread.quit()
            self.thread.wait()
            self.running = False
            logging.info("MQTTHandler stopped")

    def on_connected(self):
        self.connection_status.emit("Connected to MQTT broker")

    def on_connection_failed(self, error):
        self.connection_status.emit(error)
        QTimer.singleShot(5000, self.worker.connect_with_retry)

    def on_worker_stopped(self):
        self.running = False