from __future__ import division, print_function

from collections import namedtuple
import numpy as np


# There are two different record types.  The first is a numpy structured
# array and the second is a namedtuple.  Numpy expects to have an an array
# at the top level, meaning everyting needs to be indexed with an extra [0]
# as there is only one of these objects.  I use np to do the read and then
# convert to a namedtuple afterwords to avoid the extra indexing.

RDR7dtype = [
	('UCode',				'|S1'			),
	('PackageSize',			'<u2'			),
	('CheckSum',			'<3u2'			),
	('ElapsedTime',			'<u2'			),
	('InstrumentStatus',	'<u2'			),
	('InstrumentError',		'<u8'			),
	('Data',				'<(10,33)f4'	),
	('ErrorCodes',			'<10u4'			),
	('ResetCodes',			'<10u4'			),
	('SheathTemperature',	'<u2'			),
	('AbsolutePressure',	'<u2'			),
	('AnalogInput1',		'<10u2',		),
	('AnalogInput2',		'<10u2',		),
	('Elm',					'<(10,22)u4'	),
	('CR',					'|S1'			)
]

RDR7Type = namedtuple('RDR7Type', [name for name,fmt in RDR7dtype])


N= 2346
b = '\0'*N
d = np.frombuffer(b, dtype=RDR7dtype, count=1)


d = d.copy()
v = d.view(np.recarray)
v.UCode[0] = 'U'
v.PackageSize[0] = N
v.CheckSum[0] = (1,2,3)
v.CR[0] = '\r'

x = RDR7Type(*d[0])
print(x.SheathTemperature)
x = x._replace(SheathTemperature=(x.SheathTemperature+1)/10.0,
               AbsolutePressure =(x.AbsolutePressure+1)/10.0)
print(x.SheathTemperature)
print(x.AbsolutePressure)

