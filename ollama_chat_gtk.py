import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

import asyncio
from ollama import AsyncClient
import threading

class ChatWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Chat App")
        self.set_default_size(600, 400)

        # Tworzenie pól tekstowych
        self.chat_view = Gtk.TextView()
        self.chat_view.set_editable(False)
        self.chat_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.chat_buffer = self.chat_view.get_buffer()

        self.input_view = Gtk.TextView()
        self.input_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.input_buffer = self.input_view.get_buffer()

        # Tworzenie przycisków
        self.send_button = Gtk.Button.new_with_label("Wyślij")
        self.send_button.connect("clicked", self.send_message)

        # Układanie widgetów
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        chat_scroll = Gtk.ScrolledWindow()
        chat_scroll.add(self.chat_view)
        vbox.pack_start(chat_scroll, True, True, 0)

        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, 
spacing=6)
        input_box.pack_start(self.input_view, True, True, 0)
        input_box.pack_start(self.send_button, False, False, 0)
        vbox.pack_start(input_box, False, False, 0)

        # Uruchamianie pętli zdarzeń asyncio w osobnym wątku
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self.start_loop, 
daemon=True)
        self.loop_thread.start()

    def start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def send_message(self, widget):
        start_iter = self.input_buffer.get_start_iter()
        end_iter = self.input_buffer.get_end_iter()
        user_message = self.input_buffer.get_text(start_iter, end_iter, 
True)
        self.input_buffer.set_text("")

        self.chat_buffer.insert_at_cursor(f"Użytkownik: {user_message}\n")
        asyncio.run_coroutine_threadsafe(self.get_response(user_message), 
self.loop)

    async def get_response(self, user_message):
        message = {'role': 'user', 'content': user_message}
        async for part in await AsyncClient().chat(model='llama3', 
messages=[message], stream=True):
            content = part['message']['content']
            GLib.idle_add(self.chat_buffer.insert_at_cursor, content)
        GLib.idle_add(self.chat_buffer.insert_at_cursor, "\n")

window = ChatWindow()
window.connect("destroy", Gtk.main_quit)
window.show_all()
Gtk.main()

