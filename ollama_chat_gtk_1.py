import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango

import asyncio
from ollama import AsyncClient
import threading
import gc
import json
import subprocess
import requests

class ChatWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Zaawansowana Aplikacja Czatu")
        self.set_default_size(800, 600)

        self.available_models = []
        self.model_tags = {}
        self.fetch_models_and_tags()

        self.conversation_history = []
        self.temperature = 0.7

        # Tworzenie pól tekstowych
        self.chat_view = Gtk.TextView()
        self.chat_view.set_editable(False)
        self.chat_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.chat_buffer = self.chat_view.get_buffer()

        self.input_view = Gtk.TextView()
        self.input_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.input_buffer = self.input_view.get_buffer()

        # Tworzenie przycisków i kontrolek
        self.send_button = Gtk.Button.new_with_label("Wyślij")
        self.send_button.connect("clicked", self.send_message)

        self.auto_select_checkbox = Gtk.CheckButton(label="Auto-wybór modelu")
        self.auto_select_checkbox.set_active(True)

        self.clear_memory_button = Gtk.Button.new_with_label("Wyczyść pamięć")
        self.clear_memory_button.connect("clicked", self.clear_memory)

        self.clear_chat_button = Gtk.Button.new_with_label("Wyczyść czat")
        self.clear_chat_button.connect("clicked", self.clear_chat)

        self.save_button = Gtk.Button.new_with_label("Zapisz konwersację")
        self.save_button.connect("clicked", self.save_conversation)

        self.load_button = Gtk.Button.new_with_label("Wczytaj konwersację")
        self.load_button.connect("clicked", self.load_conversation)

        self.theme_button = Gtk.Button.new_with_label("Zmień motyw")
        self.theme_button.connect("clicked", self.toggle_theme)

        self.font_increase_button = Gtk.Button.new_with_label("Zwiększ czcionkę")
        self.font_increase_button.connect("clicked", self.increase_font_size)

        self.font_decrease_button = Gtk.Button.new_with_label("Zmniejsz czcionkę")
        self.font_decrease_button.connect("clicked", self.decrease_font_size)

        self.run_code_button = Gtk.Button.new_with_label("Uruchom kod Python")
        self.run_code_button.connect("clicked", self.run_python_code)

        self.download_model_button = Gtk.Button.new_with_label("Pobierz model")
        self.download_model_button.connect("clicked", self.show_download_dialog)

        self.serve_model_button = Gtk.Button.new_with_label("Uruchom serwer")
        self.serve_model_button.connect("clicked", self.serve_model)

        # Tworzenie rozwijanej listy modeli z zaznaczeniami
        self.model_tree_store = Gtk.TreeStore(bool, str, str)  # Dodano kolumnę dla tagu
        self.model_tree_view = Gtk.TreeView(model=self.model_tree_store)

        toggle_renderer = Gtk.CellRendererToggle()
        toggle_renderer.connect("toggled", self.on_model_toggled)
        column_toggle = Gtk.TreeViewColumn("Aktywny", toggle_renderer, active=0)
        self.model_tree_view.append_column(column_toggle)

        text_renderer = Gtk.CellRendererText()
        column_text = Gtk.TreeViewColumn("Model", text_renderer, text=1)
        self.model_tree_view.append_column(column_text)

        tag_renderer = Gtk.CellRendererText()
        column_tag = Gtk.TreeViewColumn("Tag", tag_renderer, text=2)
        self.model_tree_view.append_column(column_tag)

        for model in self.available_models:
            parent = self.model_tree_store.append(None, [False, model, ""])
            for tag in self.model_tags.get(model, []):
                self.model_tree_store.append(parent, [False, f"{model}:{tag}", tag])

        model_scroll = Gtk.ScrolledWindow()
        model_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        model_scroll.add(self.model_tree_view)
        model_scroll.set_min_content_height(100)

        # Układanie widgetów
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        chat_scroll = Gtk.ScrolledWindow()
        chat_scroll.add(self.chat_view)
        vbox.pack_start(chat_scroll, True, True, 0)

        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        input_box.pack_start(self.input_view, True, True, 0)
        input_box.pack_start(self.send_button, False, False, 0)
        vbox.pack_start(input_box, False, False, 0)

        control_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        control_box.pack_start(self.auto_select_checkbox, False, False, 0)
        control_box.pack_start(self.clear_memory_button, False, False, 0)
        control_box.pack_start(self.clear_chat_button, False, False, 0)
        control_box.pack_start(self.save_button, False, False, 0)
        control_box.pack_start(self.load_button, False, False, 0)
        vbox.pack_start(control_box, False, False, 0)

        ui_control_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        ui_control_box.pack_start(self.theme_button, False, False, 0)
        ui_control_box.pack_start(self.font_increase_button, False, False, 0)
        ui_control_box.pack_start(self.font_decrease_button, False, False, 0)
        ui_control_box.pack_start(self.run_code_button, False, False, 0)
        ui_control_box.pack_start(self.download_model_button, False, False, 0)
        ui_control_box.pack_start(self.serve_model_button, False, False, 0)
        vbox.pack_start(ui_control_box, False, False, 0)

        vbox.pack_start(model_scroll, False, True, 0)

        # Uruchamianie pętli zdarzeń asyncio w osobnym wątku
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self.start_loop, daemon=True)
        self.loop_thread.start()

    def fetch_models_and_tags(self):
        try:
            response = requests.get("https://ollama-models.zwz.workers.dev/")
            data = response.json()
            for model in data.get("models", []):
                self.available_models.append(model["name"])
                self.model_tags[model["name"]] = model["tags"]
        except Exception as e:
            print(f"Error fetching models and tags: {e}")

    def on_model_toggled(self, widget, path):
        iter = self.model_tree_store.get_iter(path)
        current_value = self.model_tree_store.get_value(iter, 0)
        self.model_tree_store.set_value(iter, 0, not current_value)

        # Jeśli to model główny, zaktualizuj wszystkie jego tagi
        if self.model_tree_store.iter_has_child(iter):
            child_iter = self.model_tree_store.iter_children(iter)
            while child_iter:
                self.model_tree_store.set_value(child_iter, 0, not current_value)
                child_iter = self.model_tree_store.iter_next(child_iter)
        # Jeśli to tag, zaktualizuj stan modelu głównego
        else:
            parent_iter = self.model_tree_store.iter_parent(iter)
            if parent_iter:
                any_child_active = False
                child_iter = self.model_tree_store.iter_children(parent_iter)
                while child_iter:
                    if self.model_tree_store.get_value(child_iter, 0):
                        any_child_active = True
                        break
                    child_iter = self.model_tree_store.iter_next(child_iter)
                self.model_tree_store.set_value(parent_iter, 0, any_child_active)

    def show_download_dialog(self, widget):
        dialog = Gtk.Dialog(title="Pobierz model", parent=self)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_OK, Gtk.ResponseType.OK)

        model_combo = Gtk.ComboBoxText()
        for model in self.available_models:
            model_combo.append_text(model)
        model_combo.set_active(0)

        tag_combo = Gtk.ComboBoxText()
        model_combo.connect("changed", self.update_tag_combo, tag_combo)
        self.update_tag_combo(model_combo, tag_combo)

        box = dialog.get_content_area()
        box.add(Gtk.Label("Wybierz model:"))
        box.add(model_combo)
        box.add(Gtk.Label("Wybierz tag:"))
        box.add(tag_combo)
        dialog.show_all()

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            selected_model = model_combo.get_active_text()
            selected_tag = tag_combo.get_active_text()
            threading.Thread(target=self.download_model, args=(f"{selected_model}:{selected_tag}",)).start()

        dialog.destroy()

    def update_tag_combo(self, model_combo, tag_combo):
        model = model_combo.get_active_text()
        tag_combo.remove_all()
        for tag in self.model_tags.get(model, []):
            tag_combo.append_text(tag)
        tag_combo.set_active(0)

    def start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def send_message(self, widget):
        start_iter = self.input_buffer.get_start_iter()
        end_iter = self.input_buffer.get_end_iter()
        user_message = self.input_buffer.get_text(start_iter, end_iter, True)
        self.input_buffer.set_text("")

        selected_model = self.get_selected_model_with_tag()

        self.conversation_history.append({'role': 'user', 'content': user_message})
        self.chat_buffer.insert_at_cursor(f"Użytkownik: {user_message}\n")
        self.chat_buffer.insert_at_cursor(f"Wybrany model: {selected_model}\n")
        asyncio.run_coroutine_threadsafe(self.get_response(selected_model), self.loop)

    def get_selected_model_with_tag(self):
        iter = self.model_tree_store.get_iter_first()
        while iter:
            if self.model_tree_store.get_value(iter, 0):  # jeśli model jest zaznaczony
                model = self.model_tree_store.get_value(iter, 1)
                child_iter = self.model_tree_store.iter_children(iter)
                while child_iter:
                    if self.model_tree_store.get_value(child_iter, 0):  # jeśli tag jest zaznaczony
                        tag = self.model_tree_store.get_value(child_iter, 2)
                        return f"{model}:{tag}"
                    child_iter = self.model_tree_store.iter_next(child_iter)
                return model  # jeśli żaden tag nie jest zaznaczony, zwróć sam model
            iter = self.model_tree_store.iter_next(iter)
        return self.available_models[0]  # jeśli nic nie jest zaznaczone, zwróć pierwszy dostępny model

    async def get_response(self, selected_model):
        async for part in await AsyncClient().chat(model=selected_model, messages=self.conversation_history, stream=True):
            content = part['message']['content']
            GLib.idle_add(self.chat_buffer.insert_at_cursor, content)
        GLib.idle_add(self.chat_buffer.insert_at_cursor, "\n")

        self.conversation_history.append({'role': 'assistant', 'content': content})
        self.trim_conversation_history()

    def clear_memory(self, widget):
        gc.collect()
        self.chat_buffer.insert_at_cursor("Pamięć wyczyszczona.\n")

    def clear_chat(self, widget):
        self.conversation_history = []
        self.chat_buffer.set_text("")
        self.chat_buffer.insert_at_cursor("Czat wyczyszczony.\n")

    def save_conversation(self, widget):
        dialog = Gtk.FileChooserDialog("Zapisz konwersację", self,
                                       Gtk.FileChooserAction.SAVE,
                                       (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_SAVE, Gtk.ResponseType.OK))
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            with open(dialog.get_filename(), 'w') as file:
                json.dump(self.conversation_history, file)
            self.chat_buffer.insert_at_cursor("Konwersacja zapisana.\n")
        dialog.destroy()

    def load_conversation(self, widget):
        dialog = Gtk.FileChooserDialog("Wczytaj konwersację", self,
                                       Gtk.FileChooserAction.OPEN,
                                       (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            with open(dialog.get_filename(), 'r') as file:
                self.conversation_history = json.load(file)
            self.chat_buffer.insert_at_cursor("Konwersacja wczytana.\n")
        dialog.destroy()

    def toggle_theme(self, widget):
        settings = Gtk.Settings.get_default()
        dark_mode = settings.get_property("gtk-application-prefer-dark-theme")
        settings.set_property("gtk-application-prefer-dark-theme", not dark_mode)

    def increase_font_size(self, widget):
        font_desc = self.chat_view.get_style_context().get_font(Gtk.StateFlags.NORMAL)
        font_desc.set_size(int(font_desc.get_size() * 1.1))
        self.chat_view.modify_font(font_desc)

    def decrease_font_size(self, widget):
        font_desc = self.chat_view.get_style_context().get_font(Gtk.StateFlags.NORMAL)
        font_desc.set_size(int(font_desc.get_size() * 0.9))
        self.chat_view.modify_font(font_desc)

    def run_python_code(self, widget):
        start_iter = self.input_buffer.get_start_iter()
        end_iter = self.input_buffer.get_end_iter()
        code = self.input_buffer.get_text(start_iter, end_iter, True)
        self.input_buffer.set_text("")

        try:
            exec_locals = {}
            exec(code, {}, exec_locals)
            output = exec_locals.get('output', 'Kod wykonany pomyślnie.')
        except Exception as e:
            output = f'Błąd wykonania kodu: {str(e)}'

        self.chat_buffer.insert_at_cursor(f"Wynik wykonania kodu:\n{output}\n")

    def serve_model(self, widget):
        try:
            command = ["ollama", "serve"]
            subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.chat_buffer.insert_at_cursor("Serwer modeli został uruchomiony.\n")
        except Exception as e:
            self.chat_buffer.insert_at_cursor(f"Wystąpił błąd podczas uruchamiania serwera: {str(e)}\n")

    def download_model(self, model_name):
        try:
            command = ["ollama", "pull", model_name]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            for line in process.stdout:
                GLib.idle_add(self.chat_buffer.insert_at_cursor, line)

            process.wait()
            if process.returncode == 0:
                GLib.idle_add(self.chat_buffer.insert_at_cursor, f"Model {model_name} został pobrany.\n")
            else:
                GLib.idle_add(self.chat_buffer.insert_at_cursor, f"Błąd podczas pobierania modelu {model_name}.\n")
        except Exception as e:
            GLib.idle_add(self.chat_buffer.insert_at_cursor, f"Wystąpił błąd: {str(e)}\n")

    def trim_conversation_history(self):
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-50:]

win = ChatWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
