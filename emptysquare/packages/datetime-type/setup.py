from setuptools import setup

setup(
    name='lektor-datetime-type',
    version='0.1',
    author=u'A. Jesse Jiryu Davis',
    author_email='jesse@emptysquare.net',
    license='MIT',
    py_modules=['lektor_datetime_type'],
    entry_points={
        'lektor.plugins': [
            'datetime-type = lektor_datetime_type:DatetimeTypePlugin',
        ]
    }
)
