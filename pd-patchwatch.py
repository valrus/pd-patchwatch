# python3

import cmd
import os
import sys
import textwrap
from functools import partial

from pypd import Pd, PdParser
import pdgui

PD_BIN = os.environ.get("PD_BIN", os.path.join(os.sep, "usr", "bin", "pd"))
PATCH_DIR = os.path.join(os.path.dirname(__file__), "patches")


class PdPatch(object):
    def kill(self):
        if self.proc and self.proc.Alive():
            self.proc.Exit()
            self.proc = None
            return True
        return False

    def __init__(self, patchDir, patchName):
        if patchName.endswith(".pd"):
            patchFullName, self.patchName = patchName, patchName[:-3]
        else:
            patchFullName, self.patchName = patchName + ".pd", patchName
        self.objects = 0
        self.gui = {}
        p = PdParser(os.path.join(patchDir, patchFullName))
        p.add_filter_method(partial(PdPatch.found_object, self),
                            type="#X")
        for cls in pdgui.PdGui.__subclasses__():
            p.add_filter_method(partial(PdPatch.found_gui, self, cls),
                                type="#X", object=cls.__name__)
        print(p.parse(), "elements in this patch.")
        print(self.objects, "objects.")
        self.proc = Pd(open=patchFullName, path=[patchDir])

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

    def __init__(self, patchDir=PATCH_DIR):
        cmd.Cmd.__init__(self)
        self.patchDir = patchDir
        # TODO: handle case where patchDir doesn't exist
        self.availPatches = os.listdir(self.patchDir)
        self.patch = None
        self.pd = None

    def preloop(self):
        self.do_list(None)

    def do_list(self, __):
        print("Available patches:")
        print(os.linesep.join("{:<3} {}".format(i + 1, patch.replace(".pd", ""))
                              for i, patch in enumerate(self.availPatches)))

    def do_start(self, line):
        patchName = line.strip()
        try:
            patchName = self.availPatches[int(patchName) - 1]
        except ValueError:
            # patchName is already a string, use it as is
            pass
        self.patch = PdPatch(self.patchDir, patchName)

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
            print("Patch {0} stopped.".format(self.patch.patchName))
        self.patch = None

    do_kill = do_stop

    def do_quit(self, line):
        self.do_stop(line)
        print("OK. Bye!")
        return True

    do_exit = do_quit


def main(argv=None):
    patchShell = PatchWatcher()
    try:
        patchShell.cmdloop()
    except:
        patchShell.do_quit(None)
        raise


if __name__ == "__main__":
    sys.exit(main())
