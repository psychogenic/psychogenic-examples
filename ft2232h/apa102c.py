'''
    Basic APA102C addressable LED interfacing
    Copyright (C) 2023 Pat Deegan, https://psychogenic.com
    
    These LEDs, under many names, are addressable but also
    have a clock signal, which makes them easier to manage
    than the stuff with a single line but strict timing
    requirements.
    
    There in e.g. the sparkfun Lumenati 8-stick and also
    compatible with the SK9822 LEDs like
    https://cdn-shop.adafruit.com/product-files/2343/SK9822_SHIJI.pdf
    
    Here, I'm using the Tigard's UART port, for no particular reason.
    A0  UART TX
    A1  UART RX
    A2  UART RTS
    A3  UART CTS
    A4  UART DTR
    A5  UART DSR
    A6  UART DCD
'''

PIN_UART_TX  = 0
PIN_UART_RX  = 1
PIN_UART_RTS = 2
PIN_UART_CTS = 3
PIN_UART_DTR = 4
PIN_UART_DSR = 5
PIN_UART_DCD = 6


import time
import pyftdi.gpio

FTDIURIDefault = 'ftdi://ftdi:2232:TG1000a9/1'
PortGlobal = None

def getRawPort(clkLine:int, datLine:int, uri:str=FTDIURIDefault, freq:int=1e6):    
    global PortGlobal
    if PortGlobal is not None:
        return PortGlobal
        
    direction = (1 << clkLine) | (1 << datLine)
    
    ctrl = pyftdi.gpio.GpioAsyncController()
    ctrl.configure(uri, direction=direction, initial=0x0)
    PortGlobal = ctrl.get_gpio()
    PortGlobal.set_frequency(freq)
    time.sleep(0.03)
    return PortGlobal
    



class AP102CFrame:
    FrameLength = 4
    def __init__(self):
        self.bytes = bytearray(AP102CFrame.FrameLength) 
        
        
    @property 
    def payload(self):
        return bytearray(self.bytes)
        
class StartFrame(AP102CFrame):
    
    def __init__(self):
        super().__init__()
        
        
        
class LEDFrameByteIndices:
    def __init__(self):
        self.bright = 0
        self.blue = 1
        self.green = 2
        self.red = 3

class LEDFrame(AP102CFrame):
    
    BrightnessMask = 0b11100000
    def __init__(self, brightness:int=31, red:int=0, 
                green:int=0, blue:int=0):
        super().__init__()
        self.parentString = None
        self.idx = LEDFrameByteIndices()
        self.brightness = brightness
        self.red = red
        self.green = green
        self.blue = blue
        
        
        
    def _notifyParent(self):
        if self.parentString is None:
            return 
            
        self.parentString.childLEDUpdated(self)
        
        
    @property
    def rgb(self):
        return (self.red, self.green, self.blue)
        
    @rgb.setter 
    def rgb(self, cols):
        pString = self.parentString 
        self.parentString = None 
        
        self.red = cols[0]
        self.green = cols[1]
        self.blue = cols[2]
        self.parentString = pString 
        self._notifyParent()
        
    @property 
    def brightness(self):
        return self.bytes[self.idx.bright] & ~self.BrightnessMask
    
    @brightness.setter
    def brightness(self, setTo:int):
        self.bytes[self.idx.bright] = setTo | self.BrightnessMask
        self._notifyParent()
        
    
    
    
    @property 
    def red(self):
        return self.bytes[self.idx.red]
    
    @red.setter
    def red(self, setTo:int):
        self.bytes[self.idx.red] = setTo & 0xff
        self._notifyParent()
    
    
        
    @property 
    def green(self):
        return self.bytes[self.idx.green]
    
    @green.setter
    def green(self, setTo:int):
        self.bytes[self.idx.green] = setTo & 0xff
        self._notifyParent()
    
    @property 
    def blue(self):
        return self.bytes[self.idx.blue]
    
    @blue.setter
    def blue(self, setTo:int):
        self.bytes[self.idx.blue] = setTo & 0xff
        self._notifyParent()
    

class LED(LEDFrame):
    def __init__(self, id:int, brightness:int=31, red:int=0, 
                green:int=0, blue:int=0):
        super().__init__(brightness, red, green, blue)
        self.id = id
        
    def all(self, setTo:int):
        self.red = setTo
        self.green = setTo 
        self.blue = setTo
    
    
