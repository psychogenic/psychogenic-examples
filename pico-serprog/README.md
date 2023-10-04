# Caravel Pass-through Pico SerProg

This minor patch to [pico-serprog](https://github.com/stacksmashing/pico-serprog/tree/main) (commit 961ef27) prepends the pass-through byte to every transaction, such that you can run it on a raspi pico and then use it with flashrom to burn to the caravel-connected flash.

## flashrom

If you have some 'code' as binary data (code.bin) and you want to flash it with this installed on the pico, then the process is just "use flashrom" as usual.

Note that by default it wants to write and verify the entire flash memory.

To avoid this lengthy process, you can create a layout file, e.g. put this is ttflash.layout:

```
00000000:000025ff exe
00002600:003FFFFF storage
```

Just ensure the exe region has enough space for your bytes. Then:

`
flashrom -V --noverify-all -p serprog:dev=/dev/ttyACM0:115200 -l ttflash.layout --image exe -w code.bin
`

