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
INIT_PATCH = "patchbay.pd"


class PdPatch(object):
    def __init__(self, patchPath=None, channel=1, pd=None):
        self.objectCount = 0
        self.channel = channel
        self.objects = []
        self.guiIndices = []
        self.pd = pd

        if patchPath:
            patchDir, patchName = os.path.split(patchPath)
            if patchName.endswith(".pd"):
                fileName, self.name = (patchName, os.path.splitext(patchName))
            else:
                fileName, self.name = patchName + ".pd", patchName

            p = PdParser(os.path.join(patchDir, fileName))
            p.add_filter_method(self.found_io, type="#X", object="adc~")
            p.add_filter_method(self.found_io, type="#X", object="dac~")
            p.add_filter_method(self.found_connect, type="#X",
                                action="connect")
            for cls in pdgui.PdGui.__subclasses__():
                p.add_filter_method(partial(self.found_object, cls), type="#X",
                                    object=cls.__name__)
            p.add_filter_method(partial(self.found_object, pdgui.PdObject),
                                type="#X")
            print(p.parse(), "elements in this patch.")

    def _connectSockets(self, fromSocket, toSocket, twoWay=True):
        self.objects[fromSocket.index].outlets[fromSocket.position] = toSocket
        if twoWay:
            self.objects[toSocket.index].inlets[toSocket.position] = fromSocket

    def found_connect(self, canvasStack, type, action, args):
        obj1, outlet, obj2, inlet = map(int, args.split())
        self._connectSockets(pdgui.socket(obj1, outlet),
                             pdgui.socket(obj2, inlet))

    def found_io(self, canvasStack, type, action, args):
        pass

    def found_object(self, cls, canvasStack, type, action, args):
        if action == "connect":
            return
        if cls is pdgui.PdObject:
            self.objects.append(cls(args.split()))
            self.objectCount += 1
        else:
            self.guiIndices.append(self.objectCount - 1)
            print("canvasStack:", canvasStack,
                  "type:", type,
                  "action:", action,
                  "arguments:", args.split())

    def add(self, objectArgs):
        self.objects.append(pdgui.PdObject(objectArgs))
        self.pd.send(" ".join(["obj"] + objectArgs))
        return len(self.objects) - 1

    def getObj(self, index):
        return self.objects[index]

    def removeObjectAt(self, index):
        objectToRemove = self.objects[index]
        # Remove this object's inbound connections from other objects
        for outSocket in objectToRemove.inlets.values():
            self.objects[outSocket.index].outlets.pop(outSocket.position)
        # Remove this object's outbound connections from other objects
        for inSocket in objectToRemove.outlets.values():
            self.objects[inSocket.index].inlets.pop(inSocket.position)

        # Find this object and remove it
        self.pd.send(" ".join(["find", objectToRemove.name, "1"]))
        for i in range(sum(obj.name == objectToRemove.name
                       for obj in self.objects[:index])):
            self.pd.send("findagain")
        self.pd.send("cut")

        # Adjust indices of removed object's outgoing sockets to higher indices
        for pos, outgoingSocket in objectToRemove.outlets.items():
            if outgoingSocket.index >= index:
                fixedSocket = pdgui.socket(outgoingSocket.index - 1,
                                           outgoingSocket.position)
                self._connectSockets(pdgui.socket(index, pos), fixedSocket,
                                     twoWay=False)

        # Adjust all incoming connections to objects after the removed one
        for i, obj in enumerate(self.objects[index + 1:]):
            for pos, incomingSocket in obj.inlets.items():
                fixedSocket = pdgui.socket(i + index, pos)
                self._connectSockets(incomingSocket, fixedSocket,
                                     twoWay=False)

        return self.objects.pop(index)

    def hasConnection(self, fromSocket, toSocket):
        return (
            self.objects[fromSocket.index].outlets[fromSocket.position]
            == toSocket and
            self.objects[toSocket.index].inlets[toSocket.position]
            == fromSocket
        )

    def disconnect(self, fromSocket, toSocket):
        if self.hasConnection(fromSocket, toSocket):
            self.objects[fromSocket.index].outlets.pop(fromSocket.position)
            self.objects[toSocket.index].inlets.pop(fromSocket.position)
        self.pd.send(" ".join(
            map(str, ("disconnect", ) + fromSocket + toSocket)
        ))

    def connect(self, fromSocket, toSocket):
        self._connectSockets(fromSocket, toSocket)
        self.pd.send(" ".join(map(str, ("connect", ) + fromSocket + toSocket)))

    def __str__(self):
        return (
            "{}, with GUI elements:".format(self.name) + os.linesep +
            os.linesep.join(("{:<3} {}".format(i, self.objects[i].args)
                             for i in self.guiIndices))
        )


def fileNameInsert(f, insert):
    start, end = os.path.splitext(f)
    return start + "_" + str(insert) + end


class PdPatchBay(object):
    def __init__(self, patchDir=PATCH_DIR, nogui=True):
        self.patchDir = patchDir
        self.availPatches = [p for p in os.listdir(self.patchDir)
                             if os.path.splitext(p)[0].endswith("~")]
        self.effects = ({}, {})
        self.pd = pd(initPatch=os.path.join(patchDir, INIT_PATCH), nogui=nogui)
        self.patch = PdPatch(patchPath=os.path.join(patchDir, INIT_PATCH),
                             channel=None,
                             pd=self.pd)
        self.ins, self.outs = [2, 3], [4, 5]

    def _chainConnect(self, newObjIndex, channel):
        # disconnect dac from previous patch
        toIndex = self.outs[channel]
        outObj = self.patch.getObj(toIndex)
        previousOutlet = outObj.inlets[0]
        self.patch.disconnect(previousOutlet,
                              pdgui.socket(toIndex, 0))
        # connect previous patch to new patch
        self.patch.connect(previousOutlet,
                           pdgui.socket(newObjIndex, 0))
        # connect new patch to dac
        self.patch.connect(pdgui.socket(newObjIndex, 0),
                           pdgui.socket(self.outs[channel], 0))

    def start(self, name, channel=0):
        newPatch = PdPatch(
            patchPath=os.path.join(self.patchDir, name),
            channel=channel + 1,
        )
        objectArgs = list(map(str, [
            315 if channel else 40,
            80 + 40 * (len(self.effects[channel]) + 1),
            name
        ]))
        newIndex = self.patch.add(objectArgs)
        self._chainConnect(newIndex, channel)
        self.effects[channel][name] = (newPatch, newIndex)

    def stop(self, name, channel=0):
        if name in self.effects[channel]:
            patch, index = self.effects[channel].pop(name)
            removedObj = self.patch.removeObjectAt(index)
            self.patch.connect(removedObj.inlets[0],
                               removedObj.outlets[0])
        # Reduce indices of all objects after the removed one
        for channelEffects in self.effects:
            for name, eff in channelEffects.items():
                if eff[1] >= index:
                    channelEffects[name] = (eff[0], eff[1] - 1)

    def stop_all(self):
        for chan, channelEffects in enumerate(self.effects):
            for patchName in list(channelEffects.keys()):
                self.stop(patchName, chan)

    def shutdown(self):
        self.stop_all()
        self.pd.kill()


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
        if name in self.patchBay.effects[channel]:
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
        for chan, channelPatches in enumerate(self.patchBay.effects):
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
        patchName = patchName if patchName.endswith("~") else patchName + "~"
        channel = int(parts[0]) - 1 if parts else 0
        return patchName, channel

    def do_stop(self, line):
        if line is Ellipsis:
            self.patchBay.shutdown()
        elif not line.strip():
            return
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
                        default=True,
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
