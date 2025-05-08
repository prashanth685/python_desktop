import paho.mqtt.client as mqtt
from PyQt5.QtCore import QThread, QObject, pyqtSignal, QTimer
import logging
import struct
from datetime import datetime
import time
import random

# logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

class MQTTWorker(QObject):
    data_received = pyqtSignal(str, list)
    connected = pyqtSignal()
    connection_failed = pyqtSignal(str)
    stopped = pyqtSignal()
    error_occurred = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(self, db, project_name, broker="192.168.1.175", port=1883):
        super().__init__()
        self.db = db
        self.project_name = project_name
        self.broker = broker
        self.port = port
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.subscribed_topics = set()
        self.pending_subscriptions = set()
        self.running = False
        self.base_retry_interval = 5
        self.max_retries = 5
        self.retry_count = 0

    def start(self):
        if not self.running:
            self.running = True
            self.status_update.emit("Initiating connection to MQTT broker...")
            self.connect_with_retry()
            self.client.loop_start()
            logging.info("MQTT worker loop started")

    def stop(self):
        if self.running:
            self.running = False
            self.client.loop_stop()
            self.client.disconnect()
            self.subscribed_topics.clear()
            self.pending_subscriptions.clear()
            self.retry_count = 0
            logging.info("MQTT worker loop stopped and client disconnected")
            self.stopped.emit()

    def connect_with_retry(self):
        if not self.running:
            return
        self.retry_count = 0
        self.attempt_connection()

    def attempt_connection(self):
        if self.retry_count >= self.max_retries:
            error_msg = f"Failed to connect to MQTT broker after {self.max_retries} attempts."
            logging.error(error_msg)
            self.connection_failed.emit(error_msg)
            self.status_update.emit(error_msg)
            return

        try:
            self.client.connect(self.broker, self.port, keepalive=60)
            logging.info(f"Connected to MQTT broker at {self.broker}:{self.port}")
            self.retry_count = 0
            self.connected.emit()
            self.status_update.emit("Connected to MQTT broker")
        except Exception as e:
            self.retry_count += 1
            error_msg = f"Attempt {self.retry_count}/{self.max_retries} failed: {str(e)}"
            logging.error(error_msg)
            self.status_update.emit(error_msg)
            # Exponential backoff with jitter
            delay = self.base_retry_interval * (2 ** (self.retry_count - 1)) + random.uniform(0, 0.1)
            QTimer.singleShot(int(delay * 1000), self.attempt_connection)

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info(f"Connected to MQTT broker with result code {rc}")
            self.subscribe_to_topics()
            self.connected.emit()
            self.status_update.emit("Connected to MQTT broker")
            self.retry_count = 0
            # Process any pending subscriptions
            if self.pending_subscriptions:
                for topic in list(self.pending_subscriptions):
                    self.client.subscribe(topic, qos=1)
                    self.subscribed_topics.add(topic)
                    logging.info(f"Subscribed to pending topic: {topic}")
                self.pending_subscriptions.clear()
        else:
            error_msg = f"Connection failed with result code {rc}"
            logging.error(error_msg)
            self.connection_failed.emit(error_msg)
            self.status_update.emit(error_msg)
            self.attempt_connection()

    def subscribe_to_topics(self):
        tags = list(self.db.tags_collection.find({"project_name": self.project_name}))
        if not tags:
            logging.warning(f"No tags found for project {self.project_name}")
            self.status_update.emit(f"No tags found for project {self.project_name}")
            return
        for tag in tags:
            topic = tag["tag_name"]
            if topic not in self.subscribed_topics:
                try:
                    self.client.subscribe(topic, qos=1)
                    self.subscribed_topics.add(topic)
                    logging.info(f"Subscribed to topic: {topic}")
                    self.status_update.emit(f"Subscribed to topic: {topic}")
                except Exception as e:
                    logging.error(f"Failed to subscribe to {topic}: {str(e)}")
                    self.pending_subscriptions.add(topic)
                    self.status_update.emit(f"Queued subscription for {topic}")

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
                logging.info(f"Processed {len(values)} values for {tag_name}")
                self.data_received.emit(tag_name, values)
            else:
                logging.error(f"Failed to process values: {message}")
                self.error_occurred.emit(f"Failed to process values for {tag_name}: {message}")
        
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
        self.worker.status_update.connect(self.connection_status)
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

    def on_worker_stopped(self):
        self.running = False