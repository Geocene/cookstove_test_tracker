@echo on
h2xml -I. -c -o %1.xml %1.h
xml2py -v -c -kdefst -l nicaiu -o %1.py %1.xml 
