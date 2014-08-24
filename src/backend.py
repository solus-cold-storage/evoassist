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

import sys

sys.path.append("/usr/lib/evoassist")

try:
    import gi.repository
    from gi.repository import GObject
    from evoassist import EvoAssistService
    import dbus.mainloop
except Exception, e:
    print e
    sys.exit(1)

if __name__ == '__main__':
    GObject.threads_init()
    dbus.mainloop.glib.threads_init()
    loop = GObject.MainLoop()
    try:
        service = EvoAssistService(loop)
        loop.run()
    except Exception, e:
        print e
    finally:
        loop.quit()
    sys.exit(0)
