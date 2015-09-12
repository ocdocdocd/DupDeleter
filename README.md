# DupDeleter

## Introduction

DupDeleter is a program that lets you recursively search any directory on your computer to locate similar image files and delete them if you wish. It does not just detect only exact duplicate image files, but also images that are similar. For example, it will detect that an image is a duplicate if it is the same image but just larger/smaller, or small, localized changes. The user has the option to delete either selected duplicates or let the program automatically delete all duplicates, leaving just one copy of each (that copy being the first one encountered by the program during its search).

## Requirements

The following packages must be installed:
- Pillow
- pygobject

## Installation

Just checkout the branch, make sure all required packages are installed, and run dupdeletergui.py.

## Contributions

If you find a bug or wish to add a feature, please make your pull requests to the development branch.

## License

This software is available under the MIT license.