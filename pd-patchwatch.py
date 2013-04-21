# python3

import argparse
import cmd
import os
import sys
import tempfile
import textwrap
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
    def kill(self):
        self.pd.send(
            " ".join([";", self.fileName, "menuclose;"])
        )
        return True

    def __init__(self, patchPath=None, pd=None):
        self.objects = 0
        self.trees = []
        self.lines = []
        self.gui = {}
        self.pd = pd

        if patchPath:
            patchDir, patchName = os.path.split(patchPath)
            if patchName.endswith(".pd"):
                self.fileName, self.name = (patchName,
                                            os.path.splitext(patchName))
            else:
                self.fileName, self.name = patchName + ".pd", patchName
            p = PdParser(os.path.join(patchDir, self.fileName))
            p.add_filter_method(partial(PdPatch.found_object, self),
                                type="#X")
            p.add_filter_method(partial(PdPatch.found_anything, self))
            for cls in pdgui.PdGui.__subclasses__():
                p.add_filter_method(partial(PdPatch.found_gui, self, cls),
                                    type="#X", object=cls.__name__)
            print(p.parse(), "elements in this patch.")
            print(self.objects, "objects.")
            self.pd.send(
                " ".join([";", "pd open",
                          self.fileName,
                          os.path.join(patchDir, ""),
                          ";"])
            )

    def found_anything(self, canvasStack, type, action, args):
        self.lines.append(" ".join([type, action, args]))

    def found_object(self, canvasStack, type, action, args):
        self.objects += 1

    def found_gui(self, cls, canvasStack, type, action, args):
        self.gui[self.objects - 1] = cls(args.split())
        print("canvasStack:", canvasStack,
              "type:", type,
              "action:", action,
              "arguments:", args.split())


class PatchWatcher(cmd.Cmd):
    """Stand-in interface for Pd patch handling."""

    prompt = os.linesep + "> "
    intro = textwrap.fill(
        "Pd patch watcher. No help right now.",
        subsequent_indent=" " * 4)

    def _makeRouter(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as router:
            routerName = router.name[:]
            print("#N canvas 0 0 800 1000 10;", file=router)
            print("#X obj 12 10 netreceive 3000;", file=router)
            print("#X obj 12 40 route pd",
                  " ".join([p for p in self.availPatches]), ";",
                  file=router)
            print("#X obj 12 100 s pd;", file=router)
            for i, patchName in enumerate(self.availPatches):
                print("#X obj 12", 130 + 30 * i,
                      "s", "pd-{};".format(patchName),
                      file=router)
            print("#X connect 0 0 1 0;", file=router)
            print("#X connect 1 0 2 0;", file=router)
            for i in range(len(self.availPatches)):
                print("#X connect 1", i + 1, i + 3, 0, ";", file=router)
            print("", file=router)
        return routerName

    def __init__(self, patchDir=PATCH_DIR, nogui=True):
        cmd.Cmd.__init__(self)
        self.patchDir = patchDir
        # TODO: handle case where patchDir doesn't exist
        self.availPatches = os.listdir(self.patchDir)
        self.patch = None
        self.router = self._makeRouter()
        self.pd = pd(initPatch=self.router, nogui=nogui)

    def preloop(self):
        self.do_list(None)

    def do_list(self, __):
        print("Available patches:")
        print(os.linesep.join("{:<3} {}".format(i + 1,
                                                os.path.splitext(patch)[0])
                              for i, patch in enumerate(self.availPatches)))

    def do_start(self, line):
        patchName = line.strip()
        try:
            patchName = self.availPatches[int(patchName) - 1]
        except ValueError:
            # patchName is already a string, use it as is
            pass
        if self.patch:
            self.patch.kill()
        self.patch = PdPatch(pd=self.pd,
                             patchPath=os.path.join(self.patchDir, patchName))

    def complete_start(self, text, line, begidx, endidx):
        barePatchNames = [p.replace(".pd", "") for p in self.availPatches]
        if text:
            return [p for p in barePatchNames if p.startswith(text)]
        else:
            return barePatchNames

    def do_show(self, line):
        if self.patch:
            print("Current patch:", self.patch.patchName)
            if self.patch.gui:
                print(
                    "Patch GUI elements:",
                    os.linesep.join(("{:<3} {}".format(i, obj.args)
                                     for i, obj in self.patch.gui.items()))
                )

    def do_dbg(self, __):
        import pdb
        pdb.set_trace()

    def do_stop(self, __):
        if self.patch and self.patch.kill():
            print("Patch {0} stopped.".format(self.patch.name))
        self.patch = None

    do_kill = do_stop

    def do_quit(self, line):
        self.do_stop(line)
        self.pd.kill()
        os.unlink(self.router)
        print("OK. Bye!")
        return True

    do_exit = do_quit


def setupParser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_false", dest="nogui",
                        default=False,
                        help="Start Pd with a gui.")
    return parser


def main(argv=None):
    parser = setupParser()
    args = parser.parse_args()
    patchShell = PatchWatcher(nogui=args.nogui)
    try:
        patchShell.cmdloop()
    except:
        patchShell.do_quit(None)
        raise


if __name__ == "__main__":
    sys.exit(main())
