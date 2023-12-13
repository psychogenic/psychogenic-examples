'''
    Caravel Housekeeping SPI register access utility script
    Copyright (C) 2023 Pat Deegan, https://psychogenic.com
    
    This script is a simple demo for using the Caravel SPI to 
    read and write registers.  See the caravel housekeeping SPI 
    docs for details: 
    https://caravel-harness.readthedocs.io/en/latest/housekeeping-spi.html
    
    I used a Tigard (FT2232H) but any method to get SPI out
    should work.  Some details about the FTDI USB - SPI/I2C/JTAG/etc
    chip are in https://youtu.be/WIIR77fCHYc 
    
    Connect to
        - mprj_io[1]_SDO
        - mprj_io[2]_SDI
        - mprj_io[3]_nCS
        - mprj_io[4]_SCK
    and GND/3v3 as applicable
    
    ** Basic GPIO config **
    
    To write a GPIO configuration, create a GPIOConfig object,
    either using raw value
    
        gconf = GPIOConfig(0x0800)
        or, e.g.
        gconf = GPIOConfig(GPIOMode.USER_INPUT_PULLUP)
        
    these objects may be queried or set for various attribs
        print(gconf.output_disable)
        gconf.output_disable = True
    
    Then write the config
        setGPIOConfig(MPRJ_IO_IDX, gconf)
    
    When all are written, latch the changes
        latchGPIOConfig()
    
    To see raw SPI sent, set
    DUMPSPI = True

'''

import time 
from enum import Enum
from pyftdi.spi import SpiController, SpiIOError

DUMPSPI = False
FTDIDeviceURI = 'ftdi://ftdi:2232:TG1000a9/2'

ReadReg  = 0b01000000
WriteReg = 0b10000000

Ctrl = SpiController()
SPIDev = None 

class RegisterAddress(Enum):
    ManufacturerID = 0x01
    ProductID = 0x03
    UserProjectID = 0x04
    CPUIRQ = 0x0a
    CPUReset = 0x0b
    
    GPIOControl = 0x13 # gpio_adr | 12'h000 : spiaddr = 8'h13;	// GPIO control
    BaseGPIOAddress = 0x1d

class GPIOMode(Enum):
    MGMT_INPUT_NOPULL 	= 0x0403
    MGMT_INPUT_PULLDOWN = 0x0c01
    MGMT_INPUT_PULLUP 	= 0x0801
    MGMT_OUTPUT 	    = 0x1809
    MGMT_BIDIRECTIONAL 	= 0x1801
    MGMT_ANALOG 	    = 0x000b
    
    
    USER_INPUT_NOPULL 	= 0x0401
    USER_INPUT_PULLDOWN = 0x0c00
    USER_INPUT_PULLUP 	= 0x0800
    USER_OUTPUT 	    = 0x1808
    USER_BIDIRECTIONAL 	= 0x1800
    USER_ANALOG 	    = 0x000a
    
    
class GPIOPadBits(Enum):
    MGMT_ENABLE       = 0x0001
    OUTPUT_DISABLE    = 0x0002
    HOLD_OVERRIDE     = 0x0004
    INPUT_DISABLE     = 0x0008
    MODE_SELECT       = 0x0010
    ANALOG_ENABLE     = 0x0020
    ANALOG_SELECT     = 0x0040
    ANALOG_POLARITY   = 0x0080
    SLOW_SLEW_MODE    = 0x0100
    TRIPPOINT_SEL     = 0x0200
    DIGITAL_MODE_MASK = 0x1c00



