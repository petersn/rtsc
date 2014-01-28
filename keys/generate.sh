#! /bin/sh

openssl req -config config.ini -x509 -nodes -days 3650 -newkey rsa:2048 -keyout rtsc_key -out rtsc_key.crt
openssl rsa -in rtsc_key -pubout > rtsc_key.pub

