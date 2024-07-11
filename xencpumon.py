#!/usr/bin/env python3

import gi, os, time, threading, subprocess
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

#import sys
#sys.settrace

class CoreWidget(Gtk.Box):
    
    def addFreq(self, freq):
        self.coreFreq = freq
        self.coreFreqLbl.set_text("Freq: " + str(self.coreFreq) + "GHz")

    def addLoad(self, load):
        self.coreLoad = load
        self.coreLoadLbl.set_text("Load: " + str(self.coreLoad) + "%")

        if(len(self.loads) < 30):
            self.loads.append(load)
        else:
            for i in range(0, 29):
                self.loads[i] = self.loads[i+1]
            self.loads[29] = load

        self.queue_draw()

    def __init__(self, coreId, type):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        
        self.orientation = Gtk.Orientation.VERTICAL
        self.coreId = coreId
        self.loads = []
        self.coreLoad = 0.0
        self.coreFreq = 0.0
        self.set_name(type)

        self.coreLoadLbl = Gtk.Label(label="Load: " + str(self.coreLoad) + "%")
        self.coreFreqLbl = Gtk.Label(label="Freq: " + str(self.coreFreq) + "GHz")
        self.pack_start(Gtk.Label(label="Core: " + str(self.coreId)), False, False, 0)
        self.pack_start(self.coreLoadLbl, False, False, 0)
        self.pack_start(self.coreFreqLbl, False, False, 0)
        
        self.loadBox = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.pack_start(self.loadBox, True, True, 0)
        self.loadBox.set_size_request(100,100)

        self.darea = Gtk.DrawingArea()
        self.darea.connect('draw', self.on_draw)
        self.loadBox.pack_start(self.darea, True, True, 0)

    def on_draw(self, window, cr):
        xoffset= 0
        for load in self.loads:
            if(load < 25):
                cr.set_source_rgba(0, 1.53, 0.77, 0.5)
            elif (load < 50):
                cr.set_source_rgba(2.30, 2.30, 0, 0.5)
            elif (load < 75):
                cr.set_source_rgba(2.30, 0.92, 0, 0.5)
            else:
                cr.set_source_rgba(2.55, 0.51, 0.51, 0.5)
            
            cr.rectangle(xoffset,100-load,2,load)
            cr.fill()
            xoffset += 3

