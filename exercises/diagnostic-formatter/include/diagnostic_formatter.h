#ifndef DIAGNOSTIC_FORMATTER_H
#define DIAGNOSTIC_FORMATTER_H

#include <stdarg.h>
#include <stddef.h>

int diagnostic_vformat(
    char *buffer,
    size_t capacity,
    const char *format,
    va_list arguments
);
int diagnostic_format(
    char *buffer,
    size_t capacity,
    const char *format,
    ...
);

#endif
