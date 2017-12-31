#!/bin/bash
git clone https://github.com/eanlain/litmus.git
cd litmus
./configure --with-ssl
sudo make install
