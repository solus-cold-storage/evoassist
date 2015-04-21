#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright 2014 Ikey Doherty <ikey.doherty@gmail.com>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#

import gi.repository
from gi.repository import Gtk, Gat, GObject
import dbus
from dbus.mainloop.glib import DBusGMainLoop

import pisi
import pisi.db

class EvoWelcome(Gat.SidebarWindow):

    soft_select = False
    software_page = None

    spinners = list()

    def __init__(self):
        Gat.SidebarWindow.__init__(self)
        self.connect('delete-event', Gtk.main_quit)
        self.set_sidebar_title("Tasks")
        self.set_icon_name("info")
        self.set_size_request(400, 400)

        stack = Gtk.Stack()
        stack.set_border_width(6)
        stack.set_transition_type(Gtk.StackTransitionType.SLIDE_UP_DOWN)   
        self.get_content_area().pack_start(stack, True, True, 0)
        sidebar = Gat.Sidebar()
        sidebar.set_stack(stack)
        self.get_sidebar().add(sidebar)
        self.get_sidebar().set_reveal_child(True)

        # pages..
        welcome = self.create_welcome_page()
        stack.add_named(welcome, "welcome")
        stack.child_set_property(welcome, "title", "Welcome")
        self.set_title("Welcome")

        '''updates = Gtk.VBox(0)
        stack.add_named(updates, "updates")
        stack.child_set_property(updates, "title", "Check for updates")'''

        # proprietary
        software = self.create_software_page()
        self.software_page = software
        stack.add_named(software, "software")
        stack.child_set_property(software, "title", "Get software")

        # support
        support = self.create_support_page()
        stack.add_named(support, "support")
        stack.child_set_property(support, "title", "Get support")

        stack.connect("notify::visible-child-name", self.on_notify)
        stack.set_visible_child_name("welcome")

        self.show_all()

        for spin in self.spinners:
            spin.hide()
        self.tick.hide()

    def on_notify(self, o, p):
        v = GObject.Value()
        v.init(GObject.TYPE_STRING)
        child = o.get_visible_child()
        if child is None:
            return
        title = o.child_get_property(child, "title", v)
        self.set_title(v.get_string())

    def create_welcome_page(self):
        layout = Gtk.VBox(0)

        version = "Evolve OS"
        with open("/etc/evolveos-release", "r") as inp:
            lines = inp.readlines()
            version = lines[0].replace("\r","").replace("\n", "")

        banner = Gtk.Label("<big>%s</big>" % version)
        banner.set_use_markup(True)
        layout.pack_start(banner, False, False, 5)
        layout.set_halign(Gtk.Align.START)

        words = """
Welcome to the Solus Operating System. Please note this project is still in its infancy,
and users are encouraged to report any issues that they find. Also note,
this tool is also brand new and has limitations and bugs.

<i>Negativity aside...</i> we really hope you enjoy using Evolve OS, and
look forward to your support and feedback in making the distribution better
for future users!"""
        content = Gtk.Label(words)
        content.set_halign(Gtk.Align.START)
        content.set_valign(Gtk.Align.START)
        content.set_use_markup(True)

        layout.pack_start(content, True, True, 5)

        return layout

    def create_item(self, name, icon_name, description, link=None):
        grid = Gtk.Grid()
        grid.set_border_width(16)
        grid.set_row_spacing(4)
        grid.set_column_spacing(16)
    
        if link is not None:
            label = Gtk.LinkButton.new_with_label(link, "<big>%s</big>" % name)
            label.get_child().set_use_markup(True)
        else:
            label = Gtk.Label("<big>%s</big>" % name)
            label.set_use_markup(True)
        label.set_alignment(0.0, 0.5)
        icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DIALOG)
        desc = Gtk.Label(description)
        desc.get_style_context().add_class("dim-label")
        desc.set_alignment(0.0, 0.5)
        if link is not None:
            desc.set_property("margin-left", 8)
        grid.attach(icon, 0, 0, 1, 2)
        grid.attach(label, 1, 0, 1, 1)
        grid.attach(desc, 1, 1, 1, 1)

        return grid

    def create_software_page(self):
        scroller = Gtk.ScrolledWindow(None, None)
        scroller.set_shadow_type(Gtk.ShadowType.IN)
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        lbox = Gtk.ListBox()
        scroller.add(lbox)

        item = self.create_item("Google Chrome", "google-chrome", "Google Chrome is a free to use web browser")
        wrap = Gtk.HBox(0)
        wrap.pack_start(item, True, True, 0)
        spin = Gtk.Spinner()
        self.install_btn = Gtk.Button("Install")
        self.install_btn.get_style_context().add_class("suggested-action")
        self.install_btn.set_valign(Gtk.Align.CENTER)
        self.install_btn.connect("clicked", self.do_install)
        wrap.pack_end(self.install_btn, False, False, 2)
        wrap.pack_end(spin, False, False, 2)
        tick = Gtk.Image.new_from_icon_name("emblem-ok-symbolic", Gtk.IconSize.BUTTON)
        wrap.pack_end(tick, False, False, 2)
        lbox.add(wrap)

        # HACK #
        self.spinner = spin
        self.tick = tick
        self.spinners.append(spin)

        lbox.connect("row-selected", self.on_row)
        return scroller

    def on_row(self, thing, row):
        self.soft_select = row

    def do_install(self, w):
        self.install_btn.set_sensitive(False)
        self.spinner.show()
        self.spinner.start()
        bus = dbus.SystemBus()
        obj = bus.get_object("com.evolveos.evoassist", "/com/evolveos/EvoAssist")
        iface = dbus.Interface(obj, "com.evolveos.evoassist")
        iface.connect_to_signal("Progress", self.do_prog)
        iface.BuildPackage("google-chrome-stable", reply_handler=self.on_repl, error_handler=self.on_err)

    def create_support_page(self):
        layout = Gtk.VBox(0)

        irc = self.create_item("Get help on IRC in real time", "im-irc", "Talk to other Evolve OS users in real time", link="irc://irc.freenode.net/#solus")
        layout.pack_start(irc, False, False, 10)
        forums = self.create_item("Get help on our forums", "applications-internet", "Help others or get helped, leave a post on the forums", link="https://solus-project.com/forums")
        layout.pack_start(forums, False, False, 10)
        bugs = self.create_item("Report a bug", "dialog-error", "Reporting bugs helps us to improve the project for everyone", link="https://github.com/solus-project/repository/issues")
        layout.pack_start(bugs, False, False, 10)

        return layout
    def on_repl(self, o):      
        pass      
        #print "ok %s" % str(o)

    def on_err(self, o):
        self.install_btn.set_sensitive(True)
        #print "error %s" % str(o)

    def do_prog(self, pct, message):
        if str(message).startswith("ERROR: "):
            content = message.split("ERROR: ")[1]
            d = Gtk.MessageDialog(self, Gtk.DialogFlags.DESTROY_WITH_PARENT | Gtk.DialogFlags.MODAL,
                                  Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE,
                                  content)
            d.run()
            d.destroy()

        if (pct == 0 and message == "DONE"):
            # yes.. that is "completion" ...
            self.install_btn.set_sensitive(True)
            self.spinner.stop()
            self.spinner.hide()
            db = pisi.db.installdb.InstallDB()
            if db.has_package("google-chrome-stable"):
                self.install_btn.hide()
                self.tick.show()
        # for the curious/debugs
        #print message

if __name__ == "__main__":
    DBusGMainLoop(set_as_default=True)
    win = EvoWelcome()
    Gtk.main()

