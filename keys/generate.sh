#! /bin/bash

openssl req -x509 -nodes -days 3650 -newkey rsa:4096 -keyout priv.key -out cert.crt

