from locust import HttpUser, between, events, task
from websocket import create_connection
import gevent
import ssl

class WebSocketLoadTest(HttpUser):
    wait_time = between(1, 5)  # Simulates user wait time between tasks

    def on_start(self):
        """
        This method runs when a user is spawned. It initializes a WebSocket connection.
        """
        self.ws_url = "ws://your-websocket-server-url"
        try:
            self.ws = create_connection(
                self.ws_url,
                sslopt={"cert_reqs": ssl.CERT_NONE}  # Ignore SSL verification (for testing only)
            )
            self.spawn_listener()
        except Exception as e:
            print(f"WebSocket connection error: {e}")
            self.ws = None

    def spawn_listener(self):
        """
        Spawns a listener to continuously receive messages from the WebSocket server.
        """
        def _receive():
            while True:
                try:
                    message = self.ws.recv()
                    events.request_success.fire(
                        request_type="WebSocket Receive",
                        name="Receive Message",
                        response_time=0,  # Replace with actual timing if needed
                        response_length=len(message),
                    )
                except Exception as e:
                    events.request_failure.fire(
                        request_type="WebSocket Receive",
                        name="Receive Message",
                        response_time=0,
                        response_length=0,
                        exception=e,
                    )
                    break

        gevent.spawn(_receive)

    @task
    def send_message(self):
        """
        Sends a message to the WebSocket server.
        """
        if self.ws:
            try:
                self.ws.send('{"type": "test", "content": "Hello, server!"}')
                events.request_success.fire(
                    request_type="WebSocket Send",
                    name="Send Message",
                    response_time=0,  # Replace with actual timing if needed
                    response_length=0,
                )
            except Exception as e:
                events.request_failure.fire(
                    request_type="WebSocket Send",
                    name="Send Message",
                    response_time=0,
                    response_length=0,
                    exception=e,
                )
    
    def on_stop(self):
        """
        Cleanup method called when the user stops.
        """
        if self.ws:
            self.ws.close()
