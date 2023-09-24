'''
    PCF8575 I/O expander implementation, via pyftdi I2cController.
    Copyright (C) 2023 Pat Deegan https://psychogenic.com/
    
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
    
    Lots of details about the PCF8575 in my video about creating a 
    digital model of the IC for simulation:
    https://www.youtube.com/watch?v=BS_uTqz3zik
    
    And about using the FT2232H (specifically within the Tigard module):
    https://youtu.be/WIIR77fCHYc 
    
    
    # Sample usage:
    # defaults to all inputs (pulled high)
    ioexp = IOExpander(addressSelect=0b011)
    
    # set some as outputs
    for i in range(8):
        ioexp.setPinMode(i, PinMode.OUTPUT)
    
    # and write to them
    ioexp.write(0, True) # high
    ioexp.write(1, 0) # low
    ioexp.write(2, False) # low
    
    # read some inputs
    if not ioexp.read(10):
        print(hex(ioexp.readInputs()))
        ioexp.dumpInputs()
        
'''
import time
from enum import Enum
from pyftdi.i2c import I2cController

# three address bits
AddressBits = 0b000

# FT2232H uri (Tigard)
FTDIDeviceURI = 'ftdi://ftdi:2232:TG1000a9/2'


# internal
BaseAddress = 0x20
Ctrl = I2cController()
CtrlIsConfig = False

def device(addressSelect:int=AddressBits, devURI:str=FTDIDeviceURI):
    global CtrlIsConfig
    if not CtrlIsConfig:
        CtrlIsConfig = True
        Ctrl.configure(devURI) 
    
    return Ctrl.get_port(BaseAddress | addressSelect)
    
class PinMode(Enum):
    OUTPUT = 0
    INPUT = 1

class IOExpander:
    '''
        IOExpander - PCF8575 I/O expander.
        
        This i/o expander uses a simple protocol that allows:
        
            - tying any of the 16 pins LOW (output LOW)
            - tying any of the 16 pins HIGH through a pull-up (output HIGH == input)
            
        This class has facilities to set and track the 'mode' of any io pin, even though
        output high is basically the same as input.
        This allows us to distinguish between a HIGH output and a HIGH input, namely with
            readInputs()
        which returns a 16-bit integer where the only 1 values are bits (pins) that are 
        both high and configured as inputs.
        
        Inputs may be read(pin).  You write(pin, value) to outputs to set the pin.
        
        The rawRead and rawWrite methods ignore this distinction between input and output,
        and just deal with the device values directly.
            
        The interrupt pin may be used to monitor changes on any input pin.
        The important thing with this is that there is no latching: any interrupt will
        disappear if the changed pin toggles back to its original state before the 
        new value is read.
        
        Reading or writing to the device clears the interrupt.
    
    '''
    def __init__(self, addressSelect:int=AddressBits, devURI:str=FTDIDeviceURI):
        '''
            IOExpander
            @param addressSelect: address select bits, default 0b000
            @param devURI: device uri, default ftdi://ftdi:2232:TG1000a9/2
            
            @note: by default, on startup, all io pins are configured as
            inputs (equivalent to output HIGH, thanks to pull-up).
            
        '''
        self.address_select = addressSelect
        self.devURI = devURI
        self.inputs = 0xffff
        self.regvalue = 0xffff
        self._device = None 
    
    @property
    def device(self):
        '''
            Returns the raw pyftdi I2C port/device
        '''
        if self._device is not None:
            return self._device 
        
        self._device = device(self.address_select, self.devURI)
        return self._device
        
        
    
    def setPinMode(self, pin:int, mode:PinMode):
        '''
            setPinMode
            @param pin: the pin index (0-15)
            @param mode: PinMode.INPUT or PinMode.OUTPUT
            
            @note: ensures inputs are configured correctly (i.e. high with pull-up)
        
        '''
        pinBit = (1 << pin)
        if mode == PinMode.OUTPUT:
            # output
            self.inputs = self.inputs & (~(pinBit))
        else:
            # input
            if not (self.regvalue & pinBit):
                # this can't be an input, set high first
                self.write(pin, True)
            self.inputs = self.inputs | pinBit
                
            
            
    def pinMode(self, pin:int):
        '''
            pinMode
            @param pin: io pin index (0-15)
            
            Returns the currently set mode
        '''
        if self.inputs & (1 << pin):
            return PinMode.INPUT
        
        return PinMode.OUTPUT
        
        
        
    def readInputs(self):
        '''
            reads current value of all pins configured as inputs
            returns u16, with outputs set to 0
        '''
        v = self.rawRead()
        v = v & self.inputs 
        return v 
        
    def read(self, pin:int):
        '''
            read an input io pin
            returns True if high, False otherwise.
        '''
        if not self.inputs & (1 << pin):
            return False
            
        v = self.readInputs()
        if v & (1 << pin):
            return True
        return False
        
    def write(self, pin:int, value:bool):
        '''
            write the value of an output pin.
            @param pin: io pin index (0-15)
            @param value: true/1 for high or false/0 for low
            
            @note: ensures pin in question is registered as an output
        '''
        self.setPinMode(pin, PinMode.OUTPUT)
        if value:
            self.regvalue = self.regvalue | (1 << pin)
        else:
            self.regvalue = self.regvalue & (~(1<<pin))
            
        self.rawWrite(self.regvalue)
            
    def rawWrite(self, u16:int):
        '''
            rawWrite
            @param u16: 16-bit value to write
            
            low-level write to device.
            
            @note: clears interrupt
        '''
        vout = [u16 & 0x00ff, ((u16 & 0xff00) >> 8)]
        self.device.write(bytearray(vout))
        
    
    def rawRead(self):
        '''
            rawRead
            returns raw 16-bit value read from device.
            @note: clears interrupt
        '''
        vin = self.device.read(2) 
        # low, high
        v = (vin[1] << 8) | vin[0]
        return v
        
        
    def dumpInputs(self):
        '''
            dumpInputs
            Utility method to print out a list of 
             INPUT_PIN_INDEX:  READ_VALUE (HIGH or LOW)
        '''
        v = self.readInputs()
        for i in range(16):
            if self.pinMode(i) == PinMode.INPUT:
                state = 'LOW'
                if v & (1 << i):
                    state = 'HIGH'
                
                print(f'{i}:\t{state}')
                
    def flash(self, pin:int, times:int=5, halfper:float=0.25):
        '''
            flash
            @param pin: io pin index (0-15)
            @param times: num times to toggle
            @param halfper: period/2
            
            Utility method to toggle an io output repeatedly.
        '''
        for i in range(times):
            self.write(pin, False)
            time.sleep(halfper)
            self.write(pin, True)
            time.sleep(halfper)
            
        


if __name__ == '__main__':
    
    ioexp = IOExpander()
    ioexp.dumpInputs()
        
    # set some as outputs
    for i in range(8):
        ioexp.setPinMode(i, PinMode.OUTPUT)
    
    # and write to them
    ioexp.write(0, True) # high
    ioexp.write(1, 0) # low
    ioexp.write(2, False) # low
    
    # read some inputs
    print(hex(ioexp.readInputs()))
    ioexp.dumpInputs()
    


