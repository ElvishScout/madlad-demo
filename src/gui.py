import os
import threading
import inspect
import ctypes
from tkinter import *
from tkinter import font
from tkinter.ttk import *

from translator import *
from languages import languages

font_path = os.environ.get("FONT_PATH") or os.path.join(base_path, "./fonts/SourceHanSansSC-Regular.otf")


# Thanks to https://stackoverflow.com/users/13618/philippe-f
class ThreadWithExc(threading.Thread):
    """A thread class that supports raising an exception in the thread from
    another thread.
    """

    @staticmethod
    def _async_raise(tid, exctype: type):
        """Raises an exception in the threads with id tid"""
        if not inspect.isclass(exctype):
            raise TypeError("Only types can be raised (not instances)")
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), ctypes.py_object(exctype))
        if res == 0:
            raise ValueError("invalid thread id")
        elif res != 1:
            # "if it returns a number greater than one, you're in trouble,
            # and you should call it again with exc=NULL to revert the effect"
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), None)
            raise SystemError("PyThreadState_SetAsyncExc failed")

    def _get_my_tid(self):
        """determines this (self's) thread id

        CAREFUL: this function is executed in the context of the caller
        thread, to get the identity of the thread represented by this
        instance.
        """
        if not self.is_alive():  # Note: self.isAlive() on older version of Python
            raise threading.ThreadError("the thread is not active")

        # do we have it cached?
        if hasattr(self, "_thread_id"):
            return self._thread_id

        # no, look for it in the _active dict
        for tid, tobj in threading._active.items():
            if tobj is self:
                self._thread_id = tid
                return tid

        # TODO: in python 2.6, there's a simpler way to do: self.ident

        raise AssertionError("could not determine the thread's id")

    def raise_exc(self, exctype):
        """Raises the given exception type in the context of this thread.

        If the thread is busy in a system call (time.sleep(),
        socket.accept(), ...), the exception is simply ignored.

        If you are sure that your exception should terminate the thread,
        one way to ensure that it works is:

            t = ThreadWithExc( ... )
            ...
            t.raise_exc( SomeException )
            while t.isAlive():
                time.sleep( 0.1 )
                t.raise_exc( SomeException )

        If the exception is to be caught by the thread, you need a way to
        check that your thread has caught it.

        CAREFUL: this function is executed in the context of the
        caller thread, to raise an exception in the context of the
        thread represented by this instance.
        """
        self.__class__._async_raise(self._get_my_tid(), exctype)


