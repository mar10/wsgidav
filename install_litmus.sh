#!/bin/bash
wget http://www.webdav.org/neon/litmus/litmus-0.13.tar.gz
tar xzf litmus-0.13.tar.gz
cd litmus-0.13
./configure --with-ssl
sudo make install
