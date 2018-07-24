# UDI Polyglot v2 Dyson Poly

[![license](https://img.shields.io/github/license/mashape/apistatus.svg)](https://github.com/exking/udi-dyson-poly/blob/master/LICENSE)

This Poly provides an interface between Dyson devices and [Polyglot v2](https://github.com/UniversalDevicesInc/polyglot-v2) server.

### Installation instructions
You can install NodeServer from the Polyglot store or manually running
```
cd ~/.polyglot/nodeservers
git clone https://github.com/exking/udi-dyson-poly.git Dyson
cd Dyson
./install.sh
```
### Configuration
This Poly requires at least 2 parameters to be set:
`username` - your Dyson account username
`password` - your Dyson account password
`country` - 2 letter country code, defaults to `US` if not specified.

### Notes
Dyson control is local, cloud connection is only used for authentication. Currently only TP04 and DP04 machines are supported, but underlying [libpurecoollink](http://github.com/CharlesBlonde/libpurecoollink) library supports many more, I just don't have access to those devices to test with.

Please report any problems on the UDI user forum.

Thanks and good luck.
