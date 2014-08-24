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

import dbus
import dbus.service
import dbus.glib
import time
from polkit_helper import PolkitHelper

import pisi.api
import pisi.context
import pisi.config
import pisi.ui
import threading
import os
import os.path

class EvoUiMonitor(pisi.ui.UI):

    ok = None
    bad = None
    errors = False
    warnings = False
    last_error = None

    def __init__(self, ok, bad):
        self.ok = ok
        self.bad = bad

    def info(self, msg, verbose = False, noln = False):
        self.ok(msg)

    def debug(self, msg):
        "show debugging info"
        self.ok(msg)

    def warning(self,msg):
        self.ok(msg)
        warnings = True

    def error(self,msg):
        self.ok(msg)
        last_error = msg
        errors = True

    #FIXME: merge this with info, this just means "important message"
    def action(self,msg):
        self.ok(msg)


    def display_progress(self, **ka):
        self.ok(str(ka))

    def status(self, msg = None):
        "set status, if not given clear it"
        self.ok(msg)

    def notify(self, event, **keywords):
        "notify UI of a significant event"
        self.ok(event)
        self.ok(str(keywords))


class EvoAssistService(dbus.service.Object):

    ACTION_BUILD = "com.evolveos.evoassist.build"


    def __init__(self, loop):
        bus_name = dbus.service.BusName('com.evolveos.evoassist', bus = dbus.SystemBus())
        dbus.service.Object.__init__(self, bus_name, '/com/evolveos/EvoAssist')

        self.dbus_info = None

        self.polkit = PolkitHelper()

        self.pid_map = dict()
        self.loop = loop

        # Weird as it may sound this is a dict of lists.
        self.action_pids = dict()

    ''' Return the process ID for the specified connection '''
    def get_pid_from_connection(self, conn, sender):
        if self.dbus_info is None:
            self.dbus_info = dbus.Interface(conn.get_object('org.freedesktop.DBus',
                '/org/freedesktop/DBus/Bus', False), 'org.freedesktop.DBus')
        pid = self.dbus_info.GetConnectionUnixProcessID(sender)

        return pid


    ''' Very much around the houses. Monitor connection and hold onto process id's.
        This way we know who is already "authenticated" and who is not '''
    def register_connection_with_action(self, conn, sender, action_id):
        pid = self.get_pid_from_connection(conn, sender)

        if sender not in self.pid_map:
            print "Adding new sender: %s" % sender
            self.pid_map[sender] = pid

        if action_id not in self.action_pids:
            self.action_pids[action_id] = list()

        def cb(conn,sender):
            # Complicated, doesn't really need a lambda but in the future for whatever reason
            # we may need the sender and connection objects
            if conn == "":
                pid = None
                try:
                    pid = self.pid_map[sender]
                except:
                    # already removed, called twice.
                    return
                print "Disconnected process: %d" % pid

                self.pid_map.pop(sender)
                count = 0
                for i in self.action_pids[action_id]:
                    if i == pid:
                        self.action_pids[action_id].pop(count)
                        break
                    count += 1
                if len(self.pid_map) == 0:
                    self.ShutDown(None, None)
                del count
        conn.watch_name_owner(sender, lambda x: cb(x, sender))


    ''' Utility Method. Check if the sender is authorized to perform this action. If so, add them to a persistent list.
        List is persistent until this object is destroyed. Works via process ID's '''
    def persist_authorized(self, sender,conn, action_id):
        self.register_connection_with_action(conn,sender,action_id)

        pid = self.pid_map[sender]

        if not pid in self.action_pids[action_id]:
            if self.polkit.check_authorization(pid, action_id):
                self.action_pids[action_id].append(pid)
                return True # Authorized by PolKit!

            else:
                return False # Unauthorized by PolKit!
        else:
            return True # Already authorized by PolKit in this session

    def __build_package(self, pkgname):
        def ok(msg):
            self.Progress(0, msg);
        ui = EvoUiMonitor(ok, ok)
        pisi.context.ui = ui
        pisi.context.config.values.general.ignore_safety = True
        options = pisi.config.Options()
        options.output_dir = "/tmp/evoassist"
        if not os.path.exists(options.output_dir):
            os.mkdir(options.output_dir)
        pisi.api.set_options(options)

        def dummy():
            pass
        def dummy2():
            return True
        def dummy3():
            return False
        pisi.context.disable_keyboard_interrupts = dummy
        pisi.context.enable_keyboard_interrupts = dummy
        pisi.context.keyboard_interrupt_disabled = dummy2
        pisi.context.keyboard_interrupt_pending = dummy3
        pkg = None

        # Also hacky, idc.
        if pkgname == "google-chrome-stable":
            pkg = "https://raw.githubusercontent.com/evolve-os/3rd-party/master/network/web/browser/google-chrome-stable/pspec.xml"
        else:
            ok("ERROR: Unknown package description")
            ok("DONE")
            return

        # Ruthless I know.
        kids = os.listdir(options.output_dir)
        if len(kids) > 0:
            os.system("rm %s/*.eopkg" % options.output_dir)

        try:
            pisi.api.build(pkg)
        except Exception, e:
            print e
            ok("ERROR: %s" % e)
            ok("DONE")
            return
        try:
            kids = os.listdir(options.output_dir)
            pisi.api.install(["%s/%s" % (options.output_dir, kids[0])])
            os.system("rm %s/*.eopkg" % options.output_dir)
        except Exception:
            print e
            ok("ERROR: %s" % e)
            ok("DONE")
            return
        ok("DONE")

    ''' Request we build a package... '''
    @dbus.service.method('com.evolveos.evoassist', sender_keyword='sender', connection_keyword='conn', async_callbacks=('reply_handler', 'error_handler'), in_signature='s', out_signature='s')
    def BuildPackage(self, pkgname, sender=None, conn=None, reply_handler=None, error_handler=None):
        reply_handler("start")
        if not self.persist_authorized(sender, conn, self.ACTION_BUILD):
            error_handler("Not authorized")
            self.Progress(0, "DONE")
            return
        t = threading.Thread(target=self.__build_package, args=(pkgname,))
        t.start()

    ''' Shut down this service '''
    @dbus.service.method('com.evolveos.evoassist',  sender_keyword='sender',  connection_keyword='conn')
    def ShutDown(self, sender=None, conn=None):
        # No special checks required as of yet, but in future, flag quit for after finishing

        print "Shutdown requested"

        # you can't just do a sys.exit(), this causes errors for clients
        self.loop.quit()

    ''' Update info back to client '''
    @dbus.service.signal('com.evolveos.evoassist')
    def Progress(self, percent, message):
        return False
