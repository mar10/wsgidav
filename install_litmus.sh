#!/bin/bash
git clone https://github.com/tolsen/litmus.git
cd litmus
./configure --with-ssl
sudo make install
