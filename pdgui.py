import os


class PdGui(object):
    objs = [
        "bng",  # bang
        "tgl",  # toggle
        "vsl",  # vertical slider
        "hsl",  # horizontal slider
        "hdl",  # horizontal row of radio buttons
        "vu",   # VU meter
        "vdl",  # vertical row of radio buttons
        "nbx",   # number box
    ]

    def __init__(self, argList):
        for i, arg in enumerate(argList):
            # set instance variables for each arg
            self.__dict__[self.__class__.args[i]] = arg

    def __str__(self):
        return os.linesep.join(
            ["Object {} with args:".format(self.name)] +
            ["    {}: {}".format(arg, self.__dict__[arg])
             for arg in self.__class__.args]
        )



class bng(PdGui):
    args = [
        "x_pos",  # horizontal position within the window
        "y_pos",  # vertical position within the window
        "name",
        "size",  # square size of the gui element
        "hold",  # hold time in milliseconds, ranges from 50 to 1000000000
        "interrupt",  # interrupt time in milliseconds, ranges from 10 to 250
        "init",  # bang on load
        "send",  # send symbol name
        "receive",  # receive symbol name
        "label",  # label
        "x_off",  # x pos of label text relative to upperleft corner
        "y_off",  # y pos of label text relative to upperleft corner
        "font",  # font type
        "fontsize",  # font size
        "bg_color",  # background color
        "fg_color",  # foreground color
        "label_color",  # label color
    ]


class tgl(PdGui):
    args = [
        "x_pos",  # horizontal position within the window
        "y_pos",  # vertical position within the window
        "name",
        "size",  # square size of the gui element
        "init",  # set on load
        "send",  # send symbol name
        "receive",  # receive symbol name
        "label",  # label
        "x_off",  # x pos of label text relative to upperleft corner
        "y_off",  # y pos of label text relative to upperleft corner
        "font",  # font type
        "fontsize",  # font size
        "bg_color",  # background color
        "fg_color",  # foreground color
        "label_color",  # label color
        "init_value",  # value sent when the [init] attribute is set
        "default_value",  # default value when the [init] attribute is not set
    ]


class nbx(PdGui):
    args = [
        "x_pos",  # horizontal position within the window
        "y_pos",  # vertical position within the window
        "name",
        "size",  # number of digits the element displays
        "height",  # vertical size of element in pixels
        "min",  # minimum value, typically -1e+037
        "max",  # maximum value, typically 1e+037
        "log",  # linear when unset, logarithmic when set
        "init",  # when set outputs
        "send",  # send symbol name
        "receive",  # receive symbol name
        "label",  # label
        "x_off",  # x pos of label text relative to upperleft corner
        "y_off",  # y pos of label text relative to upperleft corner
        "font",  # font type
        "fontsize",  # font size in pixels
        "bg_color",  # background color
        "fg_color",  # foreground color
        "label_color",  # label color
        "log_height",  # log steps: values from 10 to 2000, default is 256
    ]


class hdl(PdGui):
    args = [
        "x_pos",  # horizontal position within the window
        "y_pos",  # vertical position within the window
        "name",
        "size",  # x or y size, depending on the number of radio buttons
        "new_old",  # send new and old value, or only the new value
        "init",  # send default value on init
        "number",  # amount of radio buttons
        "send",  # send symbol name
        "receive",  # receive symbol name
        "label",  # label
        "x_off",  # x pos of label text relative to upperleft corner
        "y_off",  # y pos of label text relative to upperleft corner
        "font",  # font type
        "fontsize",  # font size
        "bg_color",  # background color
        "fg_color",  # foreground color
        "label_color",  # label color
        "default_value",  # default value when the [init] attribute is not set
    ]

hradio = vdl = vradio = hdl


class hsl(PdGui):
    args = [
        "x_pos",  # horizontal position within the window
        "y_pos",  # vertical position within the window
        "name",
        "width",  # horizontal size of gui element
        "height",  # vertical size of gui element
        "bottom",  # minimum value
        "top",  # maximum value
        "log",  # sets slider range logarithmically, otherwise linear
        "init",  # sends default value on patch load
        "send",  # send symbol name
        "receive",  # receive symbol name
        "label",  # label
        "x_off",  # x pos of label text relative to upperleft corner
        "y_off",  # y pos of label text relative to upperleft corner
        "font",  # font type
        "fontsize",  # font size
        "bg_color",  # background color
        "fg_color",  # foreground color
        "label_color",  # label color
        "default_value",  # default value times hundred
        "steady_on_click",  # when set, fader is steady, otherwise it jumps
    ]

# Vertical sliders' args are identical to horizontal ones
hslider = vsl = vslider = hsl
