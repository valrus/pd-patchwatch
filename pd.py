import os
import signal
import sys
from subprocess import Popen, PIPE

DEFAULT_PORT = 3000


class PdException(Exception):
    pass


class pd(object):
    @staticmethod
    def _getPdBin(pdbin):
        if pdbin is None:
            if "PD_BIN" in os.environ:
                return os.environ["PD_BIN"]
            else:
                if sys.platform == "win32":
                    return os.path.join("pd", "bin", "pd.exe")
                elif sys.platform == "linux2":
                    return "pd"
                elif sys.platform == "darwin":
                    return os.path.join("", "Applications", "Pd.app",
                                        "Contents", "Resources", "bin", "pd")
                else:
                    raise PdException("Unknown Pd executable location on your"
                                      " platform ({}).".format(sys.platform))
        else:
            return pdbin

    def __init__(self, stderr=True, nogui=True, initPatch=None, bin=None):
        self.pdbin = pd._getPdBin(bin)
        args = [self.pdbin]

        self.pdsend = os.path.join(os.path.dirname(self.pdbin), "pdsend")
        self.port = DEFAULT_PORT

        if stderr:
            args.append("-stderr")

        if nogui:
            args.append("-nogui")

        if initPatch:
            args.append("-open")
            args.append(initPatch)

        try:
            print(args)
            self.proc = Popen(args, stdin=None, stderr=PIPE, stdout=PIPE,
                              close_fds=(sys.platform != "win32"))
        except OSError:
            raise PdException(
                "Problem running `{}` from '{}'".format(self.pdbin,
                                                        os.getcwd()))

    def send(self, msg):
        args = [self.pdsend, str(DEFAULT_PORT)]
        print(args, msg)
        sendProc = Popen(args, stdin=PIPE, close_fds=(sys.platform != "win32"),
                         universal_newlines=True)
        out, err = sendProc.communicate(input=msg)

    def kill(self):
        os.kill(self.proc.pid, signal.SIGINT)
        if self.proc:
            self.proc.wait()