class GPIOConfig:
    def __init__(self, mode=0):
        self.stdmode = None
        if not type(mode) == int:
            self.val = mode.value 
            self.stdmode = mode 
        else:
            self.val = mode
            try:
                self.stdmode = GPIOMode(mode)
            except ValueError:
                pass
            
    @property 
    def value(self):
        return self.val 
        
    @value.setter
    def value(self, setTo:int):
        if not type(setTo) == int:
            self.val = setTo.value 
        else:
            self.val = setTo
            
    def maskBits(self, bits:GPIOPadBits):
        return self.val & bits.value 
    
    def setBits(self, bits:GPIOPadBits):
        self.val =  self.val | bits.value 
        
    def clearBits(self, bits:GPIOPadBits):
        self.val = self.val & ~(bits.value)
        
    def _set(self, bits:GPIOPadBits, setTo:bool):
        
        if setTo:
            self.setBits(bits)
        else:
            self.clearBits(bits)
        
        
        
    @property 
    def mgmt_enable(self):
        return self.maskBits(GPIOPadBits.MGMT_ENABLE)
        
    @mgmt_enable.setter
    def mgmt_enable(self, setTo:bool):
        self._set(GPIOPadBits.MGMT_ENABLE, setTo)
    
    
    
    @property 
    def output_disable(self):
        return self.maskBits(GPIOPadBits.OUTPUT_DISABLE)
        
    @output_disable.setter
    def output_disable(self, setTo:bool):
        self._set(GPIOPadBits.OUTPUT_DISABLE, setTo)
        
        
    @property 
    def mode_select(self):
        return self.maskBits(GPIOPadBits.MODE_SELECT)
        
    @mode_select.setter
    def mode_select(self, setTo:bool):
        self._set(GPIOPadBits.MODE_SELECT, setTo)
        
        
    @property 
    def hold_override (self):
        return self.maskBits(GPIOPadBits.HOLD_OVERRIDE)
        
    @hold_override.setter
    def hold_override(self, setTo:bool):
        self._set(GPIOPadBits.HOLD_OVERRIDE, setTo)
        
    @property 
    def input_disable(self):
        return self.maskBits(GPIOPadBits.INPUT_DISABLE)
        
    @input_disable.setter
    def input_disable(self, setTo:bool):
        self._set(GPIOPadBits.INPUT_DISABLE, setTo)
        
        
    @property 
    def analog_enable (self):
        return self.maskBits(GPIOPadBits.ANALOG_ENABLE)
        
    @analog_enable.setter
    def analog_enable(self, setTo:bool):
        self._set(GPIOPadBits.ANALOG_ENABLE, setTo)
        
    
    @property 
    def analog_select(self):
        return self.maskBits(GPIOPadBits.ANALOG_SELECT)
        
    @analog_select.setter
    def analog_select(self, setTo:bool):
        self._set(GPIOPadBits.ANALOG_SELECT, setTo)
        
        
    @property 
    def analog_polarity(self):
        return self.maskBits(GPIOPadBits.ANALOG_POLARITY)
        
    @analog_polarity.setter
    def analog_polarity(self, setTo:bool):
        self._set(GPIOPadBits.ANALOG_POLARITY, setTo)
        
    
    def __repr__(self):
        return f'<GPIOConfig {hex(self.value)}>'
        
    def __str__(self):
        if self.stdmode is not None:
            retStr = f'{hex(self.value)} ({str(self.stdmode)})\n'
        else:
            retStr = f'{hex(self.value)}\n'
        props = [
            'mgmt_enable',
            'output_disable',
            'input_disable',
            'hold_override',
            'mode_select',
            'analog_enable',
            'analog_select',
            'analog_polarity',
        ]
        
        propDetails = []
        for p in props:
            v = 'false'
            if getattr(self, p):
                v = 'TRUE'
            
            propDetails.append(f'  {p}:\t{v}')
        
        retStr += '\n'.join(propDetails)
        return retStr
        
        
def arrayBytesString(bts):
    return ','.join(map(lambda x: hex(x), bts))
    
def getSPI(deviceURI:str=FTDIDeviceURI):
    global SPIDev
    if SPIDev is not None:
        return SPIDev
    
    Ctrl.configure(deviceURI)
    SPIDev = Ctrl.get_port(cs=0, freq=1E6, mode=0)
    return SPIDev