class LEDString:
    def __init__(self, numLEDs:int, bright:int=31, red:int=0,
                    green:int=0, blue:int=0,
                    clkPin:int=None, datPin:int=None):
                        
        self.start = StartFrame()
        self._leds = [LED(i, bright, red, green, blue) 
                        for i in range(numLEDs)]
        self._extra = LED(numLEDs, 0, 0, 0)
                        
        for ld in self._leds:
            ld.parentString = self
                        
        self.clkPin = clkPin
        self.datPin = datPin
        self.autoUpdate = False
        if clkPin is not None and datPin is not None:
            self.autoUpdate = True
                        
    
    def childLEDUpdated(self, ld:LED):
        if self.autoUpdate:
            self.update(self.clkPin, self.datPin)
    
    def __lshift__(self, rgb):
        autoUp = self.autoUpdate
        self.autoUpdate = False
        for i in range(1, len(self.leds)):
            self.leds[i-1].rgb = self.leds[i].rgb
            
        self.leds[-1].rgb = rgb
        self.autoUpdate = autoUp
        self.update()
        
    def __rshift__(self, rgb):
        autoUp = self.autoUpdate
        self.autoUpdate = False
        rgbs = [rgb]
        for i in range(len(self.leds)):
            rgbs.append(self.leds[i].rgb)
        
        for i in range(len(self.leds)):
            self.leds[i].rgb = rgbs[i]
        
        if autoUp:
            self.autoUpdate = True
            self.update()
        
    
    @property
    def leds(self):
        return self._leds
    
    @property
    def framesAsBytes(self):
        b = self.start.payload
        #b += self.start.bytes
        for ld in self.leds:
            b += ld.payload
            
        
        b += self._extra.payload
        
        #print(f'AS BYTES: {b}')
            
        return b
        
    
    def all(self, setTo:int):
        oldAuto = self.autoUpdate
        self.autoUpdate = False
        for ld in self.leds:
            ld.all(setTo)
            
        if oldAuto:
            self.autoUpdate = True 
            self.update()
            
    def brightness(self, setTo:int):
        oldAuto = self.autoUpdate
        self.autoUpdate = False
        for ld in self.leds:
            ld.brightness = setTo
        if oldAuto:
            self.autoUpdate = True 
            self.update()
        
    
    def update(self, clkLine:int=None, dataLine:int=None):
        if clkLine is None:
            clkLine = self.clkPin 
            
        if dataLine is None:
            dataLine = self.datPin
        
        if clkLine is None or dataLine is None:
            return 
            
        serSequence = framesToSerial(self.framesAsBytes, 
            clkLine, dataLine)
        port = getRawPort(clkLine, dataLine)
        
        for b in serSequence:
            port.write(b) 


def framesToSerial(bts:bytearray, clockBit:int, dataBit:int):
    
    bitsAndClocks = []
    for b in bts:
        # a byte sequence of data to send
        # for each byte we will 
        #  - set the dataBit according to the current position in the byte
        #  - then leave that databit set, and set the clock bit high
        #  - still leaving the databit set, set the clock bit low
        # this is thus 3x values for each bit we wish to send
        for i in range(7, -1, -1):
            # clear the clock, set the bit
            datAndClockLow = 0
            if b & (1 << i):
                datAndClockLow = (1 << dataBit)
            
            bitsAndClocks.append(datAndClockLow) 
            bitsAndClocks.append(datAndClockLow | (1 << clockBit))
    
    return bitsAndClocks
    
    

def main(clkLine:int, datLine:int, uri:str, freq:int=10e3, 
    numLeds:int=3):
    lstring = LEDString(numLeds)
    port = getRawPort(clkLine, datLine, uri, freq)
    port.set_frequency(freq)
    for l in lstring.leds:
        l.red = 22
        l.blue = 0
        l.brightness = 22
        l.green = 0
        print(l.bytes)
        
    bts  = lstring.framesAsBytes 
    outstr = []
    for b in bts:
        outstr.append(hex(b))
        
    print(', '.join(outstr))
    
    serSequence = framesToSerial(bts, clkLine, datLine)
    outstr = []
    for b in serSequence:
        outstr.append(hex(b))
        port.write(b) 
        #time.sleep(0.001)
        
    print(', '.join(outstr))
        

    
def test(clk:int=PIN_UART_RTS, dat:int=PIN_UART_TX, uri=FTDIURIDefault):
    p = getRawPort(clk, dat, uri, freq=2e6)
    lstring = LEDString(8, clkPin=clk, datPin=dat)
    lstring.update()
    return (p, lstring)
            
    
if __name__ == '__main__':
    (p, lstring) = test(PIN_UART_RTS, 
                        PIN_UART_TX, 
                        'ftdi://ftdi:2232:TG1000a9/1')
    
    PauseForLogicAn = False
    time.sleep(0.33)
    
    lstring.brightness(20)
    lstring.leds[0].rgb = (0xAA, 0x10, 0x5)
    lstring.leds[1].rgb = (0x10, 0x55, 0x10)
    lstring.leds[2].rgb = (0x10, 0x10, 0x55)
    lstring.leds[2].blue = 0x60
    
    
    lstring.brightness(0)
    if PauseForLogicAn:
        # for a look on the logic analyzer...
        print("GO")
        time.sleep(2)
        lstring.update()
        time.sleep(3)
    
    if False:
        for loop in range(2):
            for i in range(32):
                lstring.brightness(i)
            
            for i in range(32):
                lstring.brightness(31-i)
    
    lstring.all(0)
    lstring.brightness(30)
    for i in range(0x20):
        lstring.all(i)
        time.sleep(0.02)
    cols = ( (0xf,0,0), (0,0xf,0), (0,0,0xf))
    for loop in range(25):
        lstring << cols[int(loop/2) % 3]
        time.sleep(0.05)
    for loop in range(60):
        lstring >> cols[int(loop/5) % 3]
        time.sleep(0.02)
        
    for i in range(32):
        lstring.brightness(31-i)
        
    lstring.all(0xff)
    lstring.brightness(31)
    
    time.sleep(0.7)
    for i in range(32):
        lstring.brightness(31-i)
        
    
    
