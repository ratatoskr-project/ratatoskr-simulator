# Changelog

All notable changes to this project will be documented in this file.

## [Released]

## [1.0.0] - 2018-01-09

### Features
- first release candidate
- supports basic NoC simulation features
- configurable NoC routers with routing and selection
- simple processing element model
- link model with transmission matrixes and raw data output for debugging
- synthetic, taskbased, and netrace support; netrace for 2D mode only

## [1.1.0] - 2018-01-22

### Features
- added functionalty of configurable routers
- adaptive routing and selection methods
- separation of processing elements and network interface
- removed netrace
- cmake support and simple build script

### Improvements
- links: removed unnecessary components; moved information to matrix

### Known Issues
- calculation of data amounts still faulty. 
- router matrixes missing
- implementation of agra, esparda, mafa missing