class XenCpuMon(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self)
        self.tLock = threading.Lock()

        self.coreUI = []
        self.ecoreFreqAvg = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.ecoreLoadAvg = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.pcoreFreqAvg = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.pcoreLoadAvg = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        self.set_title("pyMenu")
        self.set_keep_above(True)
        self.set_decorated(False)
        self.set_property("skip-taskbar-hint", True)
        self.connect("destroy", Gtk.main_quit)
        self.connect('key-release-event', self.on_event_key_release)
        self.screen = self.get_screen()
        self.visual = self.screen.get_rgba_visual()
        self.set_visual(self.visual)
        
        self.totalCores = 32
        self.pCores = 16
        self.eCores = 16

        self.runDataThread = True
        self.step = 1
        self.stepAvg = 0

        self.resize(1600, 220)
        self.init_ui()

    def on_event_key_release(self, key, event):
        if Gdk.keyval_name(event.keyval) == 'Escape':
            os._exit(0)
    
    def init_ui(self):

        self.cpuBox = Gtk.Box.new(Gtk.Orientation.VERTICAL, spacing=5)
        self.cpuBox.set_name("cpuBox")
        self.cpuLbl = Gtk.Label(label="Intel i9 13900K / 32 Cores / 16 PCores / 16 ECores")
        self.cpuBox.pack_start(self.cpuLbl, True, True, 0)

        self.pcoreBox = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, spacing=5)
        self.pCoreLbl = Gtk.Label(label="16 PCores\nLoad: 0.0%\nFreq: 0.0GHz")
        self.pcoreBox.set_name("pCoreBox")
        self.pcoreBox.pack_start(self.pCoreLbl, True, True, 0)
        
        self.ecoreBox = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, spacing=5)
        self.eCoreLbl = Gtk.Label(label="16 ECores\nLoad: 0.0%\nFreq: 0.0GHz")
        self.ecoreBox.set_name("eCoreBox")
        self.ecoreBox.pack_start(self.eCoreLbl, True, True, 0)
        
        self.cpuBox.pack_start(self.pcoreBox, True, True, 0)
        self.cpuBox.pack_start(self.ecoreBox, True, True, 0)
        self.add(self.cpuBox)        

        for x in range(self.totalCores):
            if x < self.pCores:
                self.coreUI.append(CoreWidget(x, "pCoreLoadBox"))
                self.pcoreBox.pack_start(self.coreUI[x], True, True, 0)
            else:
                self.coreUI.append(CoreWidget(x, "eCoreLoadBox"))
                self.ecoreBox.pack_start(self.coreUI[x], True, True, 0)

        self.dataThread = threading.Thread(target=self.loadData, args=(False,))
        self.dataThread.start()


    def loadData(self, debug):

        while (self.runDataThread):
            if(debug):
                if self.step > 30:
                    self.step = 1
                lines = self.get_data_test("/home/user/src/xencpumon/xenpm/" + str(self.step) + ".log")
                self.step += 1
            else:
                lines = self.get_data()
        
            load = self.parse_data(lines, "C0")
            freq = self.parse_data(lines, "Avg")

            self.pcoreFreq = 0
            self.pcoreLoad = 0
            self.ecoreFreq = 0
            self.ecoreLoad = 0
            
            for i in range(0, 31):
                if(i < 16):
                    self.pcoreFreq += freq[i] / 100000
                    self.pcoreLoad += load[i]
                else:
                    self.ecoreFreq += freq[i] / 100000
                    self.ecoreLoad += load[i]

                self.coreUI[i].addLoad(load[i])
                self.coreUI[i].addFreq(freq[i] / 100000)

            if(self.stepAvg > 9):
                self.stepAvg = 0
            
            self.pcoreFreqAvg[self.stepAvg] = self.pcoreFreq
            self.pcoreLoadAvg[self.stepAvg] = self.pcoreLoad
            self.ecoreFreqAvg[self.stepAvg] = self.ecoreFreq
            self.ecoreLoadAvg[self.stepAvg] = self.ecoreLoad
            self.stepAvg += 1

            self.pCoreLbl.set_text("16 PCores\n" + self.pcoreLblCurrTxt() + self.pcoreLblAvgTxt())
            self.eCoreLbl.set_text("16 ECores\n" + self.ecoreLblCurrTxt() + self.ecoreLblAvgTxt())

            #self.pcoreBox.queue_draw()
            #self.ecoreBox.queue_draw()
            time.sleep(5)


    def refreshUI(self):
        self.pcoreBox.queue_draw()
        self.ecoreBox.queue_draw()

    def pcoreLblCurrTxt(self):
        return "\nCurrent values   \nLoad: " + str(round(self.pcoreLoad / 16,2)) + "%\nFreq: " + str(round(self.pcoreFreq / 16,2)) + " GHz"
    
    def pcoreLblAvgTxt(self):
        pcoreFreqVal = 0.0
        pcoreLoadVal = 0.0

        for val in self.pcoreLoadAvg:
            pcoreLoadVal += val

        for val in self.pcoreFreqAvg:
            pcoreFreqVal += val

        return "\n\nLast 10 avg values   \nLoad: " + str(round(pcoreLoadVal / 160,2)) + "%\nFreq: " + str(round(pcoreFreqVal / 160,2)) + " GHz"
    
    def ecoreLblAvgTxt(self):
        ecoreFreqVal = 0.0
        ecoreLoadVal = 0.0

        for val in self.ecoreLoadAvg:
            ecoreLoadVal += val

        for val in self.ecoreFreqAvg:
            ecoreFreqVal += val

        return "\n\nLast 10 avg values   \nLoad: " + str(round(ecoreLoadVal / 160,2)) + "%\nFreq: " + str(round(ecoreFreqVal / 160,2)) + " GHz"
    
    def ecoreLblCurrTxt(self):
        return "\nCurrent values   \nLoad: " + str(round(self.ecoreLoad / 16,2)) + "%\nFreq: " + str(round(self.ecoreFreq / 16,2)) + " GHz"

    def get_data_test(self, path):
        lines = []
        f = open(path, "r")
        for ln in f.readlines():
            line = ln.strip()
            if line != "":
                lines.append(line)
        f.close()

        return lines

    def get_data(self):
        lines = []
        result = subprocess.getoutput("xenpm start 1")
        #result = os.system("xenpm start 1")
        output = result.split('\n')
        for ln in output:
            line = ln.strip()
            if line != "":
                lines.append(line)
        
        return lines
    
    def parse_data(self, lines, type):
        list = []
    
        for line in lines:
            elements = line.split('\t')
            if line.strip().startswith(type):
                load = int(elements[1].strip()) / 10
                list.append(load)
            
        return list
    

window = XenCpuMon()
window.set_position(Gtk.WindowPosition.CENTER)

CSS_DATA = b"""
    #cpuBox { border-radius: 8px; padding: 3px; color: white; }

    #pCoreBox { border-width: 1px; border-color: #9D6161; border-style: solid; border-radius: 8px; padding: 3px; color: white; }
    #pCoreLoadBox { border-width: 1px; border-color: #A44040; border-style: solid; border-radius: 8px; padding: 3px; color: white; }

    #eCoreBox { border-width: 1px; border-color: #374F6A; border-style: solid; border-radius: 8px; padding: 3px; color: white; }
    #eCoreLoadBox { border-width: 1px; border-color: #35679F; border-style: solid; border-radius: 8px; padding: 3px; color: white; }
    
    box { margin: 3px 3px 3px 3px; }
    window { border-radius: 8px; }
"""
#window { border-radius: 8px; background-color: rgba(46, 51, 64, 0.85); }
css = Gtk.CssProvider()
css.load_from_data(CSS_DATA)
style_context = window.get_style_context()
style_context.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

settings = Gtk.Settings.get_default()
settings.set_property("gtk-theme-name", "Arc-Dark")
settings.set_property("gtk-application-prefer-dark-theme", True)

window.show_all()
Gtk.main()

