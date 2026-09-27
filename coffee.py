#!/usr/bin/env python3

import re
import shutil
import subprocess
import threading

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib


class CoffeeGUI(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="com.example.Coffee"
        )

        self.package_names = []

    def do_activate(self):
        self.window = Gtk.ApplicationWindow(
            application=self
        )
        self.window.set_title("Coffee")
        self.window.set_default_size(950, 650)

        main_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8
        )

        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)

        # Header
        title = Gtk.Label()
        title.set_markup(
            "<span size='xx-large' weight='bold'>☕ Coffee</span>"
        )
        title.set_xalign(0)
        main_box.append(title)

        subtitle = Gtk.Label(
            label="A graphical Homebrew package manager"
        )
        subtitle.set_xalign(0)
        main_box.append(subtitle)

        # Package entry
        self.package_entry = Gtk.Entry()
        self.package_entry.set_placeholder_text(
            "Enter a package name, for example: neovim"
        )
        main_box.append(self.package_entry)

        # Search field
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(
            "Filter installed packages..."
        )
        self.search_entry.connect(
            "search-changed",
            self.on_search_changed
        )
        main_box.append(self.search_entry)

        # Installed package list
        self.package_list = Gtk.ListBox()
        self.package_list.set_selection_mode(
            Gtk.SelectionMode.SINGLE
        )

        list_scroll = Gtk.ScrolledWindow()
        list_scroll.set_vexpand(True)
        list_scroll.set_child(self.package_list)
        main_box.append(list_scroll)

        # Package action buttons
        package_buttons = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8
        )

        install_button = Gtk.Button(label="Install")
        install_button.connect(
            "clicked",
            self.on_install_clicked
        )

        uninstall_button = Gtk.Button(label="Uninstall")
        uninstall_button.connect(
            "clicked",
            self.on_uninstall_clicked
        )

        upgrade_button = Gtk.Button(label="Upgrade Selected")
        upgrade_button.connect(
            "clicked",
            self.on_upgrade_clicked
        )

        package_buttons.append(install_button)
        package_buttons.append(uninstall_button)
        package_buttons.append(upgrade_button)

        main_box.append(package_buttons)

        # Homebrew action buttons
        homebrew_buttons = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8
        )

        update_button = Gtk.Button(label="Update Homebrew")
        update_button.connect(
            "clicked",
            self.on_update_homebrew_clicked
        )

        upgrade_all_button = Gtk.Button(label="Upgrade All")
        upgrade_all_button.connect(
            "clicked",
            self.on_upgrade_all_clicked
        )

        refresh_button = Gtk.Button(label="Refresh List")
        refresh_button.connect(
            "clicked",
            self.on_refresh_clicked
        )

        homebrew_buttons.append(update_button)
        homebrew_buttons.append(upgrade_all_button)
        homebrew_buttons.append(refresh_button)

        main_box.append(homebrew_buttons)

        # Output label
        output_label = Gtk.Label(
            label="Command output:"
        )
        output_label.set_xalign(0)
        main_box.append(output_label)

        # Output text area
        self.output_view = Gtk.TextView()
        self.output_view.set_editable(False)
        self.output_view.set_monospace(True)
        self.output_view.set_wrap_mode(
            Gtk.WrapMode.WORD_CHAR
        )

        output_scroll = Gtk.ScrolledWindow()
        output_scroll.set_vexpand(True)
        output_scroll.set_child(self.output_view)

        main_box.append(output_scroll)

        self.window.set_child(main_box)
        self.window.present()

        # Check for Homebrew
        if not shutil.which("brew"):
            self.set_output(
                "Homebrew was not found in PATH.\n\n"
                "Install Homebrew first, then restart Coffee."
            )
            return

        self.refresh_packages()

    def set_output(self, text):
        buffer = self.output_view.get_buffer()
        buffer.set_text(text)

    def append_output(self, text):
        buffer = self.output_view.get_buffer()
        end_iter = buffer.get_end_iter()
        buffer.insert(end_iter, text)

    def run_brew(self, arguments):
        try:
            process = subprocess.Popen(
                ["brew"] + arguments,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            output_lines = []

            for line in process.stdout:
                output_lines.append(line)

                current_output = "".join(output_lines)

                GLib.idle_add(
                    self.set_output,
                    current_output
                )

            process.wait()

            return (
                process.returncode,
                "".join(output_lines)
            )

        except Exception as error:
            return (
                1,
                f"Error running Homebrew:\n{error}"
            )

    def refresh_packages(self):
        self.set_output(
            "Loading installed Homebrew packages..."
        )

        def worker():
            return_code, output = self.run_brew(
                ["list", "--formula"]
            )

            if return_code == 0:
                packages = [
                    line.strip()
                    for line in output.splitlines()
                    if line.strip()
                ]

                GLib.idle_add(
                    self.display_packages,
                    packages
                )

                GLib.idle_add(
                    self.set_output,
                    f"Loaded {len(packages)} installed formulae."
                )
            else:
                GLib.idle_add(
                    self.set_output,
                    output or "Could not load installed packages."
                )

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    def display_packages(self, packages):
        self.package_names = packages

        # Clear the current list
        while True:
            child = self.package_list.get_first_child()

            if child is None:
                break

            self.package_list.remove(child)

        search_text = self.search_entry.get_text().lower()

        for package in packages:
            if search_text:
                if search_text not in package.lower():
                    continue

            row = Gtk.ListBoxRow()
            row.package_name = package

            label = Gtk.Label(label=package)
            label.set_xalign(0)
            label.set_margin_top(6)
            label.set_margin_bottom(6)
            label.set_margin_start(8)
            label.set_margin_end(8)

            row.set_child(label)
            self.package_list.append(row)

    def on_search_changed(self, search_entry):
        self.display_packages(self.package_names)

    def get_package_name(self):
        # First use the text entered by the user
        package = self.package_entry.get_text().strip()

        # If empty, use the selected package
        if not package:
            selected_row = self.package_list.get_selected_row()

            if selected_row is not None:
                package = selected_row.package_name

        return package

    def valid_package_name(self, package):
        return re.fullmatch(
            r"[A-Za-z0-9@+._/-]+",
            package
        ) is not None

    def run_package_action(self, action):
        package = self.get_package_name()

        if not package:
            self.set_output(
                "Enter a package name or select a package."
            )
            return

        if not self.valid_package_name(package):
            self.set_output(
                "Invalid package name."
            )
            return

        self.set_output(
            f"Running: brew {action} {package}\n"
        )

        def worker():
            return_code, output = self.run_brew(
                [action, package]
            )

            if return_code == 0:
                message = (
                    f"\nCompleted successfully:\n\n"
                    f"{output}"
                )
            else:
                message = (
                    f"\nCommand failed:\n\n"
                    f"{output}"
                )

            GLib.idle_add(
                self.append_output,
                message
            )

            if action in (
                "install",
                "uninstall",
                "upgrade"
            ):
                GLib.idle_add(
                    self.refresh_packages
                )

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    def run_global_command(self, arguments, description):
        self.set_output(
            f"{description}\n\n"
        )

        def worker():
            return_code, output = self.run_brew(
                arguments
            )

            if return_code == 0:
                message = (
                    f"{description} completed successfully.\n\n"
                    f"{output}"
                )
            else:
                message = (
                    f"{description} failed.\n\n"
                    f"{output}"
                )

            GLib.idle_add(
                self.set_output,
                message
            )

            if arguments[0] in (
                "update",
                "upgrade"
            ):
                GLib.idle_add(
                    self.refresh_packages
                )

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    def on_install_clicked(self, button):
        self.run_package_action("install")

    def on_uninstall_clicked(self, button):
        self.run_package_action("uninstall")

    def on_upgrade_clicked(self, button):
        self.run_package_action("upgrade")

    def on_update_homebrew_clicked(self, button):
        self.run_global_command(
            ["update"],
            "Updating Homebrew..."
        )

    def on_upgrade_all_clicked(self, button):
        self.run_global_command(
            ["upgrade"],
            "Upgrading all Homebrew packages..."
        )

    def on_refresh_clicked(self, button):
        self.refresh_packages()


def main():
    app = CoffeeGUI()
    app.run()


if __name__ == "__main__":
    main()