def readRegister(startAddress, numBytes=1):
    spi = getSPI()
    
    startAddr = startAddress
    if type(startAddress) != int:
        startAddr = startAddress.value 
        
    cmd = [ReadReg, startAddr]
    
    if DUMPSPI:
        cmdAndPayload = []
        for b in cmd:
            cmdAndPayload.append(cmd[0])
        for i in range(numBytes):
            cmdAndPayload.append(0) 
            
        print(f"SPI READ: {arrayBytesString(cmdAndPayload)}")
    spi.write(cmd, True, False)
    
    return spi.read(numBytes, start=False, stop=True)
    
def writeRegisters(startAddress, bytesToWrite):
    spi = getSPI()
    startAddr = startAddress
    if type(startAddress) != int:
        startAddr = startAddress.value 
        
    cmdAndPayload = [WriteReg, startAddr]
    for b in bytesToWrite:
        cmdAndPayload.append(b) 
        
    if DUMPSPI:
        print(f'SPI WRITE: {arrayBytesString(cmdAndPayload)}')
    spi.write(cmdAndPayload, True, True)
    

def get16bitRegister(startAddr):
    contents = readRegister(startAddr, 2)
    val =  (contents[0] << 8) | contents[1]
    return val
    

def GPIOConfigAddress(gpio:int):
    return RegisterAddress.BaseGPIOAddress.value + (2*gpio)
    
def getGPIOConfig(gpio:int):
    startAddr = GPIOConfigAddress(gpio)
    val = get16bitRegister(startAddr)
    return GPIOConfig(val)
    
def setGPIOConfig(gpio:int, setTo:GPIOConfig):
    startAddr = GPIOConfigAddress(gpio)
    config = [0]*2
    config[0] = ((setTo.value & 0xff00) >> 8)
    config[1] = setTo.value & 0x00ff
    writeRegisters(startAddr, config)
    
def latchGPIOConfig():
    writeRegisters(RegisterAddress.GPIOControl, [1])
    
def GPIOConfigReg():
    return get16bitRegister(RegisterAddress.GPIOControl)
    
def GPIOConfigIsLatching():
    return GPIOConfigReg() & 0x01
    

def setReset(on:bool=True):
    val = 1
    if not on:
        val = 0
    writeRegisters(RegisterAddress.CPUReset, [val])
    
def dumpGPIOConfig():
    print(f'GCNF: {hex(GPIOConfigReg())}')
    
def flashInputs( gpioidstart = 24, gpioidend = 28, sleeptime=1):
    pulldown = GPIOConfig(GPIOMode.USER_INPUT_PULLDOWN)
    
    
    pullup = GPIOConfig(GPIOMode.USER_INPUT_PULLUP)
    
    
    nopull = GPIOConfig(GPIOMode.USER_INPUT_NOPULL)
    output = GPIOConfig(GPIOMode.USER_OUTPUT)
    
    for i in range(10):
        print(pulldown)
        for g in range(gpioidstart, gpioidend):
            setGPIOConfig(g, pulldown)
        
        latchGPIOConfig()
        
        time.sleep(sleeptime)
        
        print(pullup)
        for g in range(gpioidstart, gpioidend):
            setGPIOConfig(g, pullup)
        
        latchGPIOConfig()
        time.sleep(sleeptime)
        
        
        print(nopull)
        for g in range(gpioidstart, gpioidend):
            setGPIOConfig(g, nopull)
        
        latchGPIOConfig()
        time.sleep(sleeptime)

        print(output)
        for g in range(gpioidstart, gpioidend):
            setGPIOConfig(g, output)
        latchGPIOConfig()
        
        
def restart():
    setReset(True)
    setReset(False)
    
def main():
    setReset(True) # optional
    
    for i in range(37):
        print(f'GPIO {i} ({hex(GPIOConfigAddress(i))}): {getGPIOConfig(i)}\n')
    
    #flashInputs(gpioidstart = 24, gpioidend=28, sleeptime=2)
    #flashInputs(gpioidstart = 30, gpioidend=36, sleeptime=0.3)
    
    setReset(False)
    

if __name__ == '__main__':
    main()
    
