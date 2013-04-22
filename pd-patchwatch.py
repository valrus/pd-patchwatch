# python3

import argparse
import cmd
import os
import sys
import textwrap
from tempfile import mkdtemp, NamedTemporaryFile
from functools import partial

from pypd import PdParser
from pd import pd
import pdgui

PD_BIN = os.environ.get("PD_BIN", os.path.join(os.sep, "usr", "bin", "pd"))
PD_SEND = os.path.join(os.environ.get("PD_BIN", os.path.dirname(PD_BIN)),
                       "pdsend")
PATCH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "patches")
INIT_PATCH = "receive.pd"


class PdPatch(object):
    modDir = None

    def kill(self):
        self.pd.send(
            " ".join([";", self.fileName, "menuclose;"])
        )
        os.unlink(os.path.join(self.modDir, self.fileName))
        return True

    def __init__(self, patchPath=None, pd=None, channel=1):
        self.objects = 0
        self.channel = channel
        self.lines = []
        self.gui = {}
        self.pd = pd

        if patchPath:
            patchDir, patchName = os.path.split(patchPath)
            if patchName.endswith(".pd"):
                fileName, self.name = (patchName, os.path.splitext(patchName))
            else:
                fileName, self.name = patchName + ".pd", patchName

            p = PdParser(os.path.join(patchDir, fileName))
            p.add_filter_method(self.get_line)
            p.add_filter_method(self.found_object, type="#X")
            p.add_filter_method(self.found_io, type="#X", object="adc~")
            p.add_filter_method(self.found_io, type="#X", object="dac~")
            for cls in pdgui.PdGui.__subclasses__():
                p.add_filter_method(partial(self.found_gui, cls),
                                    type="#X", object=cls.__name__)
            print(p.parse(), "elements in this patch.")

            self.fileName = fileNameInsert(fileName, channel)
            with open(os.path.join(PdPatch.modDir,
                                   self.fileName), "w") as patch:
                self.dir, self.fileName = os.path.split(patch.name)
                while self.lines:
                    patch.write(self.lines.pop(0) + ";\n")
            print(open(os.path.join(self.dir, self.fileName), "r").read())
            self.pd.send(
                " ".join([";", "pd open", self.fileName, self.dir, ";"])
            )

    def get_line(self, canvasStack, type, action, args):
        self.lines.append(" ".join([type, action, args]))

    def found_object(self, canvasStack, type, action, args):
        self.objects += 1

    def found_io(self, canvasStack, type, action, args):
        thisLine = self.lines[-1]
        endIdx = thisLine.find("~")
        self.lines[-1] = " ".join([thisLine[:endIdx + 1], str(self.channel)])

    def found_gui(self, cls, canvasStack, type, action, args):
        self.gui[self.objects - 1] = cls(args.split())
        print("canvasStack:", canvasStack,
              "type:", type,
              "action:", action,
              "arguments:", args.split())

    def __str__(self):
        return (
            "{}, with GUI elements:".format(name) + os.linesep +
            os.linesep.join(("{:<3} {}".format(i, obj.args)
                             for i, obj in self.gui.items()))
        )


def fileNameInsert(f, insert):
    start, end = os.path.splitext(f)
    return start + "_" + str(insert) + end


