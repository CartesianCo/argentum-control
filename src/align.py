#GUI for Argentum Alignment

from Tkinter import *
import tkFileDialog
import Image
import ImageTk
import os

class AlignWizard(Tk):

    def __init__(self, parent):
        Tk.__init__(self, parent)
        self.parent = parent
        self.initialize()

    def initialize(self):
        #canvas and button creation
        self.configLabel = Label(self, font="Helvetica", text="\nYour Argentum will have now printed the following. "
                                                              "Select the best print for both horizontal and vertical "
                                                              "alignment.\nYou can increase the resolution of the "
                                                              "alignment shift by clicking in-between two values. You "
                                                              "will then need to generate a new hex file.\n\nOnce you "
                                                              "have selected the best alignment values, click Complete."
                                                              "\n\n",
                                 justify=LEFT)
        self.horzLabel = Label(self, font="Helvetica", text="\nHorizontal Alignment", justify=LEFT, fg="red")
        self.horzcan = Canvas(self, width=840, height=180)
        self.horzgoback = Button(self, text="Back", state=DISABLED, command=self.hgoback)
        self.vertLabel = Label(self, font="Helvetica", text="\nVertical Alignment", justify=LEFT, fg="red")
        self.vertcan = Canvas(self, width=840, height=180)
        self.vertgoback = Button(self, text="Back", state=DISABLED, command=self.vgoback)
        self.genhex = Button(self, text="Generate HEX File", command=self.bothhex)
        self.genhexh = Button(self, text="Generate Horizontal Only HEX File", command=self.horzhex)
        self.genhexv = Button(self, text="Generate Vertical Only HEX File", command=self.verthex)
        self.complete = Button(self, text="COMPLETE!", command=self.complete, state=DISABLED)
        self.backbtn = Button(self, text="< Back", command=self.goback)
        
        #dynamic widgets
        self.placecan = Canvas(self, width=840, height=400)
        self.onit = Button(self, text="On it", command=self.to_prep)

        #determine file directory path
        self.modpath = self.determine_path()
        
        #thumbnail image linking
        self.horzIm = ImageTk.PhotoImage(Image.open(self.modpath+"/img/Horizontal.png"))
        self.horzImH = ImageTk.PhotoImage(Image.open(self.modpath+"/img/Horizontal H.png"))
        self.horzImS = ImageTk.PhotoImage(Image.open(self.modpath+"/img/Horizontal S.png"))
        self.vertIm = ImageTk.PhotoImage(Image.open(self.modpath+"/img/Vertical.png"))
        self.vertImH = ImageTk.PhotoImage(Image.open(self.modpath+"/img/Vertical H.png"))
        self.vertImS = ImageTk.PhotoImage(Image.open(self.modpath+"/img/Vertical S.png"))
        
        #additional images
        self.SDload = ImageTk.PhotoImage(Image.open(self.modpath+"/img/HEX to SD.png"))
        self.place = ImageTk.PhotoImage(Image.open(self.modpath+"/img/Paper Place.png"))
        self.wizard = ImageTk.PhotoImage(Image.open(self.modpath+"/img/wizard.png"))
        self.arc = ImageTk.PhotoImage(Image.open(self.modpath+"/img/arc.png"))
        self.HEXload = ImageTk.PhotoImage(Image.open(self.modpath+"/img/ARC to HEX.png"))
        self.processing = ImageTk.PhotoImage(Image.open(self.modpath+"/img/processingoptions.png"))
        
        
        #available horzontal offset configurations
        self.horzdefault = ["H736", "H731", "H726", "H721", "H716"]
        self.horz1 = ["H736", "H735", "H734", "H733", "H732"]
        self.horz2 = ["H731", "H730", "H729", "H728", "H727"]
        self.horz3 = ["H725", "H724", "H723", "H722", "H721"]
        self.horz4 = ["H720", "H719", "H718", "H717", "H716"]
        
        
        #available vertical offset configurations
        self.vertdefault = ["V10", "V5", "V0", "V-5", "V-10"]
        self.vert1 = ["V10", "V9", "V8", "V7", "V6"]
        self.vert2 = ["V5", "V4", "V3", "V2", "V1"]
        self.vert3 = ["V-1", "V-2", "V-3", "V-4", "V-5"]
        self.vert4 = ["V-6", "V-7", "V-8", "V-9", "V-10"]
        
        
        #increase resolution rectangle naming
        self.datGap = ["G1", "G2", "G3", "G4"]
        
        
        #reset current offset configurations to default
        self.currenth = self.horzdefault
        self.currentv = self.vertdefault
        
        #bind mouse clicks to canvas
        self.vertcan.bind("<Button-1>", self.click)
        self.horzcan.bind("<Button-1>", self.click)

        #polulate the canvas
        self.welcome()

    def click(self, event):
        if self.vertcan.find_withtag(CURRENT):
            vertcurrent = self.vertcan.find_withtag(CURRENT)[0]
            if vertcurrent in self.vertcan.find_withtag("V"):
                if self.vertcan.find_withtag("VS1"):
                    if vertcurrent == self.vertcan.find_withtag("VS1")[0]:
                        return
                    else:
                        self.vertcan.itemconfig("VS1", image=self.vertIm, activeimage=self.vertImH, tag="V")
                        self.vertcan.itemconfig(CURRENT, image=self.vertImS, activeimage=self.vertImS, tag=("VS1", "V"))
                else:
                    self.vertcan.itemconfig(CURRENT, image=self.vertImS, activeimage=self.vertImS, tag=("VS1", "V"))
                self.vAlign = self.currentv[self.vertcan.find_withtag("V").index(vertcurrent)][1:]
            elif vertcurrent in self.vertcan.find_withtag("G"):
                if vertcurrent == self.vertcan.find_withtag("G1")[0]:
                    self.vrelabel(self.vert1)
                    self.currentv = self.vert1
                elif vertcurrent == self.vertcan.find_withtag("G2")[0]:
                    self.vrelabel(self.vert2)
                    self.currentv = self.vert2
                elif vertcurrent == self.vertcan.find_withtag("G3")[0]:
                    self.vrelabel(self.vert3)
                    self.currentv = self.vert3
                elif vertcurrent == self.vertcan.find_withtag("G4")[0]:
                    self.vrelabel(self.vert4)
                    self.currentv = self.vert4

        if self.horzcan.find_withtag(CURRENT):
            horzcurrent = self.horzcan.find_withtag(CURRENT)[0]
            if horzcurrent in self.horzcan.find_withtag("H"):
                if self.horzcan.find_withtag("HS1"):
                    if horzcurrent == self.horzcan.find_withtag("HS1")[0]:
                        return
                    else:
                        self.horzcan.itemconfig("HS1", image=self.horzIm, activeimage=self.horzImH, tag="H")
                        self.horzcan.itemconfig(CURRENT, image=self.horzImS, activeimage=self.horzImS, tag=("HS1", "H"))
                else:
                    self.horzcan.itemconfig(CURRENT, image=self.horzImS, activeimage=self.horzImS, tag=("HS1", "H"))
                self.hAlign = self.currenth[self.horzcan.find_withtag("H").index(horzcurrent)][1:]
            elif horzcurrent in self.horzcan.find_withtag("G"):
                if horzcurrent == self.horzcan.find_withtag("G1")[0]:
                    self.hrelabel(self.horz1)
                    self.currenth = self.horz1
                elif horzcurrent == self.horzcan.find_withtag("G2")[0]:
                    self.hrelabel(self.horz2)
                    self.currenth= self.horz2
                elif horzcurrent == self.horzcan.find_withtag("G3")[0]:
                    self.hrelabel(self.horz3)
                    self.currenth = self.horz3
                elif horzcurrent == self.horzcan.find_withtag("G4")[0]:
                    self.hrelabel(self.horz4)
                    self.currenth = self.horz4

        if (self.vAlign is not None) and (self.hAlign is not None):
            self.complete.config(state=NORMAL)

    def vrelabel(self, idlist):
        for i in range(5):
            self.vertcan.itemconfig(str(i) + "v", text=idlist[i], tag=(idlist[i], str(i) + "v"))
        for i in range(4):
            self.vertcan.itemconfig(self.datGap[i], state=HIDDEN)
        if self.vertcan.find_withtag("VS1"):
                self.vertcan.itemconfig("VS1", image=self.vertIm, activeimage=self.vertImH, tag="V")
        self.vertgoback.config(state=NORMAL)
        self.vAlign = None
        self.complete.config(state=DISABLED)

    def hrelabel(self, idlist):
        for i in range(5):
            self.horzcan.itemconfig(str(i) + "h", text=idlist[i], tag=(idlist[i], str(i) + "h"))
        for i in range(4):
            self.horzcan.itemconfig(self.datGap[i], state=HIDDEN)
        if self.horzcan.find_withtag("HS1"):
                self.horzcan.itemconfig("HS1", image=self.horzIm, activeimage=self.horzImH, tag="H")
        self.horzgoback.config(state=NORMAL)
        self.hAlign = None
        self.complete.config(state=DISABLED)

    def vgoback(self):
        for i in range(5):
            self.vertcan.itemconfig(str(i) + "v", text=self.vertdefault[i], tag=(self.vertdefault[i], str(i) + "v"))
        for i in range(4):
            self.vertcan.itemconfig(self.datGap[i], state=NORMAL)
        if self.vertcan.find_withtag("VS1"):
                    self.vertcan.itemconfig("VS1", image=self.vertIm, activeimage=self.vertImH, tag="V")
        self.vertgoback.config(state=DISABLED)
        self.currentv = self.vertdefault
        self.vAlign = None
        self.complete.config(state=DISABLED)

    def hgoback(self):
        for i in range(5):
            self.horzcan.itemconfig(str(i) + "h", text=self.horzdefault[i], tag=(self.horzdefault[i], str(i) + "h"))
        for i in range(4):
            self.horzcan.itemconfig(self.datGap[i], state=NORMAL)
        if self.horzcan.find_withtag("HS1"):
                    self.horzcan.itemconfig("HS1", image=self.horzIm, activeimage=self.horzImH, tag="H")
        self.horzgoback.config(state=DISABLED)
        self.currenth = self.horzdefault
        self.hAlign = None
        self.complete.config(state=DISABLED)

    def mergehex(self, hextup, type):

        #open all of the required hex files
        f1 = open(self.modpath+"/hex/" + hextup[0] + ".hex", "r")
        f2 = open(self.modpath+"/hex/" + hextup[1] + ".hex", "r")
        f3 = open(self.modpath+"/hex/" + hextup[2] + ".hex", "r")
        f4 = open(self.modpath+"/hex/" + hextup[3] + ".hex", "r")
        f5 = open(self.modpath+"/hex/" + hextup[4] + ".hex", "r")

        #read files
        g1 = f1.read()
        g2 = f2.read()
        g3 = f3.read()
        g4 = f4.read()
        g5 = f5.read()

        #remove final lines
        g1 = self.remove_end(g1)
        g2 = self.remove_end(g2)
        g3 = self.remove_end(g3)
        g4 = self.remove_end(g4)
        g5 = self.remove_end(g5)

        #correct ending returns
        g1 = g1 + "\nM X 0\nM Y -100"
        g2 = g2 + "\nM X 0\nM Y -100"
        g3 = g3 + "\nM X 0\nM Y -100"
        g4 = g4 + "\nM X 0\nM Y -100"

        if type=="first":
            g1 = "M Y 12600\n" + g1

        #close hex files
        f1.close()
        f2.close()
        f3.close()
        f4.close()
        f5.close()

        return g1 + g2 + g3 + g4 + g5

    def doublehex(self, h1, h2):
        h1 = self.remove_end(h1) + "M X 0\nM Y 100\n"
        return h1 + h2

    def hextofile(self, hex, name):
        hexfile = tkFileDialog.asksaveasfile(initialfile=name, mode='w', defaultextension=".hex")
        if hexfile is None:
            return False
        hexfile.write(hex)
        hexfile.close()
        return True

    def remove_last_line(self, s):
        return s[:s.rfind('\n')]

    def remove_end(self, s):
        return self.remove_last_line(self.remove_last_line(self.remove_last_line(self.remove_last_line(s))))

    def welcome(self):

        self.placecan.create_image(420, 200, image=self.wizard, anchor="center", tag="central")
        self.placecan.create_text(420, 355, font="Helvetica", tag="centraltext",
                            text="Welcome to the Cartridge Alignment Wizard!")
        self.onit.config(text="Go!", command=self.to_Basic)
        self.placecan.pack()
        self.onit.pack()

    def to_Basic(self):
        self.placecan.itemconfig("central", image=self.HEXload)
        self.placecan.itemconfig("centraltext",
                            text="First, we will print a grid of basic alignment values. To generate this file, click below.")
        self.onit.config(text="Generate Alignment Hex", command=self.bothhex)

    def setup_canv(self):

        #remove any other windows
        self.hideInitial()

        #pack all current items
        self.configLabel.pack()
        self.horzLabel.pack()
        self.horzcan.pack()
        self.horzgoback.pack()
        self.vertLabel.pack()
        self.vertcan.pack()
        self.vertgoback.pack()
        self.genhex.pack(side=LEFT)
        self.genhexh.pack(side=LEFT)
        self.genhexv.pack(side=LEFT)
        self.complete.pack(side=TOP)

        self.horzgoback.config(state=DISABLED)
        self.vertgoback.config(state=DISABLED)
        self.vAlign = None
        self.hAlign = None
        self.complete.config(state=DISABLED)

        #thumbnail image generation
        for i in range(5):
            self.horzcan.create_image(i*165+15, 15, image=self.horzIm, anchor="nw", activeimage=self.horzImH, tag="H")
            self.horzcan.create_text(i*165+90, 175, font="Helvetica", text=self.horzdefault[i], tag=(self.horzdefault[i], str(i) + "h"))

        for i in range(5):
            self.vertcan.create_image(i*165+15, 15, image=self.vertIm, anchor="nw", activeimage=self.vertImH, tag="V")
            self.vertcan.create_text(i*165+90, 175, font="Helvetica", text=self.vertdefault[i], tag=(self.vertdefault[i], str(i) + "v"))

        for i in range(4):
            self.horzcan.create_rectangle(i*165+167, 16, i*165+167+10, 163, fill="white", outline="white", width=3,
                                     activeoutline="blue", activedash=(10, 12), tag=(self.datGap[i], self.datGap[i][0]))

        for i in range(4):
            self.vertcan.create_rectangle(i*165+167, 16, i*165+167+10, 163, fill="white", outline="white", width=3,
                                     activeoutline="blue", activedash=(10, 12), tag=(self.datGap[i], self.datGap[i][0]))

    def to_SD(self):
        self.placecan.itemconfig("central", image=self.SDload)
        self.placecan.itemconfig("centraltext", text="Copy Output.hex from this directory to your Argentum SD card")
        self.onit.config(text="On it", command=self.to_prep())
        self.placecan.pack()
        self.onit.pack()

    def to_prep(self):
        self.placecan.itemconfig("central", image=self.place)
        self.placecan.itemconfig("centraltext", text="Place a piece of paper in your Argentum as shown.")
        self.placecan.create_text(420, 380, text="Then prime and insert Ascorbic and Silver cartridges.", font="helvetica", tag="aditional")
        self.onit.config(text="All over it", command=self.to_ARC)

    def to_ARC(self):
        self.placecan.delete("aditional")
        self.placecan.itemconfig("central", image=self.arc)
        self.placecan.itemconfig("centraltext" ,text="Use ArC to print this hex file onto the paper. Make sure your Argentum is calibrated and homed before printing.", width=400)
        self.onit.config(text="Alright!", command=self.setup_canv)
        return

    def horzhex(self):
        proceed = self.hextofile(self.mergehex(self.currenth, "first"), "Output")
        if proceed:
            self.hideall()
            self.to_SD()

    def verthex(self):
        proceed = self.hextofile(self.mergehex(self.currentv, "first"), "Output")
        if proceed:
            self.hideall()
            self.to_SD()

    def bothhex(self):
        proceed = self.hextofile(self.doublehex(self.mergehex(self.currentv, "first"), self.mergehex(self.currenth, "second")), "Output")
        if proceed:
            self.hideall()
            self.to_SD()

    def hideall(self):
        self.horzcan.delete(ALL)
        self.vertcan.delete(ALL)
        self.configLabel.pack_forget()
        self.horzLabel.pack_forget()
        self.vertLabel.pack_forget()
        self.horzcan.pack_forget()
        self.vertcan.pack_forget()
        self.horzgoback.pack_forget()
        self.vertgoback.pack_forget()
        self.genhex.pack_forget()
        self.genhexh.pack_forget()
        self.genhexv.pack_forget()
        self.complete.pack_forget()

    def hideInitial(self):
        self.placecan.pack_forget()
        self.onit.pack_forget()
        self.backbtn.pack_forget()

    def determine_path(self):
        try:
            root = __file__
            if os.path.islink(root):
                root = os.path.realpath(root)
            return os.path.dirname(os.path.abspath(root))
        except:
            sys.exit()

    def complete(self):
        self.hideall()
        self.placecan.itemconfig("central", image=self.processing)
        self.placecan.create_text(450, 165, text=self.vAlign, fill="red", tag="vAlign")
        self.placecan.create_text(450, 285, text=self.hAlign, fill="red", tag="hAlign")
        self.placecan.itemconfig("centraltext", state=HIDDEN)
        self.placecan.create_text(400, 380, text="Open ARC, type in these values and you're all done!", tag="additional")
        self.onit.config(text="Nailed it.", command=self.quit)
        self.placecan.pack()
        self.backbtn.pack(side=LEFT)
        self.onit.pack()

    def goback(self):
        self.placecan.delete("vAlign")
        self.placecan.delete("hAlign")
        self.placecan.delete("additional")
        self.placecan.itemconfig("centraltext", state=NORMAL)
        self.setup_canv()


#main loop
if __name__ == "__main__":
    app = AlignWizard(None)
    app.title('ARC Alignment Wizard')
    os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' ''')
    app.mainloop()