# Thanks to https://stackoverflow.com/users/25195202/cryan
class AutoSuggestCombobox(Combobox):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self._completion_list = []
        self._hits = []
        self._hit_index = 0
        self.position = 0
        self.bind("<KeyRelease>", self._handle_keyrelease)
        self.bind("<FocusOut>", self._handle_focusout)
        self.bind("<FocusIn>", self._handle_focusin)
        self.bind("<Tab>", self._handle_tab)
        self.bind("<Return>", self._handle_return)  # bind Enter key
        self.bind("<Down>", self._down_arrow)  # bind Up arrow key
        self.bind("<Up>", self._up_arrow)
        self.bind("<Button-1>", self._handle_click)  # bind mouse click
        master.bind("<Button-1>", self._handle_root_click)  # bind mouse click on root window
        self._popup_menu = None

    def set_completion_list(self, completion_list):
        """Set the list of possible completions."""
        self._completion_list = sorted(completion_list)
        self["values"] = self._completion_list

    def _handle_keyrelease(self, event):
        """Handle key release events."""
        value = self.get()
        cursor_index = self.index("insert")

        if value == "":
            self._hits = self._completion_list
        else:
            # Determine the word before the cursor
            before_cursor = value[:cursor_index].rsplit(" ", 1)[-1]

            # Filter suggestions based on the word before the cursor
            self._hits = [item for item in self._completion_list if item.lower().startswith(before_cursor.lower())]

        # Ignore Down and Up arrow key presses
        if event.keysym in ["Down", "Up", "Tab", "Return"]:
            return

        if self._hits:
            self._show_popup(self._hits)

    def _show_popup(self, values):
        """Display the popup listbox."""
        if self._popup_menu:
            self._popup_menu.destroy()

        self._popup_menu = Toplevel(self)
        self._popup_menu.wm_overrideredirect(True)
        self._popup_menu.config(bg="black")

        # Add a frame with a black background to create the border effect
        popup_frame = Frame(self._popup_menu, borderwidth=0.1)
        popup_frame.pack(padx=1, pady=(1, 1), fill="both", expand=True)

        listbox = Listbox(
            popup_frame,
            borderwidth=0,
            relief="flat",
            bg="white",
            selectbackground="#0078d4",
            bd=0,
            highlightbackground="black",
        )
        scrollbar = Scrollbar(popup_frame, orient="vertical", command=listbox.yview)
        listbox.config(yscrollcommand=scrollbar.set)

        for value in values:
            listbox.insert("end", value)

        listbox.bind("<ButtonRelease-1>", self._on_listbox_select)
        listbox.bind("<FocusOut>", self._on_listbox_focusout)
        listbox.bind("<Motion>", self._on_mouse_motion)

        # Automatically select the first entry if no mouse hover has occurred yet
        if not listbox.curselection():
            listbox.selection_set(0)

        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Adjust popup width to match entry box
        popup_width = self.winfo_width()
        self._popup_menu.geometry(f"{popup_width}x165")

        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        self._popup_menu.geometry(f"+{x}+{y}")

    def _on_listbox_select(self, event):
        """Select a value from the listbox."""
        widget = event.widget
        selection = widget.curselection()
        if selection:
            value = widget.get(selection[0])
            self._select_value(value)

    def _on_mouse_motion(self, event):
        """Handle mouse motion over the listbox."""
        widget = event.widget
        index = widget.nearest(event.y)
        widget.selection_clear(0, "end")
        widget.selection_set(index)

    def _on_listbox_focusout(self, event):
        """Handle listbox losing focus."""
        if self._popup_menu:
            self._popup_menu.destroy()
            self._popup_menu = None

    def _select_value(self, value):
        """Select a value from the popup listbox."""
        self.set(value)
        self.icursor("end")  # Move cursor to the end
        self.selection_range(0, "end")  # Select entire text
        if self._popup_menu:
            self._popup_menu.destroy()
            self._popup_menu = None

    def _handle_focusout(self, event):
        """Handle focus out events."""
        if self._popup_menu:
            try:
                if not self._popup_menu.winfo_containing(event.x_root, event.y_root):
                    self._popup_menu.destroy()
                    self._popup_menu = None
            except TclError:
                pass

    def _handle_focusin(self, event):
        """Handle focus in events."""
        if self._popup_menu:
            self._popup_menu.destroy()
            self._popup_menu = None

    def _handle_tab(self, event):
        """Handle Tab key press."""
        if self._popup_menu:
            listbox = self._popup_menu.winfo_children()[0].winfo_children()[0]
            current_selection = listbox.curselection()
            if current_selection:
                value = listbox.get(current_selection[0])
                self._select_value(value)
        return "break"

    def _handle_return(self, event):
        """Handle Enter key press."""
        if self._popup_menu:
            listbox = self._popup_menu.winfo_children()[0].winfo_children()[0]
            current_selection = listbox.curselection()
            if current_selection:
                value = listbox.get(current_selection[0])
                self._select_value(value)
                return "break"

    def _down_arrow(self, event):
        """Handle down arrow key press."""
        if self._popup_menu:
            listbox = self._popup_menu.winfo_children()[0].winfo_children()[0]
            current_selection = listbox.curselection()
            if current_selection:
                current_index = current_selection[0]
                next_index = (current_index + 1) % len(self._hits)
                listbox.selection_clear(0, "end")
                listbox.selection_set(next_index)
                listbox.activate(next_index)
                return "break"  # prevent default behavior

    def _up_arrow(self, event):
        """Handle up arrow key press."""
        if self._popup_menu:
            listbox = self._popup_menu.winfo_children()[0].winfo_children()[0]
            current_selection = listbox.curselection()
            if current_selection:
                current_index = current_selection[0]
                next_index = (current_index - 1) % len(self._hits)
                listbox.selection_clear(0, "end")
                listbox.selection_set(next_index)
                listbox.activate(next_index)
                return "break"  # prevent default behavior

    def _handle_click(self, event):
        """Handle mouse click events."""
        value = self.get()
        if value == "":
            self._hits = self._completion_list
        else:
            self._hits = [item for item in self._completion_list if item.lower().startswith(value.lower())]

        if self._hits:
            self._show_popup(self._hits)

    def _handle_root_click(self, event):
        """Handle mouse click events on root window."""
        if self._popup_menu:
            x, y = event.x_root, event.y_root
            x0, y0, x1, y1 = (
                self.winfo_rootx(),
                self.winfo_rooty(),
                self.winfo_rootx() + self.winfo_width(),
                self.winfo_rooty() + self.winfo_height(),
            )
            if not (x0 <= x <= x1 and y0 <= y <= y1):
                self._popup_menu.destroy()
                self._popup_menu = None