class PdPatchBay(object):
    def _makeRouter(self):
        with open(os.path.join(self.modDir, "router.pd"), "w") as router:
            routerName = router.name[:]
            print("#N canvas 0 0 800 1000 10;", file=router)
            print("#X obj 12 10 netreceive 3000;", file=router)
            print("#X obj 12 40 route pd",
                  " ".join([fileNameInsert(p, str(chan))
                           for p in self.availPatches
                           for chan in range(1, 3)]), ";",
                  file=router)
            print("#X obj 12 140 s pd;", file=router)
            for i, patchName in enumerate(self.availPatches):
                for chan in range(1, 3):
                    print(
                        "#X obj 12", 170 + 30 * i, "s",
                        "pd-{};".format(fileNameInsert(patchName, str(chan))),
                        file=router
                    )
            print("#X connect 0 0 1 0;", file=router)
            print("#X connect 1 0 2 0;", file=router)
            for i in range(len(self.availPatches)):
                for chan in range(2):
                    print("#X connect 1",
                          2 * i + 1 + chan, 2 * i + 3 + chan, 0,
                          ";", file=router)
            print("", file=router)
        return routerName

    def __init__(self, patchDir=PATCH_DIR, nogui=True):
        self.patchDir = patchDir
        self.modDir = mkdtemp()
        PdPatch.modDir = self.modDir
        self.availPatches = os.listdir(self.patchDir)
        self.patches = ({}, {})
        self.router = self._makeRouter()
        self.pd = pd(initPatch=self.router, nogui=nogui)

    def start(self, name, channel=0):
        self.patches[channel][name] = PdPatch(
            pd=self.pd,
            patchPath=os.path.join(self.patchDir, name),
            channel=channel + 1,
        )

    def stop(self, name, channel=0):
        if name in self.patches[channel]:
            self.patches[channel][name].kill()
            self.patches[channel].pop(name)

    def stop_all(self):
        for chan, channelPatches in enumerate(self.patches):
            for patchName in list(channelPatches.keys()):
                self.stop(patchName, chan)

    def shutdown(self):
        self.stop_all()
        self.pd.kill()
        os.unlink(self.router)
        os.rmdir(self.modDir)


class PatchWatcher(cmd.Cmd):
    """Stand-in interface for Pd patch handling."""

    prompt = os.linesep + "> "
    intro = textwrap.fill(
        "Pd patch watcher. No help right now.",
        subsequent_indent=" " * 4)

    def __init__(self, **kw):
        cmd.Cmd.__init__(self)
        self.patchBay = PdPatchBay(**kw)

    def preloop(self):
        self.do_list(None)

    def do_list(self, __):
        print("Available patches:")
        print(os.linesep.join(
            "{:<3} {}".format(i + 1,
                              os.path.splitext(patch)[0])
            for i, patch in enumerate(self.patchBay.availPatches))
        )

    def do_start(self, line):
        name, channel = PatchWatcher._parseNameAndChannel(line)
        channel = channel or 0
        if name in self.patchBay.patches[channel]:
            print("Patch {} is already running on channel {}!".format(
                name, channel
            ))
        try:
            name = self.patchBay.availPatches[int(name) - 1]
        except ValueError:
            # name is already a string, use it as is
            pass
        self.patchBay.start(name, channel)

    def complete_start(self, text, line, begidx, endidx):
        barePatchNames = [p.replace(".pd", "") for p in self.availPatches]
        if text:
            return [p for p in barePatchNames if p.startswith(text)]
        else:
            return barePatchNames

    def do_show(self, __):
        for chan, channelPatches in enumerate(self.patchBay.patches):
            print("Channel", chan + 1)
            for patch in self.channelPatches.values():
                print(patch)

    def do_dbg(self, __):
        import pdb
        pdb.set_trace()

    @staticmethod
    def _parseNameAndChannel(line):
        parts = line.strip().split()
        patchName = parts.pop(0)
        channel = int(parts[0]) - 1 if parts else 0
        return patchName, channel

    def do_stop(self, line):
        if line is Ellipsis:
            self.patchBay.shutdown()
        else:
            self.patchBay.stop(*self._parseNameAndChannel(line))

    do_kill = do_stop

    def do_quit(self, __):
        self.do_stop(Ellipsis)
        print("OK. Bye!")
        return True

    do_exit = do_quit


def setupParser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_false", dest="nogui",
                        default=False,
                        help="Start Pd with a gui.")
    parser.add_argument("--dir", dest="patchDir", default=PATCH_DIR,
                        help="Specify a different default patch directory.")
    return parser


def main(argv=None):
    parser = setupParser()
    args = parser.parse_args()
    patchShell = PatchWatcher(**vars(args))
    try:
        patchShell.cmdloop()
    except:
        patchShell.do_quit(Ellipsis)
        raise


if __name__ == "__main__":
    sys.exit(main())