class Gui(Tk):
    def __init__(self, translator: Translator):
        super().__init__()
        self.translator = translator
        self.trans_thread: ThreadWithExc | None = None
        self.signal = [False]

        self.title("Translator")
        self.geometry("800x600")

        self.create_widget()

    def create_widget(self):
        self.rowconfigure(index=0, weight=1)
        self.rowconfigure(index=2, weight=1)
        self.columnconfigure(index=2, weight=1)

        frame_input = Frame(self, height=0, relief="solid", border=1)
        frame_input.grid(row=0, column=0, columnspan=4, padx=5, pady=5, sticky="nsew")
        frame_input.rowconfigure(index=0, weight=1)
        frame_input.columnconfigure(index=0, weight=1)

        text_input = self.text_input = Text(frame_input, relief="flat", takefocus=0)
        text_input.grid(row=0, column=0, sticky="nsew")

        scroll_input = Scrollbar(frame_input, orient="vertical")
        scroll_input.grid(row=0, column=1, sticky="ns")

        text_input.config(yscrollcommand=scroll_input.set)
        scroll_input.config(command=text_input.yview)

        label_lang = Label(self, text="Target Language")
        label_lang.grid(row=1, column=0, padx=5, pady=2)

        combo_lang = self.combo_lang = AutoSuggestCombobox(self, takefocus=0)
        combo_lang.grid(row=1, column=1, padx=5, pady=2)

        button_trans = self.button_trans = Button(self, text="Translate", takefocus=0, command=self.on_button_click)
        button_trans.grid(row=1, column=3, padx=5, pady=2)

        frame_output = Frame(self, height=0, relief="solid", border=1)
        frame_output.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky="nsew")
        frame_output.rowconfigure(index=0, weight=1)
        frame_output.columnconfigure(index=0, weight=1)

        text_output = self.text_output = Text(frame_output, relief="flat", takefocus=0)
        text_output.grid(row=0, column=0, sticky="nsew")

        scroll_output = Scrollbar(frame_output, orient="vertical")
        scroll_output.grid(row=0, column=1, sticky="ns")

        text_output.config(yscrollcommand=scroll_output.set, state="disabled")
        scroll_output.config(command=text_output.yview)

        grip_grip = Sizegrip(self)
        grip_grip.grid(row=3, column=0, columnspan=4, sticky="e")

        lang_list = list(languages.keys())
        lang_list.sort()
        combo_lang.set_completion_list(lang_list)

    def on_button_click(self):
        if self.trans_thread is None:
            target = languages.get(self.combo_lang.get())
            if target is None:
                return

            text = self.text_input.get(0.0, "end")
            self.trans_thread = ThreadWithExc(target=self.translate, args=[target, text], daemon=True)
            self.trans_thread.start()
            self.button_trans.config(text="Stop")
        else:
            self.trans_thread.raise_exc(ValueError)

    def translate(self, target: str, text: str):
        self.text_output.config(state="normal")
        self.text_output.delete(0.0, "end")
        self.text_output.config(state="disabled")
        try:
            for i, line in enumerate(text.strip().split("\n")):
                output: str
                if line == "":
                    output = ""
                else:
                    output = self.translator.translate(target, line)
                self.text_output.config(state="normal")
                if i != 0:
                    self.text_output.insert("end", "\n")
                self.text_output.insert("end", output)
                self.text_output.config(state="disabled")
        except ValueError:
            pass

        self.trans_thread = None
        self.button_trans.config(text="Translate")


# Thanks to https://stackoverflow.com/users/754254/felipe
def load_font(font_path: str, private=True, enumerable=False):
    """
    Makes fonts located in file `fontpath` available to the font system.

    `private`     if True, other processes cannot see this font, and this
                  font will be unloaded when the process dies
    `enumerable`  if True, this font will appear when enumerating fonts

    See https://msdn.microsoft.com/en-us/library/dd183327(VS.85).aspx

    """

    flags = (0x10 if private else 0) | (0x20 if not enumerable else 0)
    numFontsAdded = ctypes.windll.gdi32.AddFontResourceExA(bytes(font_path, encoding="utf-8"), flags, 0)
    return bool(numFontsAdded)


if __name__ == "__main__":
    ctypes.windll.shcore.SetProcessDpiAwareness(1)

    translator = Translator(model_path)
    gui = Gui(translator)

    load_font(font_path)
    font.nametofont(f"TkDefaultFont", gui).configure(family="Source Han Sans SC", size=10)
    font.nametofont(f"TkTextFont", gui).configure(family="Source Han Sans SC", size=10)
    font.nametofont(f"TkFixedFont", gui).configure(family="Source Han Sans SC", size=12)

    gui.mainloop()